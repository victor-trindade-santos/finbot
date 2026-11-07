# tests/test_aula2.py
"""Aula 2 — a API responde, valida a entrada e lembra da conversa da sessão.

As fixtures vêm de tests/conftest.py:
- api: um cliente de teste que chama a API sem precisar ligar o servidor;
- falso: um modelo falso no lugar do LLM (não gasta tokens e sempre responde igual).
"""


def test_saude(api):
    """A rota /saude responde com status ok."""
    assert api.get("/saude").json()["status"] == "ok"


def test_chat_responde(api):
    """POST /chat devolve 200 e a resposta do modelo (aqui, o modelo falso)."""
    r = api.post("/chat", json={"mensagem": "Oi!", "sessao": "s1"})
    assert r.status_code == 200
    assert "resposta de teste" in r.json()["resposta"]


def test_chat_envia_o_historico_ao_modelo(api, falso):
    """Na 2ª pergunta, a 1ª vai junto: é assim que o FinBot "lembra" da conversa."""
    api.post("/chat", json={"mensagem": "Meu nome é Ana", "sessao": "s2"})
    api.post("/chat", json={"mensagem": "Qual é meu nome?", "sessao": "s2"})
    # falso.vistas guarda as mensagens que o modelo recebeu na última chamada.
    textos = [m.content for m in falso.vistas]
    assert "Meu nome é Ana" in textos  # a 1ª pergunta foi junto na 2ª chamada


def test_sessoes_nao_se_misturam(api):
    """Cada sessão tem seu próprio histórico: a conversa A não vê a conversa B."""
    api.post("/chat", json={"mensagem": "pergunta A", "sessao": "A"})
    api.post("/chat", json={"mensagem": "pergunta B", "sessao": "B"})
    conteudos = [m["conteudo"] for m in api.get("/sessoes/A/mensagens").json()]
    assert "pergunta A" in conteudos and "pergunta B" not in conteudos


def test_mensagem_vazia_da_erro_422(api):
    """Mensagem vazia é barrada pelo schema (min_length=1) antes de chegar ao LLM."""
    assert api.post("/chat", json={"mensagem": "", "sessao": "x"}).status_code == 422