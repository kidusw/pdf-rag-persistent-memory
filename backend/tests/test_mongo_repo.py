import os
import uuid

import pytest
from pymongo import AsyncMongoClient

from app.storage.chats import MongoChatRepository
from tests.test_chat_repo import (  # noqa: F401  (re-run the contract against Mongo)
    test_append_sets_title_once_and_truncates,
    test_create_then_get,
    test_delete_and_missing,
    test_list_newest_first,
    test_sources_round_trip,
)

pytestmark = pytest.mark.integration


@pytest.fixture
async def repo():
    uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    client = AsyncMongoClient(uri, tz_aware=True)
    name = f"pdf_rag_test_{uuid.uuid4().hex}"
    repository = MongoChatRepository(client[name])
    await repository.ensure_indexes()
    try:
        yield repository
    finally:
        await client.drop_database(name)
        await client.close()
