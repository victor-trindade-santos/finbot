# app/prompts/catalogo.py
"""Catálogo de prompts.

Cada prompt é um arquivo .md nesta pasta (ex.: sistema.md). Prompt é ARTEFATO, não texto solto no código.
"""
from pathlib import Path

PASTA = Path(__file__).parent


def carregar(nome: str) -> str:
    """Lê o texto do prompt local (arquivo app/prompts/<nome>.md)."""
    return (PASTA / f"{nome}.md").read_text(encoding="utf-8").strip()