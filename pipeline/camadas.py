"""Padrao comum de Silver e Gold: construir no stage, validar, publicar por copia.

Cada arquivo sql/<camada>/NN_<tabela>.sql cria a tabela <tabela> no dataset de stage.
A publicacao copia (operacao gratuita) as tabelas do stage para o dataset final,
e so roda depois que todas as regras bloqueantes passaram.
"""
from google.cloud import bigquery

from .bq import BQ, render_sql
from .config import RAIZ, Config
from .metricas import Execucao


def arquivos(camada: str) -> list[str]:
    return sorted(p.name for p in (RAIZ / "sql" / camada).glob("*.sql"))


def tabela_do_arquivo(nome_arquivo: str) -> str:
    return nome_arquivo.split("_", 1)[1].removesuffix(".sql")


def construir(cfg: Config, bq: BQ, execucao: Execucao, camada: str, stage: str, variaveis: dict):
    for arquivo in arquivos(camada):
        tabela = tabela_do_arquivo(arquivo)
        with execucao.etapa(f"{camada}.{tabela}") as reg:
            bq.executar(render_sql(f"{camada}/{arquivo}", **variaveis), f"{stage}.{tabela}")
            reg["linhas_saida"] = bq.client.get_table(cfg.tabela(stage, tabela)).num_rows


def publicar(cfg: Config, bq: BQ, execucao: Execucao, camada: str, stage: str, destino: str):
    for arquivo in arquivos(camada):
        tabela = tabela_do_arquivo(arquivo)
        with execucao.etapa(f"{camada}.publicar.{tabela}") as reg:
            origem_id = cfg.tabela(stage, tabela)
            destino_id = cfg.tabela(destino, tabela)
            bq.client.copy_table(
                origem_id,
                destino_id,
                job_config=bigquery.CopyJobConfig(
                    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
                ),
            ).result()
            reg["linhas_entrada"] = bq.client.get_table(origem_id).num_rows
            reg["linhas_saida"] = bq.client.get_table(destino_id).num_rows
