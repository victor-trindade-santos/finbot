# tests/test_aula1.py
"""Aula 1 — configuração, fábrica de modelos e prompts."""
import pytest

from app.config.settings import MODELOS_PADRAO, Settings
from app.llm import fabrica
from app.prompts import catalogo


def test_modelo_padrao_por_provedor():
    assert Settings(llm_provedor="groq", _env_file=None).modelo == MODELOS_PADRAO["groq"]
    assert Settings(llm_provedor="gemini", llm_modelo="outro", _env_file=None).modelo == "outro"


def test_provedor_invalido_e_barrado_ao_iniciar():
    with pytest.raises(ValueError):
        Settings(llm_provedor="openai", _env_file=None)


def test_chave_nunca_aparece_no_print():
    s = Settings(groq_api_key="gsk_segredo", _env_file=None)
    assert "gsk_segredo" not in str(s)


def test_sem_chave_da_erro_claro(monkeypatch):
    monkeypatch.setattr(fabrica.settings, "groq_api_key", None)
    monkeypatch.setattr(fabrica.settings, "llm_provedor", "groq")
    with pytest.raises(RuntimeError, match="Defina a chave"):
        fabrica.criar_modelo()


def test_prompt_de_sistema_proibe_recomendacao():
    assert "NÃO faz recomendação" in catalogo.carregar("sistema")