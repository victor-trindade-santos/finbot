# app/utils/http.py
"""Chamadas HTTP com tempo limite e cabeçalhos padrão."""
import requests

from app.config.settings import settings


def get_json(url: str, params: dict | None = None):
    # User-Agent identifica quem está chamando (algumas APIs recusam pedidos sem ele).
    headers = {"User-Agent": "FinBot-FATEC/1.0"}
    # Se houver token da brapi, ele vai no cabeçalho Authorization (só para a brapi.dev).
    token = settings.brapi_token.get_secret_value() if settings.brapi_token else ""
    if token and "brapi.dev" in url:
        headers["Authorization"] = f"Bearer {token}"
    # timeout=15: desiste em 15 s se a API não responder, em vez de travar o chat.
    resposta = requests.get(url, params=params, headers=headers, timeout=15)
    resposta.raise_for_status()  # erro HTTP (404, 500...) vira exceção
    return resposta.json()  # converte o JSON da resposta em dicionário/lista do Python