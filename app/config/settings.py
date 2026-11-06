# app/config/settings.py
"""Configuração central: tudo que vem do arquivo .env passa por aqui.

Por que pydantic-settings e não os.getenv espalhado pelo código?
- Um único lugar lista TODAS as variáveis que o projeto usa.
- Tipos são validados ao iniciar (erro cedo, mensagem clara).
- SecretStr esconde as chaves quando alguém faz print(settings).
"""
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

MODELOS_PADRAO = {
    "groq": "openai/gpt-oss-120b",  # llama-3.3-70b-versatile foi desligado em 16/08/2026
    "gemini": "gemini-2.5-flash",
    "mistral": "mistral-small-latest",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    llm_provedor: Literal["groq", "gemini", "mistral"] = "groq"
    llm_modelo: str | None = None
    groq_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    mistral_api_key: SecretStr | None = None

    @property
    def modelo(self) -> str:
        return self.llm_modelo or MODELOS_PADRAO[self.llm_provedor]


settings = Settings()