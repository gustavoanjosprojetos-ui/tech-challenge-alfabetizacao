"""Cria a infraestrutura do streaming. Idempotente: pode rodar varias vezes.

- tabelas: bronze.eventos_stream, silver.eventos_resultado_municipio e as tabelas ops do streaming
- permissao: o agente de servico do Pub/Sub pode gravar no dataset bronze
- topico Pub/Sub e assinatura BigQuery que grava cada mensagem em bronze.eventos_stream

Pre-requisito: gcloud services enable pubsub.googleapis.com
Uso: python -m pipeline.setup_streaming
"""
import re
import time

from google.api_core.exceptions import Conflict
from google.cloud import bigquery

from .bq import log
from .config import carregar
from .pubsub_rest import ErroPubSub, PubSub
from .schemas import TABELAS_STREAMING


def numero_do_projeto(bq: bigquery.Client) -> str:
    """O e-mail da conta de servico do BigQuery contem o numero do projeto: bq-<numero>@..."""
    email = bq.get_service_account_email()
    m = re.match(r"bq-(\d+)@", email)
    if not m:
        raise RuntimeError(f"Nao foi possivel obter o numero do projeto a partir de {email}")
    return m.group(1)


def criar_tabelas(cfg, bq: bigquery.Client):
    for camada, tabelas in TABELAS_STREAMING.items():
        for nome, (schema, particao, cluster) in tabelas.items():
            tabela = bigquery.Table(cfg.tabela(camada, nome), schema=schema)
            tabela.time_partitioning = bigquery.TimePartitioning(field=particao)
            if cluster:
                tabela.clustering_fields = cluster
            try:
                bq.create_table(tabela)
                log("INFO", "tabela criada", tabela=f"{camada}.{nome}")
            except Conflict:
                log("INFO", "tabela ja existe", tabela=f"{camada}.{nome}")


def liberar_escrita_pubsub(cfg, bq: bigquery.Client, email: str):
    dataset = bq.get_dataset(f"{cfg.projeto}.{cfg.datasets['bronze']}")
    entradas = list(dataset.access_entries)
    if any(e.entity_id == email and e.role == "WRITER" for e in entradas):
        log("INFO", "Pub/Sub ja pode gravar no dataset bronze", conta=email)
        return
    entradas.append(bigquery.AccessEntry(role="WRITER", entity_type="userByEmail", entity_id=email))
    dataset.access_entries = entradas
    bq.update_dataset(dataset, ["access_entries"])
    log("INFO", "permissao de escrita concedida ao Pub/Sub no dataset bronze", conta=email)


def main():
    cfg = carregar()
    s = cfg.streaming
    bq = bigquery.Client(project=cfg.projeto, location=cfg.localizacao)

    criar_tabelas(cfg, bq)

    numero = numero_do_projeto(bq)
    agente_pubsub = f"service-{numero}@gcp-sa-pubsub.iam.gserviceaccount.com"
    liberar_escrita_pubsub(cfg, bq, agente_pubsub)

    ps = PubSub(cfg.projeto)
    criado = ps.criar_topico(s["topico"])
    log("INFO", "topico criado" if criado else "topico ja existe", topico=s["topico"])

    tabela_bronze = f"{cfg.projeto}.{cfg.datasets['bronze']}.eventos_stream"
    # A permissao recem-concedida pode levar alguns segundos para valer: tentamos algumas vezes.
    for tentativa in range(1, 7):
        try:
            criada = ps.criar_assinatura_bigquery(s["assinatura"], s["topico"], tabela_bronze)
            log("INFO", "assinatura criada" if criada else "assinatura ja existe",
                assinatura=s["assinatura"], destino=tabela_bronze)
            return
        except ErroPubSub as exc:
            if tentativa == 6:
                raise
            log("WARNING", "assinatura ainda sem permissao; nova tentativa em 15 s",
                tentativa=tentativa, erro=str(exc)[:300])
            time.sleep(15)


if __name__ == "__main__":
    main()
