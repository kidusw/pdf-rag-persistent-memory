import asyncio
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, StringConstraints

from app.api.sse import format_sse
from app.config import Settings
from app.deps import get_app_settings, get_services
from app.rag.chain import to_lc_history
from app.rag.vectorstore import collection_is_empty
from app.services import Services
from app.storage.models import Message, Source, new_message, utcnow

router = APIRouter(prefix="/chats", tags=["messages"])

SNIPPET_CHARS = 200


class MessageIn(BaseModel):
    content: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


@router.post("/{chat_id}/messages")
async def post_message(
    chat_id: str,
    body: MessageIn,
    services: Services = Depends(get_services),
    settings: Settings = Depends(get_app_settings),
) -> StreamingResponse:
    repo = services.chat_repo
    chat = await repo.get(chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    if collection_is_empty(services.qdrant, settings.qdrant_collection):
        raise HTTPException(
            status_code=409, detail="No documents indexed yet. Upload a PDF first."
        )

    content = body.content
    chain = services.rag_chain
    history = to_lc_history(chat.messages[-settings.history_window :])
    user_msg = new_message("user", content)
    assistant_id = str(uuid.uuid4())

    async def events():
        parts: list[str] = []
        sources: list[Source] = []
        try:
            docs = await chain.retrieve(content, history)
            sources = [
                Source(
                    filename=d.metadata["filename"],
                    page=d.metadata["page"],
                    snippet=d.page_content[:SNIPPET_CHARS],
                )
                for d in docs
            ]
            yield format_sse("sources", [s.model_dump() for s in sources])
            async for text in chain.stream_answer(content, history, docs):
                parts.append(text)
                yield format_sse("token", {"text": text})
            yield format_sse("done", {"message_id": assistant_id})
        except Exception as e:
            yield format_sse("error", {"detail": str(e)})
        finally:
            # Runs on success, error, and client disconnect, so partial answers are kept.
            answer = "".join(parts)
            to_save = [user_msg]
            if answer:
                to_save.append(
                    Message(
                        id=assistant_id,
                        role="assistant",
                        content=answer,
                        sources=sources,
                        created_at=utcnow(),
                    )
                )
            await asyncio.shield(repo.append_messages(chat_id, to_save, title_if_empty=content))

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
