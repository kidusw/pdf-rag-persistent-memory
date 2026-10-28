from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, FilterSelector, MatchValue

from app.config import Settings
from app.rag.vectorstore import FILENAME_KEY


class EmptyDocumentError(ValueError):
    pass


@dataclass
class IngestResult:
    filename: str
    pages: int
    chunks: int


@dataclass
class DocumentInfo:
    filename: str
    chunks: int


def ingest_pdf(
    path: Path,
    filename: str,
    vector_store: QdrantVectorStore,
    client: QdrantClient,
    settings: Settings,
) -> IngestResult:
    """Index a PDF, replacing any chunks previously stored under the same filename."""
    pages = [
        Document(page_content=page.extract_text() or "", metadata={"filename": filename, "page": i})
        for i, page in enumerate(PdfReader(path).pages, start=1)
    ]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
    )
    chunks: list[Document] = [c for c in splitter.split_documents(pages) if c.page_content.strip()]
    if not chunks:
        raise EmptyDocumentError("No extractable text")

    client.delete(
        settings.qdrant_collection,
        points_selector=FilterSelector(
            filter=Filter(must=[FieldCondition(key=FILENAME_KEY, match=MatchValue(value=filename))])
        ),
    )
    vector_store.add_documents(chunks)
    return IngestResult(filename=filename, pages=len(pages), chunks=len(chunks))


def list_documents(client: QdrantClient, collection: str) -> list[DocumentInfo]:
    counts: Counter[str] = Counter()
    offset = None
    while True:
        points, offset = client.scroll(
            collection, limit=256, offset=offset, with_payload=True, with_vectors=False
        )
        counts.update(p.payload["metadata"]["filename"] for p in points)
        if offset is None:
            break
    return [DocumentInfo(filename=f, chunks=n) for f, n in sorted(counts.items())]
