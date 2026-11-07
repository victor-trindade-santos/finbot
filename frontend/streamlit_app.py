# frontend/streamlit_app.py
"""Front do FinBot em Streamlit. Ele NÃO fala com o LLM: só chama a API.

Local:   streamlit run frontend/streamlit_app.py
Nuvem:   Streamlit Community Cloud (API_URL nos Secrets aponta para a API no Render)
"""
import os
import uuid       # gera identificadores aleatórios (usado para criar o id da sessão)

import requests   # faz pedidos HTTP para a API
import streamlit as st


def config(nome: str, padrao: str) -> str:
    """Lê de variável de ambiente ou dos Secrets do Streamlit Cloud."""
    try:
        # 1º tenta a variável de ambiente; se não houver, procura nos Secrets; senão, usa o padrão.
        return os.getenv(nome) or st.secrets.get(nome, padrao)
    except Exception:  # sem arquivo de secrets (rodando local)
        return padrao


# rstrip("/") tira a barra do final, para não virar "...com//chat" ao juntar com o caminho.
API_URL = config("API_URL", "http://127.0.0.1:8000").rstrip("/")
TEMPO_LIMITE = 120  # segundos: a API grátis do Render pode levar ~1 min para "acordar"


def api(metodo: str, caminho: str, **kwargs):
    """Chama a API (ex.: api("POST", "/chat", json={...})) e devolve o JSON da resposta."""
    # **kwargs repassa argumentos extras ao requests, como json={...} com o corpo do pedido.
    resposta = requests.request(metodo, f"{API_URL}{caminho}", timeout=TEMPO_LIMITE, **kwargs)
    # Se a API respondeu com erro (4xx ou 5xx), levanta uma exceção em vez de seguir.
    resposta.raise_for_status()
    return resposta.json()


# Configuração e cabeçalho da página.
st.set_page_config(page_title="FinBot", page_icon="💬")
st.title("💬 FinBot")
st.caption("Chat educacional sobre investimentos — não é recomendação de investimento.")

# st.session_state guarda valores entre um clique e outro (o script roda de novo a cada interação)
# Na primeira execução, cria um id curto de sessão (8 caracteres) e a lista de mensagens.
if "sessao" not in st.session_state:
    st.session_state.sessao = str(uuid.uuid4())[:8]
    st.session_state.mensagens = []
usuario = "aluno1"  # fixo por enquanto; na Aula 3 o usuário poderá ser escolhido na tela


def mostrar(m: dict):
    """Desenha uma mensagem no chat, com o balão do usuário ou do assistente."""
    with st.chat_message(m["papel"]):
        st.markdown(m["conteudo"])


# Como o script roda de novo a cada interação, redesenhamos toda a conversa guardada.
for m in st.session_state.mensagens:
    mostrar(m)

# st.chat_input mostra a caixa de texto; ":=" guarda o que foi digitado em "pergunta"
# e o if só entra quando o usuário enviou algo.
if pergunta := st.chat_input("Pergunte sobre CDI, Tesouro, FIIs, ações..."):
    # Mostra a pergunta na tela na hora, antes de esperar a resposta.
    st.session_state.mensagens.append({"papel": "user", "conteudo": pergunta})
    mostrar(st.session_state.mensagens[-1])
    # Enquanto a API responde, aparece "Pensando..." na tela.
    with st.spinner("Pensando..."):
        try:
            r = api("POST", "/chat", json={"mensagem": pergunta, "sessao": st.session_state.sessao, "usuario": usuario})
            # "agente" e "fontes" só existem nas próximas aulas; .get() evita erro se não vierem.
            m = {"papel": "assistant", "conteudo": r["resposta"], "agente": r.get("agente"), "fontes": r.get("fontes", [])}
        except Exception as erro:
            # Se a API estiver fora do ar ou der erro, mostra o aviso no chat em vez de travar.
            m = {"papel": "assistant", "conteudo": f"⚠️ Erro ao falar com a API: {erro}"}
    st.session_state.mensagens.append(m)
    mostrar(m)