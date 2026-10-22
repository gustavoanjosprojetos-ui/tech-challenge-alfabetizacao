"""Testes das partes puras do pipeline (sem acesso a nuvem)."""
import re
from pathlib import Path

import pytest

from pipeline import gold, qualidade, silver
from pipeline.bq import render_sql
from pipeline.config import Config, RAIZ, data_ingestao, validar_run_id


def cfg_teste(**ajustes) -> Config:
    base = dict(
        projeto="proj-teste",
        localizacao="US",
        bucket="bucket-teste",
        fonte_dataset="basedosdados.br_inep_avaliacao_alfabetizacao",
        datasets={"bronze": "bronze", "silver_stage": "silver_stage", "silver": "silver",
                  "gold_stage": "gold_stage", "gold": "gold", "ops": "ops"},
        tabelas_fonte=["alunos"],
        max_gb_por_query=5,
        corte_alfabetizacao=743,
        qualidade={"match_alunos_resultado_municipio": 0.9,
                   "match_meta_municipio_resultado": 0.95,
                   "match_meta_uf_resultado_uf": 0.85},
    )
    base.update(ajustes)
    return Config(**base)


# --- run_id: entra em SQL e caminho do GCS, entao so o formato esperado passa
def test_run_id_valido():
    assert validar_run_id("20261021T013000Z") == "20261021T013000Z"
    assert data_ingestao("20261021T013000Z") == "2026-10-21"


@pytest.mark.parametrize("ruim", ["", "2026-10-21", "20261021T013000Z' OR 1=1 --", "x/../y"])
def test_run_id_invalido(ruim):
    with pytest.raises(ValueError):
        validar_run_id(ruim)


# --- avaliacao das regras
@pytest.mark.parametrize("valor,op,limiar,esperado", [
    (0, "==", 0, True),
    (3, "==", 0, False),
    (0.96, ">=", 0.95, True),
    (0.94, ">=", 0.95, False),
    (None, ">=", 0.95, False),   # nao medido nunca e aprovado
    (12.5, None, None, True),    # informativa so mede
])
def test_avaliar(valor, op, limiar, esperado):
    assert qualidade.avaliar(valor, op, limiar) is esperado


def test_operador_desconhecido():
    with pytest.raises(ValueError):
        qualidade.avaliar(1, "!=", 0)


def test_forcar_falha_eleva_limiar_uf():
    normal = {r.nome: r for r in qualidade.regras_silver(cfg_teste())}
    forcado = {r.nome: r for r in qualidade.regras_silver(cfg_teste(), forcar_falha=True)}
    assert normal["match_meta_uf_resultado_uf"].limiar == 0.85
    assert forcado["match_meta_uf_resultado_uf"].limiar == 1.0
    assert forcado["match_meta_uf_resultado_uf"].tipo == qualidade.BLOQUEANTE


def test_toda_regra_tem_tipo_valido_e_match_e_bloqueante():
    regras = qualidade.regras_silver(cfg_teste())
    nomes = [r.nome for r in regras]
    assert len(nomes) == len(set(nomes)), "nomes de regra repetidos"
    for r in regras:
        assert r.tipo in (qualidade.BLOQUEANTE, qualidade.INFORMATIVA)
        if r.tipo == qualidade.BLOQUEANTE:
            assert r.operador is not None and r.limiar is not None
        if r.nome.startswith("match_"):
            assert r.tipo == qualidade.BLOQUEANTE


def test_regras_nao_tem_chaves_python_sobrando():
    for r in qualidade.regras_silver(cfg_teste()):
        assert "{s}" not in r.sql and "{tabela}" not in r.sql, r.nome
        assert "valor" in r.sql and "detalhe" in r.sql, r.nome


