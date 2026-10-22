"""Gold: datasets analiticos construidos a partir da Silver PUBLICADA (so dado aprovado).

Mesmo padrao da Silver: constroi em gold_stage, valida e so entao publica em gold.
Tabelas (ver sql/gold): indicadores por municipio, UF e Brasil (oficial x recalculado),
meta x resultado com estados distintos, resumo executivo, validacao do recalculo e a
base de features para a Fase 3.
"""
from . import camadas, qualidade
from .bq import BQ
from .config import Config
from .metricas import Execucao

CAMADA = "gold"
ARQUIVOS = camadas.arquivos(CAMADA)


def variaveis(cfg: Config) -> dict:
    return {
        "projeto": cfg.projeto,
        "silver": cfg.datasets["silver"],
        "stage": cfg.datasets["gold_stage"],
    }


def executar(cfg: Config, bq: BQ, execucao: Execucao):
    camadas.construir(cfg, bq, execucao, CAMADA, "gold_stage", variaveis(cfg))
    with execucao.etapa("qualidade.gold") as reg:
        resultados = qualidade.validar_gold(cfg, bq, execucao.run_id)
        reg["linhas_saida"] = len(resultados)
    camadas.publicar(cfg, bq, execucao, CAMADA, "gold_stage", "gold")
