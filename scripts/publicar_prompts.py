# scripts/publicar_prompts.py
"""Aula 3 — Envia os prompts (app/prompts/*.md) para o Langfuse.

    python -m scripts.publicar_prompts            # cria só os que ainda não existem
    python -m scripts.publicar_prompts --forcar   # envia o .md como NOVA versão de todos

Depois de publicado, edite o prompt no site do Langfuse: salve uma versão nova e
mova o rótulo 'production' para ela. O app passa a usar a versão nova em até 60 s, sem deploy.
"""
import sys

from app.config.settings import settings
from app.llm.observabilidade import cliente_langfuse
from app.prompts import catalogo


def publicar(forcar: bool = False) -> None:
    # Sem as chaves não há para onde enviar.
    if not settings.langfuse_ativo:
        print("Configure LANGFUSE_PUBLIC_KEY e LANGFUSE_SECRET_KEY no .env primeiro.")
        return
    lf = cliente_langfuse()
    # Para cada arquivo .md da pasta app/prompts...
    for nome in catalogo.nomes_locais():
        # ...pega o texto local e o nome no Langfuse (ex.: finbot-sistema).
        texto, remoto = catalogo.carregar(nome), catalogo.nome_langfuse(nome)
        try:
            # Busca a versão atual (cache_ttl_seconds=0: sem cache, sempre a mais nova).
            atual = lf.get_prompt(remoto, label="production", cache_ttl_seconds=0)
            # Sem --forcar, ou se o texto não mudou, não cria versão nova.
            if not forcar or atual.prompt == texto:
                print(f"=  {remoto}: já existe (versão {atual.version})")
                continue
        except Exception:
            pass  # ainda não existe no Langfuse
        # Cria uma versão nova e já a marca como "production" (a que o app usa).
        novo = lf.create_prompt(name=remoto, prompt=texto, labels=["production"],
                                commit_message="enviado por scripts/publicar_prompts.py")
        print(f"+  {remoto}: versão {novo.version} (production)")
    # flush() garante que tudo foi enviado antes de o script terminar.
    lf.flush()


if __name__ == "__main__":
    # --forcar na linha de comando liga o modo forçar.
    publicar(forcar="--forcar" in sys.argv)