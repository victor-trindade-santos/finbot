# app/prompts/catalogo.py
"""Catálogo de prompts.

Cada prompt é um arquivo .md nesta pasta (ex.: sistema.md). Prompt é ARTEFATO, não texto solto no código.
Aula 3: o Langfuse passa a ser a "fonte da verdade". O arquivo .md vira:
  1. a semente: scripts/publicar_prompts.py envia para o Langfuse;
  2. a reserva: se o Langfuse estiver fora do ar, o código usa o .md.
"""
from pathlib import Path
from app.config.settings import settings


PASTA = Path(__file__).parent


def carregar(nome: str) -> str:
    """Lê o texto do prompt local (arquivo app/prompts/<nome>.md)."""
    return (PASTA / f"{nome}.md").read_text(encoding="utf-8").strip()

# Nomes dos prompts locais: sistema.md -> "sistema" (p.stem = nome do arquivo sem a extensão).
def nomes_locais() -> list[str]:
    return sorted(p.stem for p in PASTA.glob("*.md"))


# No Langfuse, os prompts do projeto ganham o prefixo "finbot-" (ex.: finbot-sistema).
def nome_langfuse(nome: str) -> str:
    return f"finbot-{nome}"


class PromptLocal:
    """Imita um prompt do Langfuse quando ele não está configurado ou não responde."""

    # Mesmos atributos de um prompt do Langfuse: o resto do código não precisa saber de onde veio.
    is_fallback = True
    version = "local"

    def __init__(self, texto: str):
        self.prompt = texto

    def compile(self, **variaveis) -> str:
        # Troca cada {{variavel}} do texto pelo valor recebido (ex.: {{perfil}} -> "iniciante").
        texto = self.prompt
        for chave, valor in variaveis.items():
            texto = texto.replace("{{" + chave + "}}", str(valor))
        return texto


def obter(nome: str):
    """Versão 'production' do prompt no Langfuse (60 s de cache). Sem Langfuse, usa o .md.

    Uso:  p = obter("sistema");  texto = p.compile(perfil="...")
    """
    local = carregar(nome)
    # Sem as chaves do Langfuse, usa direto o arquivo .md.
    if not settings.langfuse_ativo:
        return PromptLocal(local)
    try:
        from app.llm.observabilidade import cliente_langfuse
        # label="production": a versão marcada para uso; fallback: texto usado se o prompt não existir lá.
        # cache_ttl_seconds=60: guarda o prompt por 60 s para não buscar a cada pergunta.
        return cliente_langfuse().get_prompt(
            nome_langfuse(nome), label="production", fallback=local, cache_ttl_seconds=60
        )
    except Exception as erro:
        # Qualquer falha (sem internet, Langfuse fora do ar): avisa no terminal e usa o .md.
        print(f"[prompts] Langfuse indisponível ({erro}); usando {nome}.md")
        return PromptLocal(local)