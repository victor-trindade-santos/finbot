# app/api/rotas.py
"""Rotas (endpoints) da API. Cada função = um endereço + um método HTTP."""
from fastapi import APIRouter

from app.api.schemas import Mensagem, Pergunta, Resposta
from app.config.settings import settings
from app.servicos import chat

# O router junta as rotas deste arquivo; depois ele é ligado à aplicação em app/main.py.
router = APIRouter()


# @router.get("/saude") = quando chegar um GET no endereço /saude, rode esta função.
@router.get("/saude")
def saude():
    """Usada para saber se a API está no ar (e para 'acordar' o Render)."""
    # Um dicionário devolvido aqui vira JSON na resposta.
    return {"status": "ok", "provedor": settings.llm_provedor, "modelo": settings.modelo}


# response_model=Resposta: a FastAPI confere a saída e a documenta no /docs.
@router.post("/chat", response_model=Resposta)
def perguntar(p: Pergunta):
    """Recebe a pergunta (JSON validado pelo schema Pergunta) e devolve a resposta."""
    # A rota só traduz HTTP: quem faz o trabalho é a camada de serviço.
    return chat.perguntar(p.mensagem, p.sessao, p.usuario)


# {sessao} no endereço vira o parâmetro "sessao" da função (ex.: /sessoes/abc/mensagens).
@router.get("/sessoes/{sessao}/mensagens", response_model=list[Mensagem])
def mensagens(sessao: str):
    """Devolve o histórico de mensagens de uma sessão."""
    return chat.historico(sessao)