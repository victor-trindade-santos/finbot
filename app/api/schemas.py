# app/api/schemas.py
"""Modelos de entrada e saída da API (Pydantic).

Eles são o CONTRATO: a FastAPI valida o que chega (erro 422 se faltar campo)
e gera a documentação automática em /docs.
"""
from pydantic import BaseModel, Field


class Pergunta(BaseModel):
    """O que o front ENVIA para POST /chat."""
    # min_length=1 recusa mensagem vazia (422); examples aparece como exemplo no /docs.
    mensagem: str = Field(min_length=1, examples=["O que é CDI?"])
    # Sem valor padrão = campo obrigatório: se faltar, a FastAPI responde 422.
    sessao: str = Field(examples=["sessao-123"])
    # Com valor padrão = campo opcional: se não vier, vale "anonimo".
    usuario: str = "anonimo"


class Resposta(BaseModel):
    """O que a API DEVOLVE em POST /chat."""
    resposta: str


class Mensagem(BaseModel):
    """Uma mensagem do histórico, devolvida em GET /sessoes/{sessao}/mensagens."""
    papel: str      # "user" (pessoa) ou "assistant" (FinBot)
    conteudo: str   # o texto da mensagem