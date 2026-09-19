from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'postgresql://lenny:lenny-local-only@localhost:5432/lenny'
    ollama_base_url: str = 'http://localhost:11434'
    embedding_model: str = 'nomic-embed-text'
    agent_url: str = 'http://localhost:3001'
    default_llm_provider: Literal['ollama', 'anthropic', 'gemini'] = 'ollama'
    retrieval_threshold: float = 0.45
    retrieval_mode: Literal['vector', 'lexical'] = 'vector'
    top_k: int = 6
    model_timeout: int = 240
    cors_origin: str = 'http://localhost:3000'
    admin_email: str = ''
    admin_password: str = ''
    session_days: int = 30

@lru_cache
def settings():
    return Settings()
