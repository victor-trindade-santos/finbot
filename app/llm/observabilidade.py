# app/llm/observabilidade.py
"""Aula 2 — Observabilidade com Langfuse.

Cada pergunta vira um TRACE: a árvore com tudo o que aconteceu (chamadas ao LLM,
ferramentas, busca em documentos), com entrada, saída, tokens e tempo de cada passo.
Sem chaves no .env, tudo continua funcionando, só não registra.
"""
import os
from contextlib import contextmanager  # transforma uma função em um bloco "with ...:"

from app.config.settings import settings

# O SDK do Langfuse lê as credenciais destas variáveis de ambiente.
# Aqui copiamos os valores do .env (que já estão em settings) para o ambiente do programa.
# setdefault só grava se a variável ainda não existir: não sobrescreve o que já veio do sistema.
if settings.langfuse_ativo:
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key.get_secret_value())
    os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)
    # Ambiente que aparece no filtro Environment do Langfuse: "local" no seu computador.
    # No Render, a variável já vem do render.yaml ("producao") e o setdefault não a substitui.
    os.environ.setdefault("LANGFUSE_TRACING_ENVIRONMENT", "local")


def cliente_langfuse():
    """Devolve o cliente do Langfuse (na Aula 3 ele será usado para buscar os prompts)."""
    # O import fica dentro da função: a biblioteca só é carregada quando for usada de fato.
    from langfuse import get_client
    return get_client()


def callbacks() -> list:
    """Lista de callbacks para o LangChain/LangGraph enviarem cada passo ao Langfuse."""
    # Sem as chaves, devolve lista vazia: o chat funciona normalmente, só não registra nada.
    if not settings.langfuse_ativo:
        return []
    from langfuse.langchain import CallbackHandler
    # O CallbackHandler é avisado a cada passo (início e fim da chamada ao LLM)
    # e envia entrada, saída, tokens e tempo para o painel do Langfuse.
    return [CallbackHandler()]


@contextmanager
def rastrear(sessao: str, usuario: str, nome: str = "chat"):
    """Agrupa os traces por sessão e usuário (aba Sessions do Langfuse).

    Uso:
        with rastrear("sessao-123", "aluno1"):
            ...  # tudo o que rodar aqui dentro fica marcado com essa sessão e esse usuário
    """
    if not settings.langfuse_ativo:
        yield  # sem Langfuse: apenas executa o bloco "with", sem marcar nada
        return
    from langfuse import propagate_attributes
    # propagate_attributes "carimba" sessão, usuário e nome em todo trace criado dentro do bloco.
    with propagate_attributes(session_id=sessao, user_id=usuario, trace_name=nome):
        yield  # neste ponto roda o código que está dentro do "with rastrear(...)"