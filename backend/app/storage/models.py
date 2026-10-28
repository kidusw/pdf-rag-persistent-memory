import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["user", "assistant"]


def utcnow() -> datetime:
    return datetime.now(UTC)


class Source(BaseModel):
    filename: str
    page: int
    snippet: str


class Message(BaseModel):
    id: str
    role: Role
    content: str
    sources: list[Source] = Field(default_factory=list)
    created_at: datetime


class ChatSummary(BaseModel):
    id: str
    title: str
    updated_at: datetime


class Chat(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[Message] = Field(default_factory=list)


def new_message(
    role: Role, content: str, sources: Iterable[Source | dict[str, Any]] = ()
) -> Message:
    return Message(
        id=str(uuid.uuid4()),
        role=role,
        content=content,
        sources=list(sources),
        created_at=utcnow(),
    )
