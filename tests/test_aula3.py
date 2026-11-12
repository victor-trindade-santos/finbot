# tests/test_aula3.py
"""Aula 3 — grafo com checkpointer (curto prazo), perfil (longo prazo) e prompts versionados."""
# A fixture falso (tests/conftest.py) troca o LLM e o MongoDB por versões falsas, em memória.
from app.agents import grafo
from app.prompts import catalogo
from app.repository import perfis


# Mesma sessão lembra a conversa; outra sessão começa do zero.
def test_memoria_de_curto_prazo_por_sessao(falso):
    grafo.executar("Meu nome é Ana", sessao="t1")
    grafo.executar("Qual é meu nome?", sessao="t1")
    assert "Meu nome é Ana" in [m.content for m in falso.vistas]
    grafo.executar("Oi", sessao="t2")
    assert "Meu nome é Ana" not in [m.content for m in falso.vistas]  # outra sessão, outra memória


# O histórico mostrado na tela é lido do checkpointer (pergunta + resposta).
def test_historico_vem_do_checkpointer(falso):
    grafo.executar("Pergunta 1", sessao="t3")
    historico = grafo.historico("t3")
    assert [m["papel"] for m in historico] == ["user", "assistant"]


# O perfil salvo no Mongo aparece no prompt de sistema (falso.vistas[0]).
def test_perfil_entra_no_prompt(falso):
    perfis.salvar_perfil("bia", {"nome": "Bia", "objetivo": "reserva de emergência"})
    grafo.executar("Oi", sessao="t4", usuario="bia")
    assert "reserva de emergência" in falso.vistas[0].content


# A API salva e lê o perfil, e a 1ª pergunta vira o título da conversa.
def test_api_perfil_e_conversas(api):
    api.put("/usuarios/caio/perfil", json={"nome": "Caio", "experiencia": "iniciante"})
    assert api.get("/usuarios/caio/perfil").json()["nome"] == "Caio"
    api.post("/chat", json={"mensagem": "O que é CDI?", "sessao": "c1", "usuario": "caio"})
    assert api.get("/usuarios/caio/conversas").json()[0]["titulo"] == "O que é CDI?"


# Sem chaves do Langfuse, o prompt vem do .md e {{perfil}} é preenchido.
def test_prompt_sem_langfuse_usa_arquivo_local():
    p = catalogo.obter("sistema")
    assert p.is_fallback
    assert p.compile(perfil="iniciante").endswith("iniciante")