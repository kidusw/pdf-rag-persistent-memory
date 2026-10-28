from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.deps import get_services
from app.services import Services
from app.storage.models import Chat, ChatSummary

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_chat(services: Services = Depends(get_services)) -> Chat:
    return await services.chat_repo.create()


@router.get("")
async def list_chats(services: Services = Depends(get_services)) -> list[ChatSummary]:
    return await services.chat_repo.list()


@router.get("/{chat_id}")
async def get_chat(chat_id: str, services: Services = Depends(get_services)) -> Chat:
    chat = await services.chat_repo.get(chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(chat_id: str, services: Services = Depends(get_services)) -> Response:
    if not await services.chat_repo.delete(chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
