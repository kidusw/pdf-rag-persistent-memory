from app.api.messages import MessageIn, post_message
from app.rag.chain import RagChain
from tests.helpers import FailingAfterFirstTokenLLM, parse_sse


async def ask(client, chat_id: str, content: str):
    return await client.post(f"/api/chats/{chat_id}/messages", json={"content": content})


async def test_stream_order_and_persistence(client, upload_sample):
    chat = (await client.post("/api/chats")).json()
    r = await ask(client, chat["id"], "what purrs?")
    events = parse_sse(r.text)
    assert r.headers["content-type"].startswith("text/event-stream")
    assert r.headers["x-accel-buffering"] == "no"
    assert events[0][0] == "sources"
    assert events[0][1][0] == {"filename": "c.pdf", "page": 1, "snippet": "cats purr"}
    assert {e for e, _ in events[1:-1]} == {"token"}
    assert "".join(d["text"] for e, d in events if e == "token") == "Cats purr loudly."
    assert events[-1][0] == "done"
    saved = (await client.get(f"/api/chats/{chat['id']}")).json()
    assert [m["role"] for m in saved["messages"]] == ["user", "assistant"]
    assert saved["messages"][1]["id"] == events[-1][1]["message_id"]
    assert saved["messages"][1]["content"] == "Cats purr loudly."
    assert saved["title"] == "what purrs?"
    assert saved["messages"][1]["sources"][0]["page"] == 1


async def test_second_message_sends_history(client, services, upload_sample):
    chat = (await client.post("/api/chats")).json()
    await ask(client, chat["id"], "what purrs?")
    services.rag_chain.llm.calls.clear()
    await ask(client, chat["id"], "how loud?")
    rewrite_prompt = services.rag_chain.llm.calls[0]
    assert [m.content for m in rewrite_prompt[1:]] == [
        "what purrs?",
        "Cats purr loudly.",
        "how loud?",
    ]


async def test_409_when_no_documents(client):
    chat = (await client.post("/api/chats")).json()
    r = await ask(client, chat["id"], "hi")
    assert r.status_code == 409
    assert r.json() == {"detail": "No documents indexed yet. Upload a PDF first."}


async def test_404_and_422(client, upload_sample):
    assert (await ask(client, "nope", "hi")).status_code == 404
    chat = (await client.post("/api/chats")).json()
    assert (await ask(client, chat["id"], "   ")).status_code == 422


async def test_llm_failure_mid_stream(client, services, upload_sample):  # Review Focus 4
    services.rag_chain = RagChain(FailingAfterFirstTokenLLM(), services.vector_store, k=4)
    chat = (await client.post("/api/chats")).json()
    events = parse_sse((await ask(client, chat["id"], "q")).text)
    assert events[-1] == ("error", {"detail": "rate limited"})
    saved = (await client.get(f"/api/chats/{chat['id']}")).json()
    assert [m["role"] for m in saved["messages"]] == ["user", "assistant"]
    assert saved["messages"][1]["content"] == "Partial"


async def test_failure_before_any_token_saves_only_user_message(client, services, upload_sample):
    class Boom(RagChain):
        async def retrieve(self, question, history):
            raise RuntimeError("qdrant down")

    services.rag_chain = Boom(services.rag_chain.llm, services.vector_store, k=4)
    chat = (await client.post("/api/chats")).json()
    events = parse_sse((await ask(client, chat["id"], "q")).text)
    assert events == [("error", {"detail": "qdrant down"})]
    saved = (await client.get(f"/api/chats/{chat['id']}")).json()
    assert [m["role"] for m in saved["messages"]] == ["user"]


async def test_client_disconnect_saves_partial_answer(services, settings, upload_sample):
    chat = await services.chat_repo.create()
    response = await post_message(
        chat.id, MessageIn(content="what purrs?"), services=services, settings=settings
    )
    stream = response.body_iterator
    assert (await anext(stream)).startswith("event: sources")
    assert (await anext(stream)).startswith("event: token")
    await stream.aclose()  # what Starlette does when the browser goes away
    saved = await services.chat_repo.get(chat.id)
    assert [m.role for m in saved.messages] == ["user", "assistant"]
    assert saved.messages[1].content == "Cats"
