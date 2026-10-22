"""Streaming simulado: simulador de eventos (produtor) e micro-lote incremental (consumidor).

Fluxo:
  simulador --Pub/Sub--> assinatura BigQuery --> bronze.eventos_stream (bruto, append)
  micro-lote: bronze.eventos_stream -> valida, deduplica -> silver.eventos_resultado_municipio
                                    -> quarentena em ops.eventos_invalidos
                                    -> gold.indicador_municipio_hibrido (oficial + simulado)

O evento simulado representa um resultado preliminar de avaliacao municipal (rede municipal,
2o ano) do ano seguinte ao ultimo resultado oficial. Todo evento leva origem = "simulado".

Uso:
  python -m pipeline.streaming simular --eventos 300 --por-segundo 5
  python -m pipeline.streaming processar                       # um micro-lote
  python -m pipeline.streaming processar --lotes 10 --intervalo 30   # varios, em sequencia
"""
import argparse
import json
import random
import sys
import time
import uuid
from datetime import datetime, timezone

from . import qualidade
from .bq import BQ, log, render_sql
from .config import Config, carregar, novo_run_id, validar_run_id
from .metricas import Execucao
from .pubsub_rest import PubSub
from .schemas import OPS_STREAM_LOTES

TIPOS_INVALIDOS = (
    "json_invalido",
    "campo_obrigatorio_ausente",
    "origem_invalida",
    "municipio_inexistente",
    "alfabetizados_maior_que_avaliados",
    "ano_fora_da_faixa",
)


# ---------------------------------------------------------------- simulador (produtor)
def agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def carregar_municipios(cfg: Config, bq: BQ, limite: int) -> tuple[int, list[dict]]:
    """Municipios reais (rede municipal) do ultimo ano oficial, para eventos plausiveis."""
    tabela = cfg.tabela("gold", "indicador_municipio")
    sql = f"""
SELECT ano, id_municipio, taxa_oficial, n_avaliados
FROM `{tabela}`
WHERE rede_codigo = '3' AND tem_resultado_oficial AND n_avaliados IS NOT NULL
  AND ano = (SELECT MAX(ano) FROM `{tabela}` WHERE tem_resultado_oficial)
ORDER BY FARM_FINGERPRINT(id_municipio)
LIMIT {int(limite)}"""
    _, resultado = bq.executar(sql, "streaming: municipios para simulacao")
    linhas = [dict(r.items()) for r in resultado]
    if not linhas:
        raise RuntimeError("gold.indicador_municipio vazia: rode o pipeline batch antes do streaming.")
    return linhas[0]["ano"] + 1, linhas


def evento_valido(municipio: dict, ano: int, rng: random.Random) -> dict:
    n = max(5, int(rng.gauss(municipio["n_avaliados"], municipio["n_avaliados"] * 0.1)))
    taxa = min(100.0, max(0.0, rng.gauss(municipio["taxa_oficial"] + 3, 6)))
    return {
        "event_id": str(uuid.uuid4()),
        "event_time": agora_iso(),
        "tipo": "resultado_municipio",
        "ano": ano,
        "id_municipio": municipio["id_municipio"],
        "rede_codigo": "3",
        "serie": "2",
        "n_avaliados": n,
        "n_alfabetizados": round(n * taxa / 100),
        "origem": "simulado",
    }


def corromper(evento: dict, tipo: str) -> bytes:
    """Gera um payload invalido de proposito, para exercitar a quarentena."""
    e = dict(evento)
    if tipo == "json_invalido":
        return b'{"event_id": "quebrado", "ano": 2025,'
    if tipo == "campo_obrigatorio_ausente":
        e.pop("id_municipio")
    elif tipo == "origem_invalida":
        e["origem"] = "oficial"  # o streaming nunca pode se passar por dado oficial
    elif tipo == "municipio_inexistente":
        e["id_municipio"] = "9999999"
    elif tipo == "alfabetizados_maior_que_avaliados":
        e["n_alfabetizados"] = e["n_avaliados"] + 10
    elif tipo == "ano_fora_da_faixa":
        e["ano"] = 1999
    return json.dumps(e).encode("utf-8")


def simular(cfg: Config, bq: BQ, eventos: int, por_segundo: float, pct_duplicados: float,
            pct_invalidos: float, semente: int | None):
    rng = random.Random(semente)
    ano, municipios = carregar_municipios(cfg, bq, limite=max(50, eventos))
    ps = PubSub(cfg.projeto)
    topico = cfg.streaming["topico"]
    contagem = {"validos": 0, "duplicados_reenviados": 0, "invalidos": {t: 0 for t in TIPOS_INVALIDOS}}
    ja_enviados: list[bytes] = []
    intervalo = 1.0 / por_segundo if por_segundo > 0 else 0
    log("INFO", "simulacao iniciada", eventos=eventos, ano_simulado=ano, topico=topico)

    for i in range(eventos):
        sorteio = rng.random()
        if ja_enviados and sorteio < pct_duplicados:
            payload = rng.choice(ja_enviados)  # mesmo event_id, nova mensagem: duplicado de verdade
            contagem["duplicados_reenviados"] += 1
        elif sorteio < pct_duplicados + pct_invalidos:
            tipo = rng.choice(TIPOS_INVALIDOS)
            payload = corromper(evento_valido(rng.choice(municipios), ano, rng), tipo)
            contagem["invalidos"][tipo] += 1
        else:
            payload = json.dumps(evento_valido(rng.choice(municipios), ano, rng)).encode("utf-8")
            ja_enviados.append(payload)
            contagem["validos"] += 1
        ps.publicar(topico, [(payload, {"origem": "simulado", "tipo": "resultado_municipio"})])
        if (i + 1) % 50 == 0:
            log("INFO", "eventos publicados", enviados=i + 1, de=eventos)
        if intervalo:
            time.sleep(intervalo)

    log("INFO", "simulacao concluida", ano_simulado=ano, total=eventos,
        validos=contagem["validos"], duplicados_reenviados=contagem["duplicados_reenviados"],
        invalidos=sum(contagem["invalidos"].values()), invalidos_por_tipo=contagem["invalidos"])
    return contagem


