import pytest
from pydantic import ValidationError

from app.config import Settings


def test_missing_openai_key_fails(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_defaults():
    s = Settings(openai_api_key="x", _env_file=None)
    assert (s.openai_model, s.embedding_model, s.retrieval_k, s.history_window) == (
        "gpt-4o-mini",
        "text-embedding-3-small",
        4,
        10,
    )
    assert (s.embedding_dim, s.max_upload_mb, s.qdrant_collection, s.mongo_db) == (
        1536,
        10,
        "documents",
        "pdf_rag",
    )
