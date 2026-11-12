# app/repository/conversas.py
"""Lista de conversas de cada usuário (para a barra lateral do chat)."""
from datetime import datetime, timezone

from app.repository import mongo


def _colecao():
    # Coleção com um documento por conversa (sessão).
    return mongo.banco()["conversas"]


# Cria a conversa na 1ª pergunta; nas seguintes, só atualiza a data.
def registrar(sessao: str, usuario: str, primeira_pergunta: str) -> None:
    agora = datetime.now(timezone.utc)
    _colecao().update_one(
        {"sessao": sessao},
        # $set: sempre atualiza a data; $setOnInsert: título e criação só são gravados quando a conversa é nova.
        {"$set": {"atualizada_em": agora},
         "$setOnInsert": {"sessao": sessao, "usuario": usuario, "titulo": primeira_pergunta[:60], "criada_em": agora}},
        upsert=True,
    )


def listar(usuario: str) -> list[dict]:
    # Conversas do usuário, da mais recente para a mais antiga (-1), no máximo 20.
    return list(_colecao().find({"usuario": usuario}, {"_id": 0}).sort("atualizada_em", -1).limit(20))
