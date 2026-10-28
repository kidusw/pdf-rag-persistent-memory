from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.embeddings import DeterministicFakeEmbedding
from qdrant_client import QdrantClient
from reportlab.pdfgen import canvas

from app.config import Settings
from app.main import create_app
from app.rag.vectorstore import ensure_collection, make_vector_store
from app.services import Services
from app.storage.chats import InMemoryChatRepository


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        openai_api_key="test",
        upload_dir=str(tmp_path / "uploads"),
        embedding_dim=32,
        _env_file=None,
    )


@pytest.fixture
def qdrant(settings) -> QdrantClient:
    client = QdrantClient(":memory:")
    ensure_collection(client, settings.qdrant_collection, settings.embedding_dim)
    return client


@pytest.fixture
def embeddings(settings) -> DeterministicFakeEmbedding:
    return DeterministicFakeEmbedding(size=settings.embedding_dim)


@pytest.fixture
def vector_store(qdrant, settings, embeddings):
    return make_vector_store(qdrant, settings.qdrant_collection, embeddings)


@pytest.fixture
def make_pdf(tmp_path):
    """Write a PDF with one page per string; an empty string makes a blank page."""

    def _make(pages: list[str], name: str = "doc.pdf") -> Path:
        path = tmp_path / "pdfs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        c = canvas.Canvas(str(path))
        for text in pages:
            if text:
                c.drawString(72, 720, text)
            c.showPage()
        c.save()
        return path

    return _make


@pytest.fixture
def services(qdrant, vector_store) -> Services:
    return Services(
        chat_repo=InMemoryChatRepository(), qdrant=qdrant, vector_store=vector_store, rag_chain=None
    )


@pytest.fixture
async def client(settings, services):
    app = create_app(settings, services=services)
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as c:
        yield c
