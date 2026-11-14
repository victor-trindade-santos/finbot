# app/utils/mensagens.py
"""Ferramentas para lidar com o histórico de mensagens."""
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage


def conversa_limpa(mensagens: list[AnyMessage], limite: int = 10) -> list[AnyMessage]:
    """Só perguntas do usuário e respostas finais (sem chamadas de ferramenta).

    Por quê? Janela de contexto: enviar tudo custa tokens e confunde o modelo.
    As últimas 'limite' mensagens bastam para manter o assunto.
    """
    # Fica com as perguntas (HumanMessage) e com as respostas que têm texto e não são pedidos de ferramenta.
    limpas = [
        m for m in mensagens
        if isinstance(m, HumanMessage) or (isinstance(m, AIMessage) and m.content and not m.tool_calls)
    ]
    return limpas[-limite:]  # só as últimas 'limite' mensagens

def turno_atual(mensagens: list[AnyMessage], limite: int = 10) -> list[AnyMessage]:
    """Histórico limpo + TUDO desde a última pergunta (inclusive chamadas de ferramenta deste turno)."""
    # Posição da última pergunta (0 se não houver nenhuma).
    ultima = max((i for i, m in enumerate(mensagens) if isinstance(m, HumanMessage)), default=0)
    # Antes da pergunta: só a conversa limpa. Depois dela: tudo, para o agente ver os resultados das ferramentas.
    return conversa_limpa(mensagens[:ultima], limite) + list(mensagens[ultima:])