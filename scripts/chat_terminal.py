# scripts/chat_terminal.py
"""Aula 1 — o primeiro chat, direto no terminal.

Rode da pasta do projeto:   python -m scripts.chat_terminal     (digite "sair" para encerrar)
"""
from langchain_core.messages import HumanMessage, SystemMessage

from app.config.settings import settings
from app.llm.fabrica import criar_modelo
from app.prompts import catalogo

modelo = criar_modelo()

# O histórico é uma LISTA de mensagens. O modelo não lembra de nada sozinho:
# a cada pergunta, mandamos a conversa inteira de novo.
historico = [SystemMessage(catalogo.carregar("sistema"))]

print(f"FinBot ({settings.llm_provedor} / {settings.modelo}) — digite 'sair' para encerrar\n")
while True:
    pergunta = input("Você: ").strip()
    if pergunta.lower() in ("sair", "exit"):
        break
    if not pergunta:
        continue
    historico.append(HumanMessage(pergunta))
    resposta = modelo.invoke(historico)          # AIMessage
    historico.append(resposta)
    tokens = resposta.usage_metadata or {}
    print(f"\nFinBot: {resposta.content}\n   [tokens: entrada={tokens.get('input_tokens')} saída={tokens.get('output_tokens')}]\n")