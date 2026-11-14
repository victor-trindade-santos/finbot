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
    "gemini": "gemini-3.8-flash",
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
    
    # Langfuse (observabilidade e prompts)
    # Chave pública: identifica o projeto no Langfuse (pode ser texto comum).
    langfuse_public_key: str | None = None
    # Chave secreta: SecretStr esconde o valor em print() e em mensagens de erro.
    langfuse_secret_key: SecretStr | None = None
    # Servidor do Langfuse (projeto criado nos EUA usa https://us.cloud.langfuse.com).
    langfuse_host: str = "https://cloud.langfuse.com"

    # Endereço da API, usado pelo front em Streamlit.
    # No computador é a API local; na nuvem, aponta para a API publicada no Render.
    api_url: str = "http://127.0.0.1:8000"
    # MongoDB
    # Estes são só valores PADRÃO: o valor real vem do .env (MONGO_URL e MONGO_BANCO)
    # no seu computador, e das variáveis de ambiente no Render. Se existir no .env, ele vale.
    # NUNCA coloque aqui a URL do Atlas: ela tem a senha do banco e este arquivo vai para o GitHub.
    mongo_url: str = "mongodb://localhost:27017"
    mongo_banco: str = "finbot"  # nome do banco de dados dentro do servidor
    
    # Dados de mercado
    # Token da brapi.dev (opcional): sem ele, só alguns ativos funcionam.
    brapi_token: SecretStr | None = None
    max_passos_agente: int = 5  # guardrail: no máximo 5 voltas no loop de tools

    @property
    def modelo(self) -> str:
        return self.llm_modelo or MODELOS_PADRAO[self.llm_provedor]
    
    # @property permite usar o método como se fosse um campo: settings.langfuse_ativo
    @property
    def langfuse_ativo(self) -> bool:
        """Diz se o Langfuse está configurado: só liga com as DUAS chaves preenchidas."""
        # get_secret_value() revela o texto guardado no SecretStr; sem chave, usa "" (vazio).
        segredo = self.langfuse_secret_key.get_secret_value() if self.langfuse_secret_key else ""
        # bool(...) dá True só se a chave pública E a secreta tiverem conteúdo.
        return bool(self.langfuse_public_key and segredo)    # @property permite usar o método como se fosse um campo: settings.langfuse_ativo
    @property
    def langfuse_ativo(self) -> bool:
        """Diz se o Langfuse está configurado: só liga com as DUAS chaves preenchidas."""
        # get_secret_value() revela o texto guardado no SecretStr; sem chave, usa "" (vazio).
        segredo = self.langfuse_secret_key.get_secret_value() if self.langfuse_secret_key else ""
        # bool(...) dá True só se a chave pública E a secreta tiverem conteúdo.
        return bool(self.langfuse_public_key and segredo)


settings = Settings()