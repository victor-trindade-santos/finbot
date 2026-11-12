# app/repository/perfis.py
"""Memória de LONGO prazo: o perfil do usuário.

Vale para TODAS as conversas do usuário (não só para uma sessão).
Fica numa coleção própria, fora do grafo: é o "BaseStore / banco externo" dos slides.
"""
from app.repository import mongo


def _colecao():
    # Coleção = a "tabela" do MongoDB; aqui fica um documento de perfil por usuário.
    return mongo.banco()["perfis"]


def salvar_perfil(usuario: str, dados: dict) -> None:
    # update_one com upsert=True: atualiza o perfil se ele existir; se não existir, cria.
    # "$set" grava os campos enviados; **dados espalha o dicionário (nome, objetivo...).
    _colecao().update_one({"usuario": usuario}, {"$set": {"usuario": usuario, **dados}}, upsert=True)


def obter_perfil(usuario: str) -> dict:
    # {"_id": 0} esconde o id interno do Mongo; se não achar, devolve só o nome do usuário.
    return _colecao().find_one({"usuario": usuario}, {"_id": 0}) or {"usuario": usuario}


def texto_perfil(usuario: str) -> str:
    """Perfil em texto, pronto para entrar no prompt de sistema."""
    p = obter_perfil(usuario)
    # Junta só os campos preenchidos, ex.: "nome: Ana; objetivo: aposentadoria".
    partes = [f"{campo}: {p[campo]}" for campo in ("nome", "objetivo", "experiencia") if p.get(campo)]
    return "; ".join(partes) or "não informado"