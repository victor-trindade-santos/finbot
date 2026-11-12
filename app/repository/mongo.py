# app/repository/mongo.py
"""Conexão com o MongoDB (uma só para o projeto inteiro)."""
from functools import lru_cache  # guarda o resultado da função para reaproveitar

from pymongo import MongoClient
from pymongo.database import Database

from app.config.settings import settings


# @lru_cache: na 1ª chamada cria a conexão; nas seguintes, devolve a mesma.
@lru_cache
def cliente() -> MongoClient:
    # serverSelectionTimeoutMS=5000: desiste em 5 s se o MongoDB não responder (em vez de travar).
    return MongoClient(settings.mongo_url, serverSelectionTimeoutMS=5000)


def banco() -> Database:
    # cliente()["finbot"] = o banco com esse nome dentro do servidor.
    return cliente()[settings.mongo_banco]