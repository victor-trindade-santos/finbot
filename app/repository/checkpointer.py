# app/repository/checkpointer.py
"""Memória de CURTO prazo: o checkpointer do LangGraph.

A cada passo do grafo, o estado (com todas as mensagens) é salvo no MongoDB,
identificado pelo thread_id (aqui, o id da sessão de chat).
Na próxima pergunta da mesma sessão, o grafo continua de onde parou.
"""
from langgraph.checkpoint.mongodb import MongoDBSaver

from app.config.settings import settings
from app.repository import mongo


def criar_checkpointer() -> MongoDBSaver:
    # O MongoDBSaver usa a mesma conexão e grava os estados do grafo no banco configurado.
    return MongoDBSaver(mongo.cliente(), db_name=settings.mongo_banco)