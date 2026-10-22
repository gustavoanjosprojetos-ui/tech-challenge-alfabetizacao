"""Cliente minimo do Pub/Sub via API REST.

Usamos a API REST (com google-auth, que ja vem com as bibliotecas do BigQuery) em vez do
pacote google-cloud-pubsub para nao depender de extensoes compiladas: o projeto roda em
versoes recentes do Python sem precisar de compilador.
"""
import base64

import google.auth
from google.auth.transport.requests import AuthorizedSession

API = "https://pubsub.googleapis.com/v1"


class ErroPubSub(RuntimeError):
    pass


class PubSub:
    def __init__(self, projeto: str):
        credenciais, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        self.sessao = AuthorizedSession(credenciais)
        self.projeto = projeto

    def topico(self, nome: str) -> str:
        return f"projects/{self.projeto}/topics/{nome}"

    def assinatura(self, nome: str) -> str:
        return f"projects/{self.projeto}/subscriptions/{nome}"

    @staticmethod
    def _verificar(resposta, aceitar=()):
        if resposta.status_code in aceitar:
            return resposta
        if resposta.status_code >= 400:
            raise ErroPubSub(f"HTTP {resposta.status_code}: {resposta.text[:1000]}")
        return resposta

    def criar_topico(self, nome: str) -> bool:
        """Cria o topico. Devolve False se ja existia."""
        r = self._verificar(self.sessao.put(f"{API}/{self.topico(nome)}", json={}), aceitar=(409,))
        return r.status_code != 409

    def criar_assinatura_bigquery(self, nome: str, topico: str, tabela: str) -> bool:
        """Assinatura que grava cada mensagem direto numa tabela do BigQuery (Bronze do streaming).

        tabela no formato projeto.dataset.tabela. writeMetadata grava message_id, publish_time,
        data (payload bruto) e attributes, sem interpretar o conteudo: o bruto fica preservado.
        """
        corpo = {
            "topic": self.topico(topico),
            "ackDeadlineSeconds": 60,
            "bigqueryConfig": {"table": tabela, "writeMetadata": True},
        }
        r = self._verificar(self.sessao.put(f"{API}/{self.assinatura(nome)}", json=corpo), aceitar=(409,))
        return r.status_code != 409

    def publicar(self, topico: str, mensagens: list[tuple[bytes, dict]]) -> list[str]:
        """Publica (payload em bytes, atributos) e devolve os message_ids gerados pelo Pub/Sub."""
        corpo = {
            "messages": [
                {"data": base64.b64encode(dados).decode("ascii"), "attributes": atributos}
                for dados, atributos in mensagens
            ]
        }
        r = self._verificar(self.sessao.post(f"{API}/{self.topico(topico)}:publish", json=corpo))
        return r.json().get("messageIds", [])
