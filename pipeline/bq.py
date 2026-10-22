"""Acesso ao BigQuery com trava de custo (dry run) e contabilizacao de bytes."""
import json
import sys
from string import Template

from google.cloud import bigquery

from .config import RAIZ, Config


def log(severity: str, mensagem: str, **campos):
    """Log estruturado em JSON: o Cloud Logging le o campo 'severity' quando roda na nuvem."""
    print(
        json.dumps({"severity": severity, "message": mensagem, **campos}, default=str, ensure_ascii=False),
        file=sys.stderr if severity in ("ERROR", "CRITICAL") else sys.stdout,
        flush=True,
    )


def render_sql(caminho_relativo: str, **variaveis) -> str:
    """Le um arquivo de sql/ e substitui ${variavel}. Variavel faltando gera erro."""
    texto = (RAIZ / "sql" / caminho_relativo).read_text(encoding="utf-8")
    return Template(texto).substitute(**variaveis)


class CustoExcedido(RuntimeError):
    pass


class BQ:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.client = bigquery.Client(project=cfg.projeto, location=cfg.localizacao)
        self.bytes_faturados = 0
        self.limite_bytes = int(cfg.max_gb_por_query * 1e9)

    def executar(self, sql: str, descricao: str, sql_dry_run: str | None = None, dry_run: bool = True):
        """Executa uma query depois de medir o custo com dry run.

        sql_dry_run: query alternativa para o dry run (ex.: o SELECT de um EXPORT DATA).
        dry_run=False: so para DDL que nao le dados (ex.: definir tabela externa).
        """
        previsto = 0
        if dry_run:
            seco = self.client.query(
                sql_dry_run or sql,
                job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False),
            )
            previsto = seco.total_bytes_processed or 0
            if previsto > self.limite_bytes:
                raise CustoExcedido(
                    f"{descricao}: dry run previu {previsto / 1e9:.2f} GB, acima de "
                    f"max_gb_por_query={self.cfg.max_gb_por_query}"
                )
        job = self.client.query(
            sql,
            job_config=bigquery.QueryJobConfig(
                maximum_bytes_billed=max(self.limite_bytes, 10 * 1024**2)
            ),
        )
        resultado = job.result()
        faturado = job.total_bytes_billed or 0
        self.bytes_faturados += faturado
        log("INFO", descricao, job_id=job.job_id, bytes_dry_run=previsto, bytes_faturados=faturado)
        return job, resultado

    def valor(self, sql: str, descricao: str):
        """Executa uma query de uma linha e devolve a linha como dict."""
        _, resultado = self.executar(sql, descricao)
        linhas = [dict(r.items()) for r in resultado]
        if len(linhas) != 1:
            raise RuntimeError(f"{descricao}: esperava 1 linha, veio {len(linhas)}")
        return linhas[0]

    def anexar_linhas(self, tabela: str, linhas: list[dict], schema: list):
        """Grava linhas em modo APPEND via load job (gratis, ao contrario do streaming insert)."""
        if not linhas:
            return
        job = self.client.load_table_from_json(
            linhas,
            tabela,
            job_config=bigquery.LoadJobConfig(
                schema=schema, write_disposition=bigquery.WriteDisposition.WRITE_APPEND
            ),
        )
        job.result()
