import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app
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
def services() -> Services:
    return Services(
        chat_repo=InMemoryChatRepository(), qdrant=None, vector_store=None, rag_chain=None
    )


@pytest.fixture
async def client(settings, services):
    app = create_app(settings, services=services)
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as c:
        yield c
