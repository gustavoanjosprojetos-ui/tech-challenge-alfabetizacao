"""Bronze: copia bruta das 7 tabelas da fonte para Parquet no GCS, sem sobrescrever execucoes anteriores.

Layout: gs://<bucket>/bronze/<tabela>/ingestion_date=AAAA-MM-DD/run_id=<run_id>/part-*.parquet
Cada execucao escreve num caminho novo (run_id unico). Nada e apagado ou sobrescrito:
- o caminho e verificado vazio antes da exportacao;
- EXPORT DATA roda com overwrite=false, entao falha se houver arquivo no destino.
As tabelas bronze.<tabela> sao externas, com particao hive (ingestion_date, run_id)
sobre todas as execucoes ja gravadas.
"""
import re

from google.cloud import storage

from .bq import BQ
from .config import Config, data_ingestao, validar_run_id
from .metricas import Execucao


class HistoricoEmRisco(RuntimeError):
    pass


class BronzeIncompleta(RuntimeError):
    pass


def prefixo(tabela: str, run_id: str) -> str:
    return f"bronze/{tabela}/ingestion_date={data_ingestao(run_id)}/run_id={run_id}"


def criar_tabela_externa(bq: BQ, cfg: Config, tabela: str):
    raiz = f"gs://{cfg.bucket}/bronze/{tabela}"
    sql = f"""
CREATE OR REPLACE EXTERNAL TABLE `{cfg.tabela('bronze', tabela)}`
WITH PARTITION COLUMNS (ingestion_date DATE, run_id STRING)
OPTIONS (
  format = 'PARQUET',
  uris = ['{raiz}/*'],
  hive_partition_uri_prefix = '{raiz}'
)"""
    # Redefine apenas o metadado da tabela externa; os arquivos no GCS nao sao tocados.
    bq.executar(sql, f"bronze.{tabela}: definir tabela externa", dry_run=False)


def executar(cfg: Config, bq: BQ, execucao: Execucao, run_id: str):
    validar_run_id(run_id)
    gcs = storage.Client(project=cfg.projeto)
    for tabela in cfg.tabelas_fonte:
        with execucao.etapa(f"bronze.{tabela}") as reg:
            fonte = f"{cfg.fonte_dataset}.{tabela}"
            reg["linhas_entrada"] = bq.client.get_table(fonte).num_rows  # metadado, sem custo

            destino = prefixo(tabela, run_id)
            if any(gcs.list_blobs(cfg.bucket, prefix=destino + "/", max_results=1)):
                raise HistoricoEmRisco(f"gs://{cfg.bucket}/{destino} ja tem arquivos; nada foi sobrescrito")

            select = f"SELECT *, CURRENT_TIMESTAMP() AS _ingerido_em FROM `{fonte}`"
            export = f"""
EXPORT DATA OPTIONS (
  uri = 'gs://{cfg.bucket}/{destino}/part-*.parquet',
  format = 'PARQUET',
  compression = 'SNAPPY',
  overwrite = false
) AS {select}"""
            bq.executar(export, f"bronze.{tabela}: exportar para GCS", sql_dry_run=select)
            criar_tabela_externa(bq, cfg, tabela)

            contagem = bq.valor(
                f"SELECT COUNT(*) AS n FROM `{cfg.tabela('bronze', tabela)}` WHERE run_id = '{run_id}'",
                f"bronze.{tabela}: contar linhas gravadas",
            )
            reg["linhas_saida"] = contagem["n"]
            if reg["linhas_saida"] != reg["linhas_entrada"]:
                raise BronzeIncompleta(
                    f"{tabela}: fonte tem {reg['linhas_entrada']} linhas, bronze gravou {reg['linhas_saida']}"
                )


def ultimo_run_id(cfg: Config) -> str:
    """run_id mais recente presente em TODAS as tabelas da Bronze (lista o GCS, sem custo de query).

    Uma execucao que falhou no meio deixa algumas tabelas sem aquele run_id;
    exigir a intersecao evita que a Silver leia uma Bronze incompleta.
    """
    gcs = storage.Client(project=cfg.projeto)
    padrao = re.compile(r"run_id=(\d{8}T\d{6}Z)/")
    completos = None
    for tabela in cfg.tabelas_fonte:
        runs = {
            m.group(1)
            for blob in gcs.list_blobs(cfg.bucket, prefix=f"bronze/{tabela}/")
            if (m := padrao.search(blob.name))
        }
        completos = runs if completos is None else completos & runs
    if not completos:
        raise RuntimeError("Nenhuma execucao completa da Bronze encontrada. Rode a etapa bronze antes.")
    return max(completos)
