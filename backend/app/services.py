from dataclasses import dataclass
from typing import Any

from app.config import Settings


@dataclass
class Services:
    """Long-lived clients shared by request handlers. Tests build this with fakes."""

    chat_repo: Any
    qdrant: Any
    vector_store: Any
    rag_chain: Any


async def build_services(settings: Settings) -> Services:
    raise NotImplementedError


async def close_services(services: Services) -> None:
    raise NotImplementedError
