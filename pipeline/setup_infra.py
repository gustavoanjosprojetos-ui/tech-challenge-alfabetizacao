"""Cria bucket, datasets e tabelas operacionais. Idempotente: pode rodar varias vezes.

Uso: python -m pipeline.setup_infra
"""
from google.api_core.exceptions import Conflict, NotFound
from google.cloud import bigquery, storage

from .bq import log
from .config import carregar
from .schemas import TABELAS_OPS


def main():
    cfg = carregar()

    gcs = storage.Client(project=cfg.projeto)
    try:
        gcs.get_bucket(cfg.bucket)
        log("INFO", "bucket ja existe", bucket=cfg.bucket)
    except NotFound:
        bucket = gcs.bucket(cfg.bucket)
        bucket.iam_configuration.uniform_bucket_level_access_enabled = True
        gcs.create_bucket(bucket, location=cfg.localizacao)
        log("INFO", "bucket criado", bucket=cfg.bucket, localizacao=cfg.localizacao)

    bq = bigquery.Client(project=cfg.projeto, location=cfg.localizacao)
    for camada, nome in cfg.datasets.items():
        ds = bigquery.Dataset(f"{cfg.projeto}.{nome}")
        ds.location = cfg.localizacao
        ds.labels = {"projeto": "tech-challenge", "camada": camada.replace("_", "-")}
        try:
            bq.create_dataset(ds)
            log("INFO", "dataset criado", dataset=nome)
        except Conflict:
            log("INFO", "dataset ja existe", dataset=nome)

    for nome, (schema, coluna_particao) in TABELAS_OPS.items():
        tabela = bigquery.Table(cfg.tabela("ops", nome), schema=schema)
        tabela.time_partitioning = bigquery.TimePartitioning(field=coluna_particao)
        try:
            bq.create_table(tabela)
            log("INFO", "tabela ops criada", tabela=nome)
        except Conflict:
            log("INFO", "tabela ops ja existe", tabela=nome)


if __name__ == "__main__":
    main()