# --- SQL da Silver: todas as variaveis substituidas, e cada arquivo cria a tabela do seu nome
def test_render_de_todos_os_sql_da_silver():
    vars_ = silver.variaveis(cfg_teste(), "20261021T013000Z")
    for arquivo in silver.ARQUIVOS:
        sql = render_sql(f"silver/{arquivo}", **vars_)
        assert "${" not in sql, arquivo
        tabela = silver.tabela_do_arquivo(arquivo)
        assert re.search(rf"CREATE OR REPLACE TABLE `proj-teste\.silver_stage\.{tabela}`", sql), arquivo


def test_silver_le_apenas_o_run_id_da_bronze():
    vars_ = silver.variaveis(cfg_teste(), "20261021T013000Z")
    for arquivo in silver.ARQUIVOS:
        sql = render_sql(f"silver/{arquivo}", **vars_)
        if ".bronze." in sql:
            leituras = sql.count("`proj-teste.bronze.")
            filtros = sql.count("run_id = '20261021T013000Z'")
            assert filtros >= leituras, f"{arquivo}: leitura da bronze sem filtro de run_id"


def test_silver_nao_converte_nulo_em_zero():
    for arquivo in silver.ARQUIVOS:
        texto = (RAIZ / "sql" / "silver" / arquivo).read_text(encoding="utf-8").upper()
        assert not re.search(r"(IFNULL|COALESCE)\([^)]*,\s*0\s*\)", texto), arquivo


# --- Gold
def test_render_de_todos_os_sql_da_gold():
    vars_ = gold.variaveis(cfg_teste())
    assert gold.ARQUIVOS, "nenhum SQL da gold encontrado"
    for arquivo in gold.ARQUIVOS:
        sql = render_sql(f"gold/{arquivo}", **vars_)
        assert "${" not in sql, arquivo
        tabela = silver.tabela_do_arquivo(arquivo)
        assert re.search(rf"CREATE OR REPLACE TABLE `proj-teste\.gold_stage\.{tabela}`", sql), arquivo


def test_gold_le_apenas_silver_publicada_e_proprio_stage():
    """A Gold nunca le bronze nem silver_stage: so dado aprovado na qualidade."""
    vars_ = gold.variaveis(cfg_teste())
    for arquivo in gold.ARQUIVOS:
        sql = render_sql(f"gold/{arquivo}", **vars_)
        datasets = set(re.findall(r"`proj-teste\.([a-z_]+)\.", sql))
        assert datasets <= {"silver", "gold_stage"}, f"{arquivo}: le {datasets}"


def test_gold_nao_converte_nulo_em_zero():
    for arquivo in gold.ARQUIVOS:
        texto = (RAIZ / "sql" / "gold" / arquivo).read_text(encoding="utf-8").upper()
        assert not re.search(r"(IFNULL|COALESCE)\([^)]*,\s*0\s*\)", texto), arquivo


def test_meta_vs_resultado_tem_estados_distintos():
    texto = (RAIZ / "sql" / "gold" / "05_meta_vs_resultado.sql").read_text(encoding="utf-8")
    for estado in qualidade.STATUS_META_VALIDOS:
        assert f"'{estado}'" in texto, estado


def test_features_separam_entrada_e_alvo():
    """Toda coluna de saida das features e identificador, f_* (entrada) ou alvo_*."""
    texto = (RAIZ / "sql" / "gold" / "08_features_municipio.sql").read_text(encoding="utf-8")
    select_final = texto.rsplit("SELECT", 1)[1].split("FROM base t")[0]
    colunas = re.findall(r"AS\s+([a-z_0-9]+)", select_final)
    identificadores = {"ano_base", "ano_alvo"}
    for c in colunas:
        assert c in identificadores or c.startswith(("f_", "alvo_")), c


def test_regras_gold_validas():
    regras = qualidade.regras_gold(cfg_teste())
    nomes = [r.nome for r in regras]
    assert len(nomes) == len(set(nomes))
    for r in regras:
        assert "gold_stage" in r.sql, r.nome
        if r.tipo == qualidade.BLOQUEANTE:
            assert r.operador and r.limiar is not None


# --- Streaming
from pipeline import streaming  # noqa: E402


