import pytest
from langchain_core.embeddings import Embeddings
from qdrant_client import QdrantClient

from app.rag.vectorstore import CollectionDimensionMismatch, ensure_collection, make_vector_store


def test_ensure_collection_idempotent_and_detects_mismatch():
    c = QdrantClient(":memory:")
    ensure_collection(c, "docs", 32)
    ensure_collection(c, "docs", 32)
    with pytest.raises(CollectionDimensionMismatch, match="vector size 32, expected 64"):
        ensure_collection(c, "docs", 64)


class OfflineEmbeddings(Embeddings):
    """Raises if anything tries to embed, i.e. if the call would hit the network."""

    def embed_documents(self, texts):
        raise AssertionError("embedding called")

    def embed_query(self, text):
        raise AssertionError("embedding called")


def test_make_vector_store_does_not_embed_at_startup():
    c = QdrantClient(":memory:")
    ensure_collection(c, "docs", 32)
    make_vector_store(c, "docs", OfflineEmbeddings())
