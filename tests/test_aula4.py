# tests/test_aula4.py
"""Aula 4 — ferramentas e o loop de tool-calling."""
# A fixture falso também troca as APIs de mercado por respostas fixas (sem internet).
from app.agents import grafo
from app.config.settings import settings
from app.tools import mercado


# O LLM escolhe a ferramenta pela descrição: ela precisa ser longa e clara.
def test_ferramentas_tem_descricao_e_argumentos():
    for f in mercado.FERRAMENTAS_MERCADO:
        assert len(f.description) > 80, f"descrição curta demais em {f.name}"
    assert mercado.cotacao_acao.args["ticker"]["type"] == "string"


# As ferramentas leem e convertem os dados das APIs (aqui, respostas falsas).
def test_ferramenta_le_api(falso):
    assert mercado.indicadores_economicos.invoke({})["cdi_aa"]["valor"] == 14.9
    assert mercado.cotacao_acao.invoke({"ticker": "petr4"})["preco"] == 38.45
    assert mercado.indicadores_fii.invoke({"ticker": "MXRF11"})["dividend_yield_12m_pct"] == 12.4  # fração virou %


# Se a API cair, a ferramenta devolve {"erro": ...} em vez de quebrar.
def test_ferramenta_nao_quebra_se_api_falhar(falso, monkeypatch):
    def sem_internet(*a, **k):
        raise ConnectionError("sem internet")
    # monkeypatch troca get_json por uma função que sempre falha.
    monkeypatch.setattr(mercado, "get_json", sem_internet)
    assert "erro" in mercado.indicadores_economicos.invoke({})


# O modelo pede a ferramenta, recebe o dado e responde com ele, citando a fonte.
def test_loop_pede_ferramenta_e_responde_com_o_dado(falso):
    falso.ferramenta = "cotacao_acao"  # o modelo falso vai pedir esta ferramenta
    saida = grafo.executar("Quanto está a PETR4?", sessao="m1")
    assert falso.chamadas == ["tool:cotacao_acao", "resposta"]
    assert "38.45" in saida["resposta"]
    assert saida["fontes"] == ["brapi.dev"]


def test_guardrail_limita_as_voltas(falso, monkeypatch):
    """Com limite de 1 passo, o agente pede a ferramenta e o código o interrompe."""
    from langchain_core.messages import HumanMessage

    from app.agents.base import criar_agente
    monkeypatch.setattr(settings, "max_passos_agente", 1)
    agente = criar_agente("teste", "sistema", mercado.FERRAMENTAS_MERCADO)
    saida = agente.invoke({"messages": [HumanMessage("Selic?")]})
    assert "poucos passos" in saida["messages"][-1].content


def test_nome_de_ferramenta_inventado_tenta_de_novo(falso, monkeypatch):
    """Simula o erro real do Groq: 'attempted to call tool taxa_bcb which was not in request.tools'."""
    original = falso.invoke
    falhas = {"n": 0}

    def invoke_com_erro(self, mensagens, config=None):
        if falhas["n"] == 0 and getattr(self, "_ferramentas", None):
            falhas["n"] += 1
            raise RuntimeError("Error code: 400 - tool call validation failed: attempted to call tool 'taxa_bcb'")
        return original.__func__(self, mensagens, config)

    monkeypatch.setattr(type(falso), "invoke", invoke_com_erro)
    from langchain_core.messages import HumanMessage

    from app.agents.base import criar_agente
    agente = criar_agente("teste", "sistema", mercado.FERRAMENTAS_MERCADO)
    saida = agente.invoke({"messages": [HumanMessage("Selic?")]})
    assert falhas["n"] == 1                                   # errou uma vez...
    assert "tool:indicadores_economicos" in falso.chamadas                 # ...tentou de novo e usou a ferramenta certa
    assert saida["messages"][-1].content.startswith("resposta de teste")  # e respondeu, sem erro 500


def test_taxas_pedem_dados_ate_hoje(falso, monkeypatch):
    """A meta Selic vinha com data futura; agora pedimos o período até hoje."""
    from datetime import date
    pedidos = []

    def registra(url, params=None):
        pedidos.append(params)
        return [{"data": "21/10/2026", "valor": "15.00"}]
    monkeypatch.setattr(mercado, "get_json", registra)
    mercado.buscar_taxas()
    assert pedidos[0]["dataFinal"] == date.today().strftime("%d/%m/%Y")