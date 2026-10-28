from __future__ import annotations

import itertools
import uuid
from typing import Protocol

from pymongo import DESCENDING
from pymongo.asynchronous.database import AsyncDatabase

from app.storage.models import Chat, ChatSummary, Message, utcnow

TITLE_MAX = 60


class ChatRepository(Protocol):
    async def create(self) -> Chat: ...
    async def list(self) -> list[ChatSummary]: ...
    async def get(self, chat_id: str) -> Chat | None: ...
    async def append_messages(
        self, chat_id: str, messages: list[Message], title_if_empty: str
    ) -> bool: ...
    async def delete(self, chat_id: str) -> bool: ...


def _new_chat() -> Chat:
    now = utcnow()
    return Chat(id=str(uuid.uuid4()), title="", created_at=now, updated_at=now, messages=[])


class InMemoryChatRepository:
    def __init__(self) -> None:
        self._chats: dict[str, Chat] = {}
        # Tie-breaker so ordering is stable even when timestamps collide.
        self._seq: dict[str, int] = {}
        self._counter = itertools.count()

    async def create(self) -> Chat:
        chat = _new_chat()
        self._chats[chat.id] = chat
        self._seq[chat.id] = next(self._counter)
        return chat.model_copy(deep=True)

    async def list(self) -> list[ChatSummary]:
        chats = sorted(
            self._chats.values(),
            key=lambda c: (c.updated_at, self._seq[c.id]),
            reverse=True,
        )
        return [ChatSummary(id=c.id, title=c.title, updated_at=c.updated_at) for c in chats]

    async def get(self, chat_id: str) -> Chat | None:
        chat = self._chats.get(chat_id)
        return chat.model_copy(deep=True) if chat else None

    async def append_messages(
        self, chat_id: str, messages: list[Message], title_if_empty: str
    ) -> bool:
        chat = self._chats.get(chat_id)
        if chat is None:
            return False
        chat.messages.extend(m.model_copy(deep=True) for m in messages)
        if not chat.title:
            chat.title = title_if_empty[:TITLE_MAX]
        chat.updated_at = utcnow()
        self._seq[chat_id] = next(self._counter)
        return True

    async def delete(self, chat_id: str) -> bool:
        self._seq.pop(chat_id, None)
        return self._chats.pop(chat_id, None) is not None


class MongoChatRepository:
    def __init__(self, db: AsyncDatabase) -> None:
        self._col = db["chats"]

    async def ensure_indexes(self) -> None:
        await self._col.create_index([("updated_at", DESCENDING)])

    async def create(self) -> Chat:
        chat = _new_chat()
        doc = chat.model_dump()
        doc["_id"] = doc.pop("id")
        await self._col.insert_one(doc)
        return chat

    async def list(self) -> list[ChatSummary]:
        cursor = self._col.find({}, {"title": 1, "updated_at": 1}).sort("updated_at", DESCENDING)
        return [
            ChatSummary(id=d["_id"], title=d["title"], updated_at=d["updated_at"])
            async for d in cursor
        ]

    async def get(self, chat_id: str) -> Chat | None:
        doc = await self._col.find_one({"_id": chat_id})
        if doc is None:
            return None
        doc["id"] = doc.pop("_id")
        return Chat.model_validate(doc)

    async def append_messages(
        self, chat_id: str, messages: list[Message], title_if_empty: str
    ) -> bool:
        result = await self._col.update_one(
            {"_id": chat_id},
            {
                "$push": {"messages": {"$each": [m.model_dump() for m in messages]}},
                "$set": {"updated_at": utcnow()},
            },
        )
        if result.matched_count == 0:
            return False
        await self._col.update_one(
            {"_id": chat_id, "title": ""}, {"$set": {"title": title_if_empty[:TITLE_MAX]}}
        )
        return True

    async def delete(self, chat_id: str) -> bool:
        result = await self._col.delete_one({"_id": chat_id})
        return result.deleted_count == 1
