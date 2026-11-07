# app/servicos/chat.py
"""Camada de serviço: a ÚNICA porta de entrada do chat.

A API (e qualquer outro canal no futuro: WhatsApp, terminal...) chama estas funções.
Assim, quando o "miolo" muda de aula para aula, a API não precisa mudar.
"""
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.chatbot import responder
from app.llm.observabilidade import callbacks, rastrear

# Memória provisória: some quando a API reinicia (na Aula 3 vai para o MongoDB).
# É um dicionário: a chave é o id da sessão e o valor é a lista de mensagens dela.
# O "_" no início do nome indica que é de uso interno deste arquivo.
_memoria: dict[str, list] = {}


def perguntar(pergunta: str, sessao: str, usuario: str = "anonimo") -> dict:
    """Recebe uma pergunta, chama o agente e guarda a troca no histórico da sessão."""
    # setdefault pega a lista da sessão; se a sessão for nova, cria uma lista vazia.
    historico = _memoria.setdefault(sessao, [])
    # Tudo dentro do "with" fica registrado no Langfuse com essa sessão e esse usuário.
    with rastrear(sessao, usuario):
        resposta = responder(historico, pergunta, callbacks=callbacks())
    # Guarda a pergunta e a resposta para a próxima chamada lembrar da conversa.
    historico += [HumanMessage(pergunta), AIMessage(resposta.content)]
    # Devolve um dicionário simples; a API transforma isso em JSON.
    return {"resposta": resposta.content}


def historico(sessao: str) -> list[dict]:
    """Devolve as mensagens da sessão em formato simples (papel + conteúdo) para a API."""
    # m.type é "human" para o usuário e "ai" para o modelo; traduzimos para user/assistant.
    # .get(sessao, []) devolve lista vazia se a sessão não existir (em vez de dar erro).
    return [
        {"papel": "user" if m.type == "human" else "assistant", "conteudo": m.content}
        for m in _memoria.get(sessao, [])
    ]