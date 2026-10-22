"""Configura o alerta de falha por e-mail no Cloud Monitoring. Idempotente.

Politica baseada em log: dispara quando um Cloud Run Job do pipeline ou o workflow de
orquestracao escreve um log com severidade ERROR. O pipeline escreve
{"severity": "ERROR", "message": "pipeline falhou", ...} em qualquer falha, inclusive
quando uma regra de qualidade bloqueante reprova; se o processo morrer antes disso,
o proprio Cloud Run e o Workflows registram a falha da execucao com severidade ERROR.

Uso: python -m pipeline.setup_alerta --email voce@exemplo.com
"""
import argparse
import re

import google.auth
from google.auth.transport.requests import AuthorizedSession

from .bq import log
from .config import carregar

API = "https://monitoring.googleapis.com/v3"
NOME_POLITICA = "Pipeline alfabetizacao - falha"
FILTRO_LOG = (
    '(resource.type="cloud_run_job" AND '
    '(resource.labels.job_name="pipeline-batch" OR resource.labels.job_name="pipeline-streaming") '
    'AND severity>=ERROR) OR '
    '(resource.type="workflows.googleapis.com/Workflow" AND severity>=ERROR)'
)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def politica(canal: str) -> dict:
    return {
        "displayName": NOME_POLITICA,
        "combiner": "OR",
        "conditions": [{
            "displayName": "Log de erro do pipeline (Cloud Run Job ou Workflows)",
            "conditionMatchedLog": {"filter": FILTRO_LOG},
        }],
        # Alertas de log exigem um limite de notificacoes: no maximo 1 e-mail a cada 5 minutos.
        "alertStrategy": {"notificationRateLimit": {"period": "300s"}, "autoClose": "1800s"},
        "notificationChannels": [canal],
        "documentation": {
            "mimeType": "text/markdown",
            "content": (
                "O pipeline de alfabetizacao falhou.\n\n"
                "1. Abra o Logs Explorer e filtre por `jsonPayload.message=\"pipeline falhou\"`.\n"
                "2. O campo `erro` diz a etapa e a causa (ex.: regra bloqueante reprovada).\n"
                "3. Consulte `ops.pipeline_execucoes` e `ops.dq_resultados` pelo `run_id`."
            ),
        },
    }


def _checar(r):
    if r.status_code >= 400:
        raise RuntimeError(f"Monitoring HTTP {r.status_code}: {r.text[:800]}")
    return r.json()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    args = parser.parse_args(argv)
    if not EMAIL_RE.match(args.email):
        parser.error(f"e-mail invalido: {args.email}")

    cfg = carregar()
    cred, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    s = AuthorizedSession(cred)
    base = f"{API}/projects/{cfg.projeto}"

    canais = _checar(s.get(f"{base}/notificationChannels")).get("notificationChannels", [])
    canal = next((c["name"] for c in canais
                  if c.get("type") == "email" and c.get("labels", {}).get("email_address") == args.email), None)
    if canal:
        log("INFO", "canal de e-mail ja existe", canal=canal)
    else:
        canal = _checar(s.post(f"{base}/notificationChannels", json={
            "type": "email",
            "displayName": f"Pipeline - {args.email}",
            "labels": {"email_address": args.email},
        }))["name"]
        log("INFO", "canal de e-mail criado", canal=canal)

    politicas = _checar(s.get(f"{base}/alertPolicies")).get("alertPolicies", [])
    existente = next((p for p in politicas if p.get("displayName") == NOME_POLITICA), None)
    if existente:
        corpo = politica(canal)
        _checar(s.patch(f"{API}/{existente['name']}", json=corpo,
                        params={"updateMask": "conditions,alertStrategy,notificationChannels,documentation,combiner"}))
        log("INFO", "politica de alerta atualizada", politica=existente["name"])
    else:
        criada = _checar(s.post(f"{base}/alertPolicies", json=politica(canal)))
        log("INFO", "politica de alerta criada", politica=criada["name"])


if __name__ == "__main__":
    main()