# ---------------------------------------------------------------- micro-lote (consumidor)
def variaveis(cfg: Config, lote_id: str) -> dict:
    return {
        "projeto": cfg.projeto,
        "bronze": cfg.datasets["bronze"],
        "silver": cfg.datasets["silver"],
        "stage": cfg.datasets["silver_stage"],
        "gold": cfg.datasets["gold"],
        "ops": cfg.datasets["ops"],
        "lote_id": validar_run_id(lote_id),
        "janela_horas": int(cfg.streaming["janela_horas"]),
    }


def processar_lote(cfg: Config, bq: BQ, execucao: Execucao) -> dict:
    lote_id = execucao.run_id
    vars_ = variaveis(cfg, lote_id)

    with execucao.etapa("stream.lote") as reg:
        bq.executar(render_sql("streaming/01_lote.sql", **vars_), "stream: montar micro-lote")
        reg["linhas_saida"] = bq.client.get_table(cfg.tabela("silver_stage", "stream_lote")).num_rows
        novas = reg["linhas_saida"]

    if novas == 0:
        log("INFO", "micro-lote sem mensagens novas", lote_id=lote_id)
        return {"lote_id": lote_id, "mensagens_novas": 0}

    for arquivo, etapa in (("02_merge_eventos.sql", "stream.merge_eventos"),
                           ("03_merge_invalidos.sql", "stream.quarentena"),
                           ("04_merge_mensagens.sql", "stream.livro_razao")):
        with execucao.etapa(etapa) as reg:
            job, _ = bq.executar(render_sql(f"streaming/{arquivo}", **vars_), etapa)
            reg["linhas_entrada"] = novas
            reg["linhas_saida"] = job.num_dml_affected_rows

    with execucao.etapa("qualidade.stream") as reg:
        reg["linhas_saida"] = len(qualidade.validar_stream(cfg, bq, lote_id))

    with execucao.etapa("stream.gold_hibrido") as reg:
        bq.executar(render_sql("streaming/05_gold_hibrido.sql", **vars_), "stream: gold hibrido")
        reg["linhas_saida"] = bq.client.get_table(cfg.tabela("gold", "indicador_municipio_hibrido")).num_rows

    with execucao.etapa("stream.metricas") as reg:
        m = bq.valor(render_sql("streaming/06_metricas_lote.sql", **vars_), "stream: metricas do lote")
        linha = {"lote_id": lote_id, "processado_em": datetime.now(timezone.utc).isoformat(), **m}
        bq.anexar_linhas(cfg.tabela("ops", "stream_lotes"), [linha], OPS_STREAM_LOTES)
        reg["linhas_saida"] = m["inseridos"]

    log("INFO", "micro-lote concluido", **linha)
    return linha


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Streaming simulado do Tech Challenge")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_sim = sub.add_parser("simular", help="publica eventos simulados no Pub/Sub")
    p_sim.add_argument("--eventos", type=int, default=300)
    p_sim.add_argument("--por-segundo", type=float, default=5.0)
    p_sim.add_argument("--pct-duplicados", type=float, default=0.05)
    p_sim.add_argument("--pct-invalidos", type=float, default=0.05)
    p_sim.add_argument("--semente", type=int, default=None, help="fixa o sorteio para repetir a simulacao")

    p_proc = sub.add_parser("processar", help="processa micro-lotes da Bronze do streaming")
    p_proc.add_argument("--lotes", type=int, default=1)
    p_proc.add_argument("--intervalo", type=int, default=30, help="segundos entre lotes (minimo 5)")

    args = parser.parse_args(argv)
    cfg = carregar()
    bq = BQ(cfg)

    if args.comando == "simular":
        if not 0 <= args.pct_duplicados + args.pct_invalidos < 1:
            parser.error("pct-duplicados + pct-invalidos precisa ficar entre 0 e 1")
        simular(cfg, bq, args.eventos, args.por_segundo, args.pct_duplicados, args.pct_invalidos, args.semente)
        return 0

    for i in range(args.lotes):
        if i:
            time.sleep(max(5, args.intervalo))
        execucao = Execucao(bq, pipeline="streaming", run_id=novo_run_id())
        try:
            processar_lote(cfg, bq, execucao)
        except Exception as exc:
            log("ERROR", "pipeline falhou", pipeline="streaming", run_id=execucao.run_id,
                erro=f"{type(exc).__name__}: {exc}")
            raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
