import pytest

from app.storage.chats import InMemoryChatRepository
from app.storage.models import new_message


@pytest.fixture
def repo():
    return InMemoryChatRepository()


async def test_create_then_get(repo):
    chat = await repo.create()
    got = await repo.get(chat.id)
    assert got.id == chat.id
    assert got.title == ""
    assert got.messages == []


async def test_append_sets_title_once_and_truncates(repo):
    chat = await repo.create()
    await repo.append_messages(chat.id, [new_message("user", "q1")], title_if_empty="x" * 80)
    await repo.append_messages(chat.id, [new_message("user", "q2")], title_if_empty="other")
    got = await repo.get(chat.id)
    assert got.title == "x" * 60
    assert [m.content for m in got.messages] == ["q1", "q2"]


async def test_list_newest_first(repo):
    a = await repo.create()
    b = await repo.create()
    await repo.append_messages(a.id, [new_message("user", "hi")], "hi")
    assert [c.id for c in await repo.list()][:2] == [a.id, b.id]


async def test_delete_and_missing(repo):
    chat = await repo.create()
    assert await repo.delete(chat.id) is True
    assert await repo.get(chat.id) is None
    assert await repo.delete(chat.id) is False
    assert await repo.append_messages("nope", [], "") is False


async def test_sources_round_trip(repo):
    chat = await repo.create()
    msg = new_message("assistant", "a", [{"filename": "a.pdf", "page": 3, "snippet": "s"}])
    await repo.append_messages(chat.id, [msg], "t")
    got = await repo.get(chat.id)
    assert got.messages[0].sources[0].page == 3
    assert got.messages[0].id == msg.id
