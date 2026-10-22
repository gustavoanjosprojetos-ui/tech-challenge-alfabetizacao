"""Silver: constroi em silver_stage, valida e so entao publica em silver.

Politica de escrita: a Silver e um retrato derivado da Bronze de um run_id. Cada execucao
reconstroi as tabelas (CREATE OR REPLACE) no dataset de stage. O historico fica na Bronze,
que nunca e sobrescrita. A publicacao em silver acontece por copia (gratuita) e SO depois que
todas as regras bloqueantes passam; se alguma falhar, silver continua com a ultima versao aprovada.
"""
from . import camadas, qualidade
from .bq import BQ
from .config import Config, validar_run_id
from .metricas import Execucao

CAMADA = "silver"
ARQUIVOS = camadas.arquivos(CAMADA)
tabela_do_arquivo = camadas.tabela_do_arquivo


def variaveis(cfg: Config, run_id: str) -> dict:
    return {
        "projeto": cfg.projeto,
        "bronze": cfg.datasets["bronze"],
        "stage": cfg.datasets["silver_stage"],
        "run_id": validar_run_id(run_id),
        "corte": int(cfg.corte_alfabetizacao),
    }


def executar(cfg: Config, bq: BQ, execucao: Execucao, run_id: str, forcar_falha: bool = False):
    camadas.construir(cfg, bq, execucao, CAMADA, "silver_stage", variaveis(cfg, run_id))
    with execucao.etapa("qualidade.silver") as reg:
        resultados = qualidade.validar_silver(cfg, bq, execucao.run_id, forcar_falha=forcar_falha)
        reg["linhas_saida"] = len(resultados)
    # Se uma regra bloqueante falhou, a excecao ja subiu e a publicacao nao roda.
    camadas.publicar(cfg, bq, execucao, CAMADA, "silver_stage", "silver")
