import pytest
from qdrant_client import QdrantClient

from app.rag.vectorstore import CollectionDimensionMismatch, ensure_collection


def test_ensure_collection_idempotent_and_detects_mismatch():
    c = QdrantClient(":memory:")
    ensure_collection(c, "docs", 32)
    ensure_collection(c, "docs", 32)
    with pytest.raises(CollectionDimensionMismatch, match="vector size 32, expected 64"):
        ensure_collection(c, "docs", 64)
