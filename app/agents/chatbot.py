# app/agents/chatbot.py
"""Agente de conversa geral: LLM + prompt de sistema (sem ferramentas).
"""
# Tipos de mensagem do LangChain (os "papéis" da Aula 1):
# SystemMessage = regras do bot, HumanMessage = usuário, AIMessage = resposta do modelo.
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.llm import fabrica        # cria o modelo do provedor escolhido no .env
from app.prompts import catalogo   # carrega o prompt de sistema (app/prompts/sistema.md)


def responder(historico: list[BaseMessage], pergunta: str, callbacks: list | None = None) -> AIMessage:
    """Monta [sistema + histórico + pergunta] e chama o modelo."""
    # O LLM não tem memória: a cada pergunta enviamos regras + conversa anterior + pergunta nova.
    mensagens = (
        [SystemMessage(catalogo.carregar("sistema"))]
        + historico[-10:]  # janela de contexto: só as 10 últimas (economiza tokens)
        + [HumanMessage(pergunta)]
    )
    # invoke() envia as mensagens ao LLM e devolve um AIMessage.
    # Os callbacks (Langfuse) vão em config; "or []" troca None por lista vazia.
    return fabrica.criar_modelo().invoke(mensagens, config={"callbacks": callbacks or []})