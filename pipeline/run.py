"""Ponto de entrada do pipeline batch.

Exemplos:
  python -m pipeline.run                            # execucao completa: bronze, silver e gold
  python -m pipeline.run --etapas silver            # reconstroi a Silver da ultima Bronze completa
  python -m pipeline.run --etapas silver --forcar-falha   # demonstra o bloqueio da qualidade

Saida com codigo 0 = sucesso. Qualquer falha (inclusive regra bloqueante) termina com codigo != 0.
"""
import argparse
import sys

from . import bronze, gold, silver
from .bq import BQ, log
from .config import carregar, novo_run_id, validar_run_id
from .metricas import Execucao

ETAPAS_VALIDAS = ("bronze", "silver", "gold")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Pipeline batch do Tech Challenge")
    parser.add_argument("--etapas", default="bronze,silver,gold",
                        help=f"lista separada por virgula entre {ETAPAS_VALIDAS}")
    parser.add_argument("--bronze-run-id", help="run_id da Bronze a usar (padrao: a mais recente completa)")
    parser.add_argument("--forcar-falha", action="store_true",
                        help="eleva um limiar de qualidade para provar que a regra bloqueante interrompe o pipeline")
    args = parser.parse_args(argv)

    etapas = [e.strip() for e in args.etapas.split(",") if e.strip()]
    invalidas = set(etapas) - set(ETAPAS_VALIDAS)
    if invalidas:
        parser.error(f"etapas invalidas: {invalidas}")

    cfg = carregar()
    bq = BQ(cfg)
    run_id = novo_run_id()
    execucao = Execucao(bq, pipeline="batch", run_id=run_id)
    log("INFO", "pipeline iniciado", run_id=run_id, etapas=etapas)

    try:
        if "bronze" in etapas:
            bronze.executar(cfg, bq, execucao, run_id)
            bronze_run_id = run_id
        elif "silver" in etapas:
            bronze_run_id = validar_run_id(args.bronze_run_id) if args.bronze_run_id else bronze.ultimo_run_id(cfg)

        if "silver" in etapas:
            log("INFO", "silver a partir da bronze", bronze_run_id=bronze_run_id)
            silver.executar(cfg, bq, execucao, bronze_run_id, forcar_falha=args.forcar_falha)

        if "gold" in etapas:
            # A Gold le a Silver PUBLICADA: so dado que passou nas regras bloqueantes.
            gold.executar(cfg, bq, execucao)
    except Exception as exc:
        # Registra o encerramento com severidade ERROR (gatilho do alerta) e REPASSA a excecao.
        log("ERROR", "pipeline falhou", run_id=run_id, erro=f"{type(exc).__name__}: {exc}",
            bytes_faturados=bq.bytes_faturados)
        raise

    log("INFO", "pipeline concluido", run_id=run_id, bytes_faturados=bq.bytes_faturados)
    return 0


if __name__ == "__main__":
    sys.exit(main())
