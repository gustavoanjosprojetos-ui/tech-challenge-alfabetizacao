"""Metricas de execucao persistidas em ops.pipeline_execucoes (uma linha por etapa, em APPEND)."""
from contextlib import contextmanager
from datetime import datetime, timezone

from .bq import BQ, log
from .schemas import PIPELINE_EXECUCOES


class Execucao:
    def __init__(self, bq: BQ, pipeline: str, run_id: str):
        self.bq = bq
        self.pipeline = pipeline
        self.run_id = run_id
        self.tabela = bq.cfg.tabela("ops", "pipeline_execucoes")

    @contextmanager
    def etapa(self, nome: str):
        """Mede a etapa e grava o resultado, com sucesso ou falha.

        O chamador preenche reg["linhas_entrada"] e reg["linhas_saida"].
        Em caso de falha a excecao e REPASSADA depois de gravada: o processo termina com erro.
        """
        inicio = datetime.now(timezone.utc)
        bytes_antes = self.bq.bytes_faturados
        reg = {"linhas_entrada": None, "linhas_saida": None}
        status, erro = "falha", None
        log("INFO", f"inicio {nome}", run_id=self.run_id)
        try:
            yield reg
            status = "sucesso"
        except BaseException as exc:
            erro = f"{type(exc).__name__}: {exc}"[:2000]
            log("ERROR", f"falha {nome}", run_id=self.run_id, erro=erro)
            raise
        finally:
            fim = datetime.now(timezone.utc)
            linha = {
                "run_id": self.run_id,
                "pipeline": self.pipeline,
                "etapa": nome,
                "status": status,
                "inicio": inicio.isoformat(),
                "fim": fim.isoformat(),
                "duracao_s": round((fim - inicio).total_seconds(), 3),
                "linhas_entrada": reg["linhas_entrada"],
                "linhas_saida": reg["linhas_saida"],
                "bytes_faturados": self.bq.bytes_faturados - bytes_antes,
                "erro": erro,
            }
            self._gravar(linha)

    def _gravar(self, linha: dict):
        # Se a propria gravacao da metrica falhar, registramos em log de erro e seguimos:
        # a excecao original da etapa (se houver) continua subindo e encerra o processo.
        try:
            self.bq.anexar_linhas(self.tabela, [linha], PIPELINE_EXECUCOES)
        except Exception as exc:  # noqa: BLE001 - falha so da metrica, nao da etapa
            log("ERROR", "nao foi possivel gravar metrica", etapa=linha["etapa"], erro=str(exc))
