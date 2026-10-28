from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.services import Services


async def test_health_returns_ok(settings):
    services = Services(chat_repo=None, qdrant=None, vector_store=None, rag_chain=None)
    app = create_app(settings, services=services)
    async with AsyncClient(transport=ASGITransport(app), base_url="http://t") as c:
        r = await c.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
