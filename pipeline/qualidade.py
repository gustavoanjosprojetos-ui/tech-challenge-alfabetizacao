"""Regras de qualidade da Silver.

- bloqueante: se falhar, o pipeline para ANTES de publicar a Silver (e portanto antes da Gold).
- informativa: registrada para acompanhamento, nao interrompe.
Todas as regras rodam, todas sao gravadas em ops.dq_resultados (APPEND), e so depois
a falha bloqueante e levantada. Nenhum except captura essa excecao: o processo termina com erro.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from .bq import BQ, log
from .config import Config
from .schemas import DQ_RESULTADOS

BLOQUEANTE = "bloqueante"
INFORMATIVA = "informativa"


class FalhaBloqueante(RuntimeError):
    pass


@dataclass(frozen=True)
class Regra:
    nome: str
    tipo: str
    sql: str  # deve devolver uma linha com as colunas valor (numero) e detalhe (texto)
    operador: str | None = None  # "==", ">=", "<=" ou None (so mede)
    limiar: float | None = None


def avaliar(valor, operador: str | None, limiar: float | None) -> bool:
    if operador is None:
        return True
    if valor is None:
        return False  # nao conseguir medir nunca conta como aprovado
    if operador == "==":
        return valor == limiar
    if operador == ">=":
        return valor >= limiar
    if operador == "<=":
        return valor <= limiar
    raise ValueError(f"operador desconhecido: {operador}")


def _match(origem_sql: str, destino_sql: str, chaves: list[str], rotulo: str) -> str:
    """SQL de taxa de correspondencia: fracao das chaves da origem que encontram par no destino."""
    on = " AND ".join(f"o.{c} = d.{c}" for c in chaves)
    concat = ", '/', ".join(f"CAST({c} AS STRING)" for c in chaves)
    return f"""
WITH o AS ({origem_sql}),
     d AS (SELECT DISTINCT {', '.join(chaves)}, TRUE AS existe FROM ({destino_sql})),
     j AS (SELECT o.*, d.existe IS NOT NULL AS casou FROM o LEFT JOIN d ON {on})
SELECT
  SAFE_DIVIDE(COUNTIF(casou), COUNT(*)) AS valor,
  FORMAT('%d de %d {rotulo} com par. Sem par (ate 30): %s',
         COUNTIF(casou), COUNT(*),
         IFNULL(ARRAY_TO_STRING(ARRAY_AGG(IF(casou, NULL, CONCAT({concat})) IGNORE NULLS LIMIT 30), ', '), '-')) AS detalhe
FROM j"""


def regras_silver(cfg: Config, forcar_falha: bool = False) -> list[Regra]:
    s = f"{cfg.projeto}.{cfg.datasets['silver_stage']}"
    q = cfg.qualidade
    limiar_uf = 1.0 if forcar_falha else q["match_meta_uf_resultado_uf"]

    def conta(sql_where: str, tabela: str) -> str:
        return f"SELECT COUNTIF({sql_where}) AS valor, FORMAT('%d linhas em {tabela}', COUNTIF({sql_where})) AS detalhe FROM `{s}.{tabela}`"

    def duplicados(tabela: str, chaves: str) -> str:
        return f"""
SELECT COUNT(*) - COUNT(DISTINCT TO_JSON_STRING(STRUCT({chaves}))) AS valor,
       FORMAT('%d linhas, chave ({chaves})', COUNT(*)) AS detalhe
FROM `{s}.{tabela}`"""

    return [
        # --- Duplicidade (bloqueantes)
        Regra("dim_rede_codigo_duplicado", BLOQUEANTE, duplicados("dim_rede", "rede_codigo"), "==", 0),
        Regra("alunos_duplicados", BLOQUEANTE, duplicados("alunos", "ano, id_aluno"), "==", 0),
        Regra("resultado_municipio_duplicado", BLOQUEANTE,
              duplicados("resultado_municipio", "ano, id_municipio, serie, rede_codigo"), "==", 0),
        Regra("resultado_uf_duplicado", BLOQUEANTE,
              duplicados("resultado_uf", "ano, sigla_uf, serie, rede_codigo"), "==", 0),
        Regra("meta_trajetoria_duplicada", BLOQUEANTE,
              duplicados("meta_trajetoria", "nivel, sigla_uf, id_municipio, rede_codigo, ano_publicacao, ano_meta"), "==", 0),

        # --- Chaves e dominios (bloqueantes): codigo desconhecido nao pode entrar calado
        Regra("rede_desconhecida", BLOQUEANTE, f"""
