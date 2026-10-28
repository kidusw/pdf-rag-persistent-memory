from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage

from app.rag.chain import RagChain, format_context, to_lc_history
from app.rag.ingest import ingest_pdf
from app.storage.models import new_message


async def test_no_history_skips_rewrite(fake_llm, vector_store, make_pdf, qdrant, settings):
    ingest_pdf(make_pdf(["cats purr"]), "c.pdf", vector_store, qdrant, settings)
    llm = fake_llm("unused")
    docs = await RagChain(llm, vector_store, k=4).retrieve("cats?", [])
    assert llm.calls == []
    assert docs[0].metadata["filename"] == "c.pdf"


async def test_history_triggers_rewrite(fake_llm, vector_store, make_pdf, qdrant, settings):
    ingest_pdf(make_pdf(["cats purr"]), "c.pdf", vector_store, qdrant, settings)
    llm = fake_llm("do cats purr?")
    await RagChain(llm, vector_store, k=4).retrieve(
        "do they?", [HumanMessage("cats"), AIMessage("ok")]
    )
    assert len(llm.calls) == 1
    assert llm.calls[0][-1].content == "do they?"


async def test_stream_answer_yields_tokens_with_context(fake_llm, vector_store):
    llm = fake_llm("Cats purr loudly")
    docs = [Document("cats purr", metadata={"filename": "c.pdf", "page": 2})]
    tokens = [t async for t in RagChain(llm, vector_store, k=4).stream_answer("q", [], docs)]
    assert len(tokens) > 1
    assert "".join(tokens) == "Cats purr loudly"
    assert "[c.pdf p.2]" in llm.calls[0][0].content
    assert "Answer only from the provided context" in llm.calls[0][0].content


def test_format_context_and_history():
    docs = [
        Document("one", metadata={"filename": "a.pdf", "page": 1}),
        Document("two", metadata={"filename": "b.pdf", "page": 3}),
    ]
    assert format_context(docs) == "[a.pdf p.1]\none\n\n[b.pdf p.3]\ntwo"
    history = to_lc_history([new_message("user", "q"), new_message("assistant", "a")])
    assert [type(m) for m in history] == [HumanMessage, AIMessage]
    assert [m.content for m in history] == ["q", "a"]
