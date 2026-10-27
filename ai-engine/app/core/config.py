from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "AegisAI Engine"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:change_me@localhost:5432/aegis_ai"
    REDIS_URL: str = "redis://localhost:6379"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL_NAME: str = "llama3.2"
    EMBEDDING_MODEL_NAME: str = "nomic-embed-text"

settings = Settings()
