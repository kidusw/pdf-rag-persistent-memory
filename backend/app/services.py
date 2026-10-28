from dataclasses import dataclass
from typing import Any

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pymongo import AsyncMongoClient
from qdrant_client import QdrantClient

from app.config import Settings
from app.rag.chain import RagChain
from app.rag.vectorstore import ensure_collection, make_vector_store
from app.storage.chats import MongoChatRepository


@dataclass
class Services:
    """Long-lived clients shared by request handlers. Tests build this with fakes."""

    chat_repo: Any
    qdrant: Any
    vector_store: Any
    rag_chain: Any
    mongo_client: Any = None


async def build_services(settings: Settings) -> Services:
    qdrant = QdrantClient(url=settings.qdrant_url)
    ensure_collection(qdrant, settings.qdrant_collection, settings.embedding_dim)
    embeddings = OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key)
    vector_store = make_vector_store(qdrant, settings.qdrant_collection, embeddings)

    mongo_client = AsyncMongoClient(settings.mongo_uri, tz_aware=True)
    chat_repo = MongoChatRepository(mongo_client[settings.mongo_db])
    await chat_repo.ensure_indexes()

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
        streaming=True,
    )
    return Services(
        chat_repo=chat_repo,
        qdrant=qdrant,
        vector_store=vector_store,
        rag_chain=RagChain(llm, vector_store, settings.retrieval_k),
        mongo_client=mongo_client,
    )


async def close_services(services: Services) -> None:
    if services.mongo_client is not None:
        await services.mongo_client.close()
    services.qdrant.close()
