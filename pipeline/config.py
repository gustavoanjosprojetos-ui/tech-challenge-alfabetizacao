"""Carrega a configuracao do pipeline (config.toml + variaveis de ambiente)."""
import os
import re
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
RUN_ID_RE = re.compile(r"^\d{8}T\d{6}Z$")


@dataclass(frozen=True)
class Config:
    projeto: str
    localizacao: str
    bucket: str
    fonte_dataset: str
    datasets: dict
    tabelas_fonte: list
    max_gb_por_query: float
    corte_alfabetizacao: int
    qualidade: dict
    streaming: dict = field(default_factory=dict)

    def tabela(self, camada: str, nome: str) -> str:
        return f"{self.projeto}.{self.datasets[camada]}.{nome}"


def carregar(caminho: str | None = None) -> Config:
    caminho = Path(caminho or os.environ.get("PIPELINE_CONFIG", RAIZ / "config.toml"))
    if not caminho.exists():
        raise SystemExit(
            f"Config nao encontrada em {caminho}. Copie config.example.toml para config.toml."
        )
    dados = tomllib.loads(caminho.read_text(encoding="utf-8"))
    dados["projeto"] = os.environ.get("GCP_PROJECT") or dados.get("projeto")
    dados["bucket"] = os.environ.get("GCS_BUCKET") or dados.get("bucket")
    # gold_stage foi adicionado depois; configs antigas continuam funcionando.
    dados.setdefault("datasets", {}).setdefault("gold_stage", "gold_stage")
    streaming = dados.setdefault("streaming", {})
    streaming.setdefault("topico", "alfabetizacao-eventos")
    streaming.setdefault("assinatura", "alfabetizacao-eventos-bronze")
    streaming.setdefault("janela_horas", 48)
    for chave in ("projeto", "bucket"):
        if not dados.get(chave):
            raise SystemExit(f"Defina '{chave}' em {caminho} ou por variavel de ambiente.")
    return Config(**dados)


def novo_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def validar_run_id(run_id: str) -> str:
    """run_id entra em SQL e em caminhos do GCS, entao so aceita o formato gerado aqui."""
    if not RUN_ID_RE.match(run_id or ""):
        raise ValueError(f"run_id invalido: {run_id!r} (esperado AAAAMMDDTHHMMSSZ)")
    return run_id


def data_ingestao(run_id: str) -> str:
    validar_run_id(run_id)
    return f"{run_id[0:4]}-{run_id[4:6]}-{run_id[6:8]}"