def test_render_de_todos_os_sql_do_streaming():
    vars_ = streaming.variaveis(cfg_teste(streaming={"topico": "t", "assinatura": "a", "janela_horas": 48}),
                                "20261021T150000Z")
    arquivos = sorted(p.name for p in (RAIZ / "sql" / "streaming").glob("*.sql"))
    assert len(arquivos) == 6
    for arquivo in arquivos:
        sql = render_sql(f"streaming/{arquivo}", **vars_)
        assert "${" not in sql, arquivo


def test_lote_classifica_cada_mensagem_em_um_resultado():
    texto = (RAIZ / "sql" / "streaming" / "01_lote.sql").read_text(encoding="utf-8")
    for resultado in ("'invalido'", "'duplicado'", "'inserido'"):
        assert resultado in texto
    for motivo in streaming.TIPOS_INVALIDOS:
        assert f"'{motivo}'" in texto, f"o SQL nao trata o invalido gerado pelo simulador: {motivo}"


def test_evento_simulado_valido():
    import random
    mun = {"id_municipio": "3550308", "taxa_oficial": 58.0, "n_avaliados": 1000}
    e = streaming.evento_valido(mun, 2025, random.Random(1))
    assert e["origem"] == "simulado" and e["ano"] == 2025 and e["rede_codigo"] == "3"
    assert 0 <= e["n_alfabetizados"] <= e["n_avaliados"]
    assert e["event_time"].endswith("Z")


def test_corromper_gera_cada_tipo_de_invalido():
    import json
    import random
    mun = {"id_municipio": "3550308", "taxa_oficial": 58.0, "n_avaliados": 1000}
    base = streaming.evento_valido(mun, 2025, random.Random(1))
    for tipo in streaming.TIPOS_INVALIDOS:
        payload = streaming.corromper(base, tipo)
        if tipo == "json_invalido":
            with pytest.raises(ValueError):
                json.loads(payload)
            continue
        e = json.loads(payload)
        if tipo == "campo_obrigatorio_ausente":
            assert "id_municipio" not in e
        elif tipo == "origem_invalida":
            assert e["origem"] != "simulado"
        elif tipo == "alfabetizados_maior_que_avaliados":
            assert e["n_alfabetizados"] > e["n_avaliados"]
    assert base["origem"] == "simulado", "corromper nao pode alterar o evento original"


def test_regras_stream_validas():
    regras = qualidade.regras_stream(cfg_teste())
    assert len({r.nome for r in regras}) == len(regras)
    for r in regras:
        if r.tipo == qualidade.BLOQUEANTE:
            assert r.operador and r.limiar is not None


# --- Orquestracao e alerta
from pipeline import setup_alerta  # noqa: E402


def test_politica_de_alerta():
    p = setup_alerta.politica("projects/p/notificationChannels/1")
    assert p["notificationChannels"] == ["projects/p/notificationChannels/1"]
    filtro = p["conditions"][0]["conditionMatchedLog"]["filter"]
    assert "severity>=ERROR" in filtro and "pipeline-batch" in filtro and "Workflow" in filtro
    # alertas de log exigem limite de notificacoes
    assert p["alertStrategy"]["notificationRateLimit"]["period"]


def test_email_do_alerta_validado():
    assert setup_alerta.EMAIL_RE.match("alguem@exemplo.com")
    assert not setup_alerta.EMAIL_RE.match("sem-arroba")


def test_workflow_roda_batch_antes_do_streaming():
    texto = (RAIZ / "orquestracao" / "workflow.yaml").read_text(encoding="utf-8")
    assert texto.index("jobs/pipeline-batch") < texto.index("jobs/pipeline-streaming")


def test_imagem_nao_leva_config_local_nem_credenciais():
    ignorados = (RAIZ / ".dockerignore").read_text(encoding="utf-8").split()
    assert "config.toml" in ignorados
    dockerfile = (RAIZ / "Dockerfile").read_text(encoding="utf-8")
    assert "config.toml" not in dockerfile.replace("config.example.toml", "")
