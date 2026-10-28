from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "documents"

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "pdf_rag"

    upload_dir: str = "./data/uploads"
    max_upload_mb: int = 10

    chunk_size: int = 1000
    chunk_overlap: int = 200
    retrieval_k: int = 4
    history_window: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
