from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health
from app.config import Settings, get_settings
from app.services import Services, build_services, close_services


def create_app(settings: Settings | None = None, services: Services | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if services is not None:
            yield
            return
        app.state.services = await build_services(settings)
        try:
            yield
        finally:
            await close_services(app.state.services)

    app = FastAPI(title="PDF RAG Chat API", lifespan=lifespan)
    app.state.settings = settings
    if services is not None:
        app.state.services = services

    app.include_router(health.router, prefix="/api")
    return app
