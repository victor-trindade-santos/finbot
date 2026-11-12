# app/agents/chatbot.py
"""Agente de conversa geral: LLM + prompt de sistema (sem ferramentas).

Aula 3: vira um NÓ de grafo. Um nó recebe o estado e devolve só o que mudou.
"""
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.llm import fabrica
from app.llm.observabilidade import config_prompt
from app.prompts import catalogo
from app.utils.mensagens import conversa_limpa


# Nó do grafo: recebe o estado atual (mensagens e perfil) e devolve só o que mudou.
def no_chatbot(estado: dict) -> dict:
    # Busca o prompt de sistema (no Langfuse ou no .md) e preenche {{perfil}}.
    prompt = catalogo.obter("sistema")
    sistema = SystemMessage(prompt.compile(perfil=estado.get("perfil", "não informado")))
    # Envia regras + conversa (sem passos internos) ao LLM; config liga o trace ao prompt.
    resposta = fabrica.criar_modelo().invoke(
        [sistema] + conversa_limpa(estado["messages"]),
        config=config_prompt(prompt),
    )
    # A nova mensagem do assistente; name="conversa" marca qual agente respondeu.
    return {"messages": [AIMessage(content=resposta.content, name="conversa")]}