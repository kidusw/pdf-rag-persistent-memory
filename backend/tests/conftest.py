import itertools
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage
from pydantic import Field
from qdrant_client import QdrantClient
from reportlab.pdfgen import canvas

from app.config import Settings
from app.main import create_app
from app.rag.chain import RagChain
from app.rag.ingest import ingest_pdf
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


class RecordingFakeLLM(GenericFakeChatModel):
    """Fake chat model that streams word by word and records every prompt it receives."""

    calls: list[list[BaseMessage]] = Field(default_factory=list)

    def _generate(self, messages, *args: Any, **kwargs: Any):
        self.calls.append(messages)
        return super()._generate(messages, *args, **kwargs)

    def _stream(self, messages, *args: Any, **kwargs: Any):
        self.calls.append(messages)
        yield from super()._stream(messages, *args, **kwargs)


@pytest.fixture
def fake_llm():
    def _make(*responses: str) -> RecordingFakeLLM:
        return RecordingFakeLLM(messages=iter([AIMessage(r) for r in responses]))

    return _make


@pytest.fixture
def services(qdrant, vector_store, settings) -> Services:
    llm = RecordingFakeLLM(messages=itertools.cycle([AIMessage("Cats purr loudly.")]))
    return Services(
        chat_repo=InMemoryChatRepository(),
        qdrant=qdrant,
        vector_store=vector_store,
        rag_chain=RagChain(llm, vector_store, k=settings.retrieval_k),
    )


@pytest.fixture
async def client(settings, services):
    app = create_app(settings, services=services)
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as c:
        yield c


@pytest.fixture
def upload_sample(make_pdf, vector_store, qdrant, settings):
    ingest_pdf(make_pdf(["cats purr"]), "c.pdf", vector_store, qdrant, settings)
