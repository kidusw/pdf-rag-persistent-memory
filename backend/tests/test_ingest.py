import pytest

from app.rag.ingest import DocumentInfo, EmptyDocumentError, ingest_pdf, list_documents
from app.rag.vectorstore import collection_is_empty


def test_ingest_sets_filename_and_page(make_pdf, vector_store, qdrant, settings):
    r = ingest_pdf(make_pdf(["alpha text", "beta text"]), "doc.pdf", vector_store, qdrant, settings)
    assert (r.filename, r.pages) == ("doc.pdf", 2)
    assert r.chunks >= 2
    hits = vector_store.similarity_search("beta text", k=10)
    assert {(h.metadata["filename"], h.metadata["page"]) for h in hits} >= {
        ("doc.pdf", 1),
        ("doc.pdf", 2),
    }
    assert set(hits[0].metadata) >= {"filename", "page"}
    assert "source" not in hits[0].metadata


def test_reupload_replaces_not_duplicates(make_pdf, vector_store, qdrant, settings):
    p = make_pdf(["alpha", "beta"])
    first = ingest_pdf(p, "doc.pdf", vector_store, qdrant, settings)
    ingest_pdf(p, "doc.pdf", vector_store, qdrant, settings)
    assert list_documents(qdrant, settings.qdrant_collection) == [
        DocumentInfo("doc.pdf", first.chunks)
    ]


def test_blank_pdf_raises(make_pdf, vector_store, qdrant, settings):
    with pytest.raises(EmptyDocumentError):
        ingest_pdf(make_pdf([""]), "blank.pdf", vector_store, qdrant, settings)


def test_collection_is_empty(qdrant, settings, make_pdf, vector_store):
    assert collection_is_empty(qdrant, settings.qdrant_collection)
    ingest_pdf(make_pdf(["x"]), "a.pdf", vector_store, qdrant, settings)
    assert not collection_is_empty(qdrant, settings.qdrant_collection)


def test_list_documents_groups_and_sorts(make_pdf, vector_store, qdrant, settings):
    ingest_pdf(make_pdf(["b"], "b.pdf"), "b.pdf", vector_store, qdrant, settings)
    ingest_pdf(make_pdf(["a"], "a.pdf"), "a.pdf", vector_store, qdrant, settings)
    assert [d.filename for d in list_documents(qdrant, settings.qdrant_collection)] == [
        "a.pdf",
        "b.pdf",
    ]
