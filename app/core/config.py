from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # GitHub
    GITHUB_TOKEN: str
    GITHUB_WEBHOOK_SECRET: str
    GITHUB_APP_ID: str | None = None
    GITHUB_APP_PRIVATE_KEY_PATH: str | None = None

    # Ollama
    OLLAMA_MODEL: str = "deepseek-coder"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Anthropic
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str | None = None
    ANTHROPIC_MAX_TOKENS: int = 4096

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/code_review_agent"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "code_review_agent"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_URL: str = "redis://localhost:6379/1"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION_NAME: str = "codebase_patterns"

    # Embeddings
    EMBEDDING_PROVIDER: str = "huggingface"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Application
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_SECRET_KEY: str
    LOG_LEVEL: str = "INFO"

    # Celery
    CELERY_WORKER_CONCURRENCY: int = 4
    CELERY_TASK_TIMEOUT: int = 300

    # MCP
    MCP_SERVER_PORT: int = 9000
    LLM_PROVIDER: str = "ollama"
    LLM_MODEL: str = "deepseek-coder"

    # Security & Limits
    MAX_FILES_TO_REVIEW: int = 20
    MAX_COMMENTS_PER_REVIEW: int = 15
    REVIEW_TIMEOUT_SECONDS: int = 300
    EXCLUDE_PATTERNS: str = "*.lock,*.exe,*.dll,*.so,*.bin,node_modules/,dist/,build/,vendor/,__pycache__/"
    RATE_LIMIT_WEBHOOKS_PER_MINUTE: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
