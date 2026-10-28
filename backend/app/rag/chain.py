from collections.abc import AsyncIterator

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.vectorstores import VectorStore

from app.rag.prompts import CONTEXTUALIZE_PROMPT, QA_PROMPT
from app.storage.models import Message


def format_context(docs: list[Document]) -> str:
    return "\n\n".join(
        f"[{d.metadata['filename']} p.{d.metadata['page']}]\n{d.page_content}" for d in docs
    )


def to_lc_history(messages: list[Message]) -> list[BaseMessage]:
    return [HumanMessage(m.content) if m.role == "user" else AIMessage(m.content) for m in messages]


class RagChain:
    """History-aware RAG in three explicit steps: rewrite -> retrieve -> stream answer."""

    def __init__(self, llm: BaseChatModel, vector_store: VectorStore, k: int) -> None:
        self.llm = llm
        self.vector_store = vector_store
        self.k = k

    async def retrieve(self, question: str, history: list[BaseMessage]) -> list[Document]:
        query = question
        if history:
            rewrite = CONTEXTUALIZE_PROMPT | self.llm | StrOutputParser()
            query = await rewrite.ainvoke({"chat_history": history, "input": question})
        return await self.vector_store.asimilarity_search(query, k=self.k)

    async def stream_answer(
        self, question: str, history: list[BaseMessage], docs: list[Document]
    ) -> AsyncIterator[str]:
        chain = QA_PROMPT | self.llm | StrOutputParser()
        async for text in chain.astream(
            {"context": format_context(docs), "chat_history": history, "input": question}
        ):
            if text:
                yield text
