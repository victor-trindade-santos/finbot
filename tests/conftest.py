# tests/conftest.py
"""Peças falsas para testar SEM gastar chamadas de API (LLM, MongoDB e APIs de mercado).

Por que testar com peças falsas? O LLM não é determinístico e custa tokens.
Aqui testamos o NOSSO código: se o fluxo, as ferramentas e a memória funcionam.
"""
import json
import os
import sys
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

sys.path.insert(0, str(Path(__file__).parent.parent))
for chave in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "API_URL"):
    os.environ[chave] = ""  # testes nunca mandam nada para fora

from app.llm import fabrica  # noqa: E402

ARGS_PADRAO = {
    "indicadores_economicos": {},
    "cotacao_acao": {"ticker": "PETR4"},
    "indicadores_fii": {"ticker": "MXRF11"},
    "tesouro_direto": {"simbolo": "tesouro-selic-01032031"},
    "simular_investimento": {"valor": 1000, "meses": 24, "percentual_cdi": 110},
}


class ModeloFalso:
    """Imita um ChatModel: invoke() e bind_tools(). Anota quem foi chamado."""

    def __init__(self):
        self.rota = "conversa"       # o que o roteador falso vai responder
        self.ferramenta = None       # qual ferramenta o agente falso vai pedir
        self.chamadas = []           # registro: "roteador", "revisor", "tool:cotacao_acao", "resposta"
        self.vistas = []             # mensagens recebidas na última chamada
        self._ferramentas = []

    def bind_tools(self, ferramentas):
        vinculado = ModeloFalso.__new__(ModeloFalso)
        vinculado.__dict__ = self.__dict__.copy()
        vinculado._dono = self
        vinculado._ferramentas = [f.name for f in ferramentas]
        return vinculado

    def _registrar(self, evento, mensagens):
        dono = getattr(self, "_dono", self)
        dono.chamadas.append(evento)
        dono.vistas = mensagens

    def invoke(self, mensagens, config=None):
        sistema = mensagens[0].content if mensagens else ""
        dono = getattr(self, "_dono", self)
        if "ROTEADOR" in sistema:
            self._registrar("roteador", mensagens)
            return AIMessage(content=f'Claro: {{"rota": "{dono.rota}", "motivo": "teste"}}')
        if "revisa a resposta" in sistema:
            self._registrar("revisor", mensagens)
            return AIMessage(content=mensagens[-1].content.split("especialista:\n")[-1] + "\n_aviso_")
        if "SUPERVISOR" in sistema:  # delega para cada especialista uma vez, depois encerra
            self._registrar("supervisor", mensagens)
            ja = {m.name for m in mensagens if isinstance(m, AIMessage)}
            proximo = next((e for e in ("mercado", "conhecimento") if e not in ja), "fim")
            return AIMessage(content=f'{{"proximo": "{proximo}"}}')
        if "LLM-as-judge" in sistema:
            self._registrar("juiz", mensagens)
            return AIMessage(content='{"nota": 0.9, "comentario": "ok"}')

        ultima_pergunta = max(i for i, m in enumerate(mensagens) if isinstance(m, HumanMessage))
        resultados = [m for m in mensagens[ultima_pergunta:] if isinstance(m, ToolMessage)]
        if self._ferramentas and not resultados:  # ainda não usou ferramenta neste turno: pede uma
            nome = dono.ferramenta if dono.ferramenta in self._ferramentas else self._ferramentas[0]
            args = ARGS_PADRAO.get(nome, {"consulta": mensagens[ultima_pergunta].content})
            self._registrar(f"tool:{nome}", mensagens)
            return AIMessage(content="", tool_calls=[{"name": nome, "args": args, "id": f"call_{len(dono.chamadas)}"}])

        self._registrar("resposta", mensagens)
        dados = " | ".join(r.content[:300] for r in resultados)
        return AIMessage(content=f"resposta de teste. {dados}".strip(),
                         usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15})


def get_json_falso(url, params=None):
    """Imita as respostas documentadas do Banco Central e da brapi."""
    if "bcb.gov.br" in url:
        valores = {"432": "15.00", "4389": "14.90", "13522": "4.80"}
        return [{"data": "21/10/2026", "valor": valores[url.split("sgs.")[1].split("/")[0]]}]
    if "stocks/quote" in url:
        return {"results": [{"symbol": "PETR4", "data": {
            "longName": "Petróleo Brasileiro S.A. - Petrobras", "regularMarketPrice": 38.45,
            "regularMarketChangePercent": 0.92, "regularMarketTime": "2026-10-21T20:07:00.000Z"}}]}
    if "fii/indicators" in url:
        return {"fiis": [{"symbol": "MXRF11", "asOfDate": "2026-09-30", "price": 9.30,
                          "priceToNav": 0.97, "dividendYield12m": 0.124, "segmentType": "Papel"}]}
    if "treasury/indicators" in url:
        return {"results": [{"symbol": "tesouro-selic-01032031", "bondType": "Tesouro Selic",
                             "maturityDate": "2031-03-01", "baseDate": "2026-10-21", "buyRate": 0.08,
                             "buyPrice": 18944.78, "rateInfo": {"description": "spread sobre a Selic"}}]}
    raise ValueError(f"URL inesperada no teste: {url}")


@pytest.fixture
def falso(monkeypatch):
    modelo = ModeloFalso()
    monkeypatch.setattr(fabrica, "criar_modelo", lambda temperatura=0.3: modelo)

    try:  # Aula 3+: MongoDB em memória e checkpointer em memória
        import mongomock
        from langgraph.checkpoint.memory import InMemorySaver

        from app.repository import checkpointer, mongo
        banco = mongomock.MongoClient().finbot_teste
        monkeypatch.setattr(mongo, "banco", lambda: banco)
        monkeypatch.setattr(checkpointer, "criar_checkpointer", InMemorySaver)
        from app.agents import grafo
        grafo.grafo.cache_clear()
    except ImportError:
        pass

    try:  # Aula 4+: APIs de mercado falsas
        from app.tools import mercado
        monkeypatch.setattr(mercado, "get_json", get_json_falso)
    except ImportError:
        pass

    try:  # Aula 5+: documentos já indexados
        from app.rag.indexador import indexar
        indexar()
    except ImportError:
        pass
    return modelo


@pytest.fixture
def api(falso):
    from fastapi.testclient import TestClient

    from app.main import app
    return TestClient(app)


def conteudo_json(texto: str):
    return json.loads(texto)