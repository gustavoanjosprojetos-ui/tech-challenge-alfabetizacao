"""Esquemas das tabelas operacionais (dataset ops). Todas recebem apenas APPEND."""
from google.cloud.bigquery import SchemaField as F

PIPELINE_EXECUCOES = [
    F("run_id", "STRING", mode="REQUIRED"),
    F("pipeline", "STRING", mode="REQUIRED"),
    F("etapa", "STRING", mode="REQUIRED"),
    F("status", "STRING", mode="REQUIRED"),
    F("inicio", "TIMESTAMP", mode="REQUIRED"),
    F("fim", "TIMESTAMP"),
    F("duracao_s", "FLOAT64"),
    F("linhas_entrada", "INT64"),
    F("linhas_saida", "INT64"),
    F("bytes_faturados", "INT64"),
    F("erro", "STRING"),
]

DQ_RESULTADOS = [
    F("run_id", "STRING", mode="REQUIRED"),
    F("executado_em", "TIMESTAMP", mode="REQUIRED"),
    F("camada", "STRING", mode="REQUIRED"),
    F("regra", "STRING", mode="REQUIRED"),
    F("tipo", "STRING", mode="REQUIRED"),
    F("valor", "FLOAT64"),
    F("operador", "STRING"),
    F("limiar", "FLOAT64"),
    F("aprovada", "BOOL", mode="REQUIRED"),
    F("detalhe", "STRING"),
]

TABELAS_OPS = {
    "pipeline_execucoes": (PIPELINE_EXECUCOES, "inicio"),
    "dq_resultados": (DQ_RESULTADOS, "executado_em"),
}

# --- Streaming
# Bronze do streaming: formato fixo da assinatura BigQuery do Pub/Sub com writeMetadata.
BRONZE_EVENTOS_STREAM = [
    F("subscription_name", "STRING"),
    F("message_id", "STRING"),
    F("publish_time", "TIMESTAMP"),
    F("data", "STRING"),
    F("attributes", "STRING"),
]

SILVER_EVENTOS = [
    F("event_id", "STRING", mode="REQUIRED"),
    F("message_id", "STRING"),
    F("lote_id", "STRING"),
    F("event_time", "TIMESTAMP"),
    F("publish_time", "TIMESTAMP"),
    F("processado_em", "TIMESTAMP"),
    F("ano", "INT64"),
    F("id_municipio", "STRING"),
    F("sigla_uf", "STRING"),
    F("rede_codigo", "STRING"),
    F("serie", "STRING"),
    F("n_avaliados", "INT64"),
    F("n_alfabetizados", "INT64"),
    F("taxa_alfabetizacao", "FLOAT64"),
    F("origem", "STRING"),
]

OPS_EVENTOS_INVALIDOS = [
    F("message_id", "STRING", mode="REQUIRED"),
    F("lote_id", "STRING"),
    F("publish_time", "TIMESTAMP"),
    F("motivo", "STRING"),
    F("data", "STRING"),
    F("registrado_em", "TIMESTAMP"),
]

# Livro-razao: cada mensagem do Pub/Sub e classificada exatamente uma vez.
OPS_STREAM_MENSAGENS = [
    F("message_id", "STRING", mode="REQUIRED"),
    F("event_id", "STRING"),
    F("lote_id", "STRING"),
    F("resultado", "STRING"),
    F("publish_time", "TIMESTAMP"),
    F("processado_em", "TIMESTAMP"),
]

OPS_STREAM_LOTES = [
    F("lote_id", "STRING", mode="REQUIRED"),
    F("processado_em", "TIMESTAMP", mode="REQUIRED"),
    F("mensagens_novas", "INT64"),
    F("inseridos", "INT64"),
    F("duplicados", "INT64"),
    F("invalidos", "INT64"),
    F("latencia_ingestao_media_s", "FLOAT64"),
    F("latencia_ponta_media_s", "FLOAT64"),
    F("latencia_ponta_p50_s", "FLOAT64"),
    F("latencia_ponta_p95_s", "FLOAT64"),
    F("latencia_ponta_max_s", "FLOAT64"),
]

# camada -> {tabela: (schema, coluna de particao, colunas de cluster)}
TABELAS_STREAMING = {
    "bronze": {"eventos_stream": (BRONZE_EVENTOS_STREAM, "publish_time", None)},
    "silver": {"eventos_resultado_municipio": (SILVER_EVENTOS, "event_time", ["id_municipio"])},
    "ops": {
        "eventos_invalidos": (OPS_EVENTOS_INVALIDOS, "publish_time", None),
        "stream_mensagens": (OPS_STREAM_MENSAGENS, "publish_time", None),
        "stream_lotes": (OPS_STREAM_LOTES, "processado_em", None),
    },
}
