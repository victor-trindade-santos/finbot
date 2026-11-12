# app/servicos/chat.py
"""Camada de serviço: a ÚNICA porta de entrada do chat.

A API (e qualquer outro canal no futuro: WhatsApp, terminal...) chama estas funções.
Assim, quando o "miolo" muda de aula para aula, a API não precisa mudar.
"""
from app.agents import grafo
from app.repository import conversas, perfis


def perguntar(pergunta: str, sessao: str, usuario: str = "anonimo") -> dict:
    # A partir desta aula, quem responde é o grafo (com memória no MongoDB).
    return grafo.executar(pergunta, sessao, usuario)


def historico(sessao: str) -> list[dict]:
    return grafo.historico(sessao)


# As funções abaixo só repassam para o repository: a API não fala direto com o banco.
def listar_conversas(usuario: str) -> list[dict]:
    return conversas.listar(usuario)


def obter_perfil(usuario: str) -> dict:
    return perfis.obter_perfil(usuario)


def salvar_perfil(usuario: str, dados: dict) -> dict:
    perfis.salvar_perfil(usuario, dados)
    return perfis.obter_perfil(usuario)