SELECT (SELECT COUNTIF(rede_descricao = 'desconhecido') FROM `{s}.alunos`)
     + (SELECT COUNTIF(rede_descricao = 'desconhecido') FROM `{s}.resultado_municipio`)
     + (SELECT COUNTIF(rede_descricao = 'desconhecido') FROM `{s}.resultado_uf`) AS valor,
       'codigos de rede sem traducao no dicionario (alunos + municipio + uf)' AS detalhe""", "==", 0),
        Regra("meta_rede_sem_mapeamento", BLOQUEANTE, f"""
SELECT COUNTIF(rede_codigo IS NULL) AS valor,
       FORMAT('rotulos sem mapeamento: %s',
              IFNULL(STRING_AGG(DISTINCT IF(rede_codigo IS NULL, rotulo_rede_meta, NULL)), '-')) AS detalhe
FROM `{s}.meta_base`""", "==", 0),
        Regra("municipio_sem_uf", BLOQUEANTE, f"""
SELECT (SELECT COUNTIF(sigla_uf IS NULL) FROM `{s}.alunos`)
     + (SELECT COUNTIF(sigla_uf IS NULL) FROM `{s}.resultado_municipio`)
     + (SELECT COUNTIF(sigla_uf IS NULL) FROM `{s}.meta_base` WHERE nivel = 'municipio') AS valor,
       'id_municipio cujo prefixo IBGE nao corresponde a nenhuma UF' AS detalhe""", "==", 0),
        Regra("id_municipio_formato_invalido", BLOQUEANTE,
              conta(r"NOT REGEXP_CONTAINS(id_municipio, r'^\d{7}$')", "resultado_municipio"), "==", 0),
        Regra("presenca_fora_dominio", BLOQUEANTE,
              conta("presenca_codigo NOT IN ('0', '1') OR presenca_codigo IS NULL", "alunos"), "==", 0),
        Regra("preenchimento_fora_dominio", BLOQUEANTE,
              conta("preenchimento_codigo NOT IN ('0', '1') OR preenchimento_codigo IS NULL", "alunos"), "==", 0),
        Regra("proficiencia_fora_escala", BLOQUEANTE,
              conta("proficiencia <= 0 OR proficiencia > 1000", "alunos"), "==", 0),
        Regra("peso_nao_positivo", BLOQUEANTE, conta("peso_aluno <= 0", "alunos"), "==", 0),
        Regra("meta_fora_0_100", BLOQUEANTE, conta("meta_pct < 0 OR meta_pct > 100", "meta_trajetoria"), "==", 0),

        # --- Taxa de correspondencia dos joins (bloqueantes, limiares no config)
        Regra("match_alunos_resultado_municipio", BLOQUEANTE, _match(
            f"SELECT DISTINCT ano, id_municipio, rede_codigo FROM `{s}.alunos` WHERE avaliado",
            f"SELECT ano, id_municipio, rede_codigo FROM `{s}.resultado_municipio`",
            ["ano", "id_municipio", "rede_codigo"], "combinacoes ano/municipio/rede de alunos avaliados",
        ), ">=", q["match_alunos_resultado_municipio"]),
        Regra("match_meta_municipio_resultado", BLOQUEANTE, _match(
            f"""SELECT ano_publicacao AS ano, id_municipio, rede_codigo FROM `{s}.meta_base`
                WHERE nivel = 'municipio'
                  AND ano_publicacao IN (SELECT DISTINCT ano FROM `{s}.resultado_municipio`)""",
            f"SELECT ano, id_municipio, rede_codigo FROM `{s}.resultado_municipio`",
            ["ano", "id_municipio", "rede_codigo"], "metas municipais",
        ), ">=", q["match_meta_municipio_resultado"]),
        Regra("match_meta_uf_resultado_uf", BLOQUEANTE, _match(
            f"""SELECT ano_publicacao AS ano, sigla_uf, rede_codigo FROM `{s}.meta_base`
                WHERE nivel = 'uf'
                  AND ano_publicacao IN (SELECT DISTINCT ano FROM `{s}.resultado_uf`)""",
            f"SELECT ano, sigla_uf, rede_codigo FROM `{s}.resultado_uf`",
            ["ano", "sigla_uf", "rede_codigo"], "metas de UF",
        ), ">=", limiar_uf),

        # --- Informativas: medem e documentam, nao bloqueiam
        Regra("pct_alunos_nao_avaliados", INFORMATIVA, f"""
SELECT SAFE_DIVIDE(COUNTIF(NOT avaliado), COUNT(*)) AS valor,
       FORMAT('%d de %d alunos fora do denominador (ausentes, prova nao preenchida ou sem peso)',
              COUNTIF(NOT avaliado), COUNT(*)) AS detalhe
FROM `{s}.alunos`"""),
        Regra("ausentes_marcados_nao_alfabetizado_na_fonte", INFORMATIVA,
              conta("NOT presente AND alfabetizado_fonte = 0", "alunos")),
        Regra("alfabetizado_fonte_diverge_do_corte", INFORMATIVA,
              conta("avaliado AND alfabetizado_fonte != IF(alfabetizado, 1, 0)", "alunos")),
        Regra("presente_preenchida_sem_proficiencia", INFORMATIVA,
              conta("presente AND prova_preenchida AND (proficiencia IS NULL OR peso_aluno IS NULL)", "alunos")),
        Regra("caderno_fora_1_21", INFORMATIVA,
              conta("caderno IS NULL OR caderno NOT BETWEEN 1 AND 21", "alunos")),
        Regra("rede_privada_em_alunos", INFORMATIVA, conta("rede_codigo = '4'", "alunos")),
        Regra("pct_resultado_municipal_sem_meta", INFORMATIVA, f"""
WITH r AS (SELECT ano, id_municipio FROM `{s}.resultado_municipio` WHERE rede_codigo = '3'),
     m AS (SELECT DISTINCT ano_publicacao AS ano, id_municipio, TRUE AS tem_meta
           FROM `{s}.meta_base` WHERE nivel = 'municipio')
SELECT SAFE_DIVIDE(COUNTIF(m.tem_meta IS NULL), COUNT(*)) AS valor,
       FORMAT('%d de %d resultados da rede municipal sem meta cadastrada',
              COUNTIF(m.tem_meta IS NULL), COUNT(*)) AS detalhe
FROM r LEFT JOIN m ON m.ano = r.ano AND m.id_municipio = r.id_municipio"""),
        Regra("ufs_sem_resultado", INFORMATIVA, f"""
WITH ufs AS (SELECT sigla_uf FROM `{s}.dim_uf`),
     anos AS (SELECT DISTINCT ano FROM `{s}.resultado_uf`),
     esperado AS (SELECT ano, sigla_uf FROM anos CROSS JOIN ufs),
     existe AS (SELECT DISTINCT ano, sigla_uf, TRUE AS tem FROM `{s}.resultado_uf`)
SELECT COUNTIF(x.tem IS NULL) AS valor,
       FORMAT('UF/ano ausentes em resultado_uf: %s',
              IFNULL(STRING_AGG(IF(x.tem IS NULL, CONCAT(e.sigla_uf, '/', CAST(e.ano AS STRING)), NULL), ', '), '-')) AS detalhe
FROM esperado e LEFT JOIN existe x ON x.ano = e.ano AND x.sigla_uf = e.sigla_uf"""),
        Regra("diferenca_max_taxa_meta_vs_resultado_municipal", INFORMATIVA, f"""
SELECT MAX(ABS(b.taxa_alfabetizacao_publicada - r.taxa_alfabetizacao)) AS valor,
       FORMAT('%d pares comparados; diferenca maxima em pontos percentuais', COUNT(*)) AS detalhe
FROM `{s}.meta_base` b
JOIN `{s}.resultado_municipio` r
  ON r.ano = b.ano_publicacao AND r.id_municipio = b.id_municipio AND r.rede_codigo = b.rede_codigo
WHERE b.nivel = 'municipio'"""),
    ]


STATUS_META_VALIDOS = ("atingiu", "nao_atingiu", "sem_meta", "sem_resultado")


def regras_gold(cfg: Config) -> list[Regra]:
    g = f"{cfg.projeto}.{cfg.datasets['gold_stage']}"

    def duplicados(tabela: str, chaves: str) -> str:
        return f"""
SELECT COUNT(*) - COUNT(DISTINCT TO_JSON_STRING(STRUCT({chaves}))) AS valor,
       FORMAT('%d linhas, chave ({chaves})', COUNT(*)) AS detalhe
FROM `{g}.{tabela}`"""

    def fora_0_100(tabela: str, colunas: list[str]) -> str:
        cond = " OR ".join(f"{c} < 0 OR {c} > 100" for c in colunas)
        return f"SELECT COUNTIF({cond}) AS valor, 'linhas com taxa fora de 0-100 em {tabela}' AS detalhe FROM `{g}.{tabela}`"

    validos = ", ".join(f"'{s}'" for s in STATUS_META_VALIDOS)
    return [
        Regra("indicador_municipio_duplicado", BLOQUEANTE,
              duplicados("indicador_municipio", "ano, id_municipio, rede_codigo"), "==", 0),
        Regra("indicador_uf_duplicado", BLOQUEANTE,
              duplicados("indicador_uf", "ano, sigla_uf, rede_codigo"), "==", 0),
        Regra("indicador_brasil_duplicado", BLOQUEANTE,
              duplicados("indicador_brasil", "ano, rede_codigo"), "==", 0),
        Regra("meta_vs_resultado_duplicado", BLOQUEANTE,
              duplicados("meta_vs_resultado", "nivel, chave, rede_codigo, ano"), "==", 0),
        Regra("features_duplicado", BLOQUEANTE,
              duplicados("features_municipio", "id_municipio, ano_base"), "==", 0),
        Regra("taxa_municipio_fora_0_100", BLOQUEANTE,
              fora_0_100("indicador_municipio", ["taxa_oficial", "taxa_recalculada"]), "==", 0),
        Regra("taxa_uf_fora_0_100", BLOQUEANTE,
              fora_0_100("indicador_uf", ["taxa_oficial", "taxa_recalculada"]), "==", 0),
        Regra("taxa_brasil_fora_0_100", BLOQUEANTE,
              fora_0_100("indicador_brasil", ["taxa_publicada", "taxa_recalculada"]), "==", 0),
        Regra("status_meta_invalido", BLOQUEANTE, f"""
SELECT COUNTIF(status_meta IS NULL OR status_meta NOT IN ({validos})) AS valor,
       'linhas de meta_vs_resultado com status fora do dominio' AS detalhe
FROM `{g}.meta_vs_resultado`""", "==", 0),
        Regra("features_sem_alvo", BLOQUEANTE, f"""
SELECT COUNTIF(alvo_taxa IS NULL) AS valor, FORMAT('%d linhas de features', COUNT(*)) AS detalhe
FROM `{g}.features_municipio`""", "==", 0),

        # Informativas: validacao cruzada com o oficial (insumo do README e do video)
        Regra("recalculo_brasil_dif_max_pp", INFORMATIVA, f"""
SELECT MAX(ABS(dif_recalculo_pp)) AS valor,
       IFNULL(STRING_AGG(FORMAT('%d rede %s: publicada %.2f, recalculada %.2f',
                                ano, rede_codigo, taxa_publicada, taxa_recalculada), '; '), '-') AS detalhe
FROM `{g}.indicador_brasil`
WHERE dif_recalculo_pp IS NOT NULL"""),
        Regra("recalculo_uf_erro_mediano_pp", INFORMATIVA, f"""
SELECT APPROX_QUANTILES(ABS(dif_recalculo_pp), 100)[OFFSET(50)] AS valor,
       FORMAT('%d pares UF/ano/rede comparados', COUNT(*)) AS detalhe
FROM `{g}.indicador_uf` WHERE dif_recalculo_pp IS NOT NULL"""),
        Regra("recalculo_municipio_pct_ate_1pp", INFORMATIVA, f"""
SELECT SAFE_DIVIDE(COUNTIF(ABS(dif_recalculo_pp) <= 1), COUNT(*)) AS valor,
       FORMAT('%d pares municipio/ano/rede comparados', COUNT(*)) AS detalhe
FROM `{g}.indicador_municipio` WHERE dif_recalculo_pp IS NOT NULL"""),
        Regra("municipios_sem_meta_ou_resultado", INFORMATIVA, f"""
SELECT COUNTIF(status_meta IN ('sem_meta', 'sem_resultado')) AS valor,
       FORMAT('sem_meta=%d, sem_resultado=%d (nivel municipio)',
              COUNTIF(status_meta = 'sem_meta'), COUNTIF(status_meta = 'sem_resultado')) AS detalhe
FROM `{g}.meta_vs_resultado` WHERE nivel = 'municipio'"""),
    ]


def regras_stream(cfg: Config) -> list[Regra]:
    s = f"{cfg.projeto}.{cfg.datasets['silver']}"
    o = f"{cfg.projeto}.{cfg.datasets['ops']}"
    st = f"{cfg.projeto}.{cfg.datasets['silver_stage']}"
    return [
        Regra("stream_event_id_duplicado", BLOQUEANTE, f"""
SELECT COUNT(*) - COUNT(DISTINCT event_id) AS valor,
       FORMAT('%d eventos na Silver do streaming', COUNT(*)) AS detalhe
FROM `{s}.eventos_resultado_municipio`""", "==", 0),
        Regra("stream_message_id_duplicado", BLOQUEANTE, f"""
SELECT COUNT(*) - COUNT(DISTINCT message_id) AS valor,
       FORMAT('%d mensagens no livro-razao', COUNT(*)) AS detalhe
FROM `{o}.stream_mensagens`""", "==", 0),
        Regra("stream_origem_nao_simulada", BLOQUEANTE, f"""
SELECT COUNTIF(origem IS NULL OR origem != 'simulado') AS valor,
       'eventos do streaming sem origem = simulado' AS detalhe
FROM `{s}.eventos_resultado_municipio`""", "==", 0),
        Regra("stream_taxa_fora_0_100", BLOQUEANTE, f"""
SELECT COUNTIF(taxa_alfabetizacao < 0 OR taxa_alfabetizacao > 100) AS valor,
       'eventos com taxa fora de 0-100' AS detalhe
FROM `{s}.eventos_resultado_municipio`""", "==", 0),
        Regra("stream_lote_pct_invalidos", INFORMATIVA, f"""
SELECT SAFE_DIVIDE(COUNTIF(resultado = 'invalido'), COUNT(*)) AS valor,
       IFNULL(STRING_AGG(DISTINCT motivo_invalido), '-') AS detalhe
FROM `{st}.stream_lote`"""),
        Regra("stream_lote_pct_duplicados", INFORMATIVA, f"""
SELECT SAFE_DIVIDE(COUNTIF(resultado = 'duplicado'), COUNT(*)) AS valor,
       FORMAT('%d duplicados de %d mensagens', COUNTIF(resultado = 'duplicado'), COUNT(*)) AS detalhe
FROM `{st}.stream_lote`"""),
    ]


def validar_stream(cfg: Config, bq: BQ, run_id: str) -> list[dict]:
    return validar(cfg, bq, run_id, "stream", regras_stream(cfg))


def validar_silver(cfg: Config, bq: BQ, run_id: str, forcar_falha: bool = False) -> list[dict]:
    if forcar_falha:
        log("WARNING", "forcar_falha ativo: limiar de match_meta_uf_resultado_uf elevado para 1.0")
    return validar(cfg, bq, run_id, "silver", regras_silver(cfg, forcar_falha))


def validar_gold(cfg: Config, bq: BQ, run_id: str) -> list[dict]:
    return validar(cfg, bq, run_id, "gold", regras_gold(cfg))


def validar(cfg: Config, bq: BQ, run_id: str, camada: str, regras: list[Regra]) -> list[dict]:
    agora = datetime.now(timezone.utc).isoformat()
    resultados = []
    for regra in regras:
        linha = bq.valor(regra.sql, f"qualidade: {regra.nome}")
        valor = None if linha["valor"] is None else float(linha["valor"])
        aprovada = avaliar(valor, regra.operador, regra.limiar)
        resultados.append({
            "run_id": run_id,
            "executado_em": agora,
            "camada": camada,
            "regra": regra.nome,
            "tipo": regra.tipo,
            "valor": valor,
            "operador": regra.operador,
            "limiar": regra.limiar,
            "aprovada": aprovada,
            "detalhe": linha["detalhe"],
        })
        log("INFO" if aprovada else ("ERROR" if regra.tipo == BLOQUEANTE else "WARNING"),
            f"regra {regra.nome}", tipo=regra.tipo, valor=valor, limiar=regra.limiar, aprovada=aprovada)

    # Grava TODAS as regras antes de decidir, para o resultado sobreviver ao fim da execucao.
    bq.anexar_linhas(cfg.tabela("ops", "dq_resultados"), resultados, DQ_RESULTADOS)

    reprovadas = [r["regra"] for r in resultados if r["tipo"] == BLOQUEANTE and not r["aprovada"]]
    if reprovadas:
        raise FalhaBloqueante(f"regras bloqueantes reprovadas: {', '.join(reprovadas)}")
    return resultados
