# app/agents/grafo.py
"""O grafo principal do FinBot.

Grafo = NÓS (funções) + ARESTAS (quem vem depois) + ESTADO (o "bastão" que passa de nó em nó).

Aula 3:   START ─▶ chatbot ─▶ END        (+ checkpointer = memória de curto prazo)
Aulas 4 e 5: um AGENTE ÚNICO com ferramentas (pensar ⇄ ferramentas), ver app/agents/base.py.
"""
from functools import lru_cache  # guarda o grafo pronto para não montar de novo a cada pergunta
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.agents.base import criar_agente, fontes_do_turno
from app.agents.chatbot import no_chatbot
from app.llm.observabilidade import callbacks, rastrear
from app.repository import checkpointer, conversas, perfis

from app.tools.mercado import FERRAMENTAS_MERCADO
from app.utils.mensagens import conversa_limpa

# O ESTADO do grafo: o que passa de nó em nó. total=False = nenhum campo é obrigatório.
class EstadoChat(TypedDict, total=False):
    # add_messages: em vez de substituir a lista, ACRESCENTA as mensagens novas ao histórico.
    messages: Annotated[list[AnyMessage], add_messages]  # histórico (o checkpointer salva)
    perfil: str                                           # memória de longo prazo, vinda do Mongo


# ---------- Montagem ----------
def montar_grafo(memoria=None):
     # O grafo agora é o agente com ferramentas (o loop pensar ⇄ ferramentas de base.py).
    return criar_agente("finbot", "sistema", FERRAMENTAS_MERCADO, checkpointer=memoria)


@lru_cache
def grafo():
    """Compila uma única vez, com a memória no MongoDB."""
    return montar_grafo(checkpointer.criar_checkpointer())


def executar(pergunta: str, sessao: str, usuario: str = "anonimo") -> dict:
    # thread_id identifica a conversa: o checkpointer guarda um histórico para cada sessão.
    config = {"configurable": {"thread_id": sessao}, "callbacks": callbacks()}
    # Só a pergunta nova vai na entrada; o histórico anterior vem do checkpointer.
    entrada = {"messages": [HumanMessage(pergunta)], "perfil": perfis.texto_perfil(usuario)}
    with rastrear(sessao, usuario):
        # Roda o grafo do START ao END e devolve o estado final.
        estado = grafo().invoke(entrada, config)
    # Registra (ou atualiza) a conversa na lista da barra lateral.
    conversas.registrar(sessao, usuario, pergunta)

    # A última mensagem do estado é a resposta do FinBot.
    final = estado["messages"][-1]
    # Posição da última pergunta do usuário: as fontes são só deste turno.
    ultima_pergunta = max(i for i, m in enumerate(estado["messages"]) if isinstance(m, HumanMessage))
    fontes = fontes_do_turno(estado["messages"][ultima_pergunta:])
    return {"resposta": final.content, "agente": "finbot", "fontes": fontes}

def historico(sessao: str) -> list[dict]:
    """Mensagens da sessão lidas do checkpointer (para mostrar na tela)."""
    # get_state lê o último estado salvo dessa sessão no checkpointer.
    estado = grafo().get_state({"configurable": {"thread_id": sessao}})
    mensagens = estado.values.get("messages", []) if estado else []
    # limite=1000: na tela queremos a conversa inteira, não só as 10 últimas.
    return [
        {"papel": "user" if m.type == "human" else "assistant", "conteudo": m.content, "agente": m.name}
        for m in conversa_limpa(mensagens, limite=1000)
    ]


if __name__ == "__main__":
    # python -m app.agents.grafo  -> desenho do grafo em Mermaid (cole em https://mermaid.live)
    print(montar_grafo().get_graph(xray=True).draw_mermaid())