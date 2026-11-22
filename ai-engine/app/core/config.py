from urllib.parse import urlsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "AegisAI Engine"
    DATABASE_URL: str = (
        "postgresql+asyncpg://USER:PASSWORD@YOUR-ENDPOINT-pooler.region.aws.neon.tech/"
        "DATABASE?ssl=require"
    )
    REDIS_URL: str = "redis://localhost:6379/0"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL_NAME: str = "llama3.2"
    EMBEDDING_MODEL_NAME: str = "nomic-embed-text"
    RAG_FAITHFULNESS_THRESHOLD: float = 0.70
    RAG_EVALUATION_TIMEOUT_SECONDS: float = 30.0
    RAG_STRICT_EVALUATION: bool = False
    # Chunks scoring below this cosine similarity are dropped before generation.
    # Tune per embedding model: relevant ~0.75, unrelated ~0.3 on nomic-embed-text.
    RAG_MIN_SCORE: float = 0.50
    # Set false once tables exist: shared Neon DB, don't run DDL on every reload.
    DB_BOOTSTRAP_ON_STARTUP: bool = True
    # Set true only when debugging SQL; it logs every statement.
    DB_ECHO: bool = False

    @property
    def DB_IS_POOLED(self) -> bool:
        """True for Neon's PgBouncer endpoint (host contains '-pooler')."""
        return "-pooler" in (urlsplit(self.DATABASE_URL).hostname or "")


settings = Settings()