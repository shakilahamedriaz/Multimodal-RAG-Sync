from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/rag_db"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # OpenAI
    openai_api_key: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # Cohere
    cohere_api_key: str = ""

    # Storage
    storage_backend: str = "local"
    local_storage_path: str = "./storage"

    # Security / Auth
    api_key_secret: str = "change-me-in-production"
    auth_enabled: bool = False   # set True in production

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: List[str] = ["http://localhost:3000"]

    # Retrieval defaults
    default_top_k: int = 20
    default_rerank_n: int = 5
    default_alpha: float = 0.5
    confidence_threshold: float = 0.35

    # Reranker: "local" (cross-encoder) or "cohere" (Cohere Rerank API)
    reranker_backend: str = "local"

    # Rate limiting (requests per minute per IP)
    rate_limit_query: str = "20/minute"
    rate_limit_upload: str = "60/minute"


settings = Settings()
