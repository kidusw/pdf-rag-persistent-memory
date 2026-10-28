from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PayloadSchemaType, VectorParams

FILENAME_KEY = "metadata.filename"


class CollectionDimensionMismatch(RuntimeError):
    pass


def ensure_collection(client: QdrantClient, name: str, dim: int) -> None:
    """Create the collection if missing; refuse to run against one with a different size."""
    if client.collection_exists(name):
        actual = client.get_collection(name).config.params.vectors.size
        if actual != dim:
            raise CollectionDimensionMismatch(
                f"Collection '{name}' has vector size {actual}, expected {dim}. "
                "Delete the collection (or the qdrant_data volume) and re-upload your PDFs."
            )
        return
    client.create_collection(name, vectors_config=VectorParams(size=dim, distance=Distance.COSINE))
    client.create_payload_index(name, FILENAME_KEY, field_schema=PayloadSchemaType.KEYWORD)


def make_vector_store(client: QdrantClient, name: str, embeddings: Embeddings) -> QdrantVectorStore:
    # ensure_collection already checked the vector size; skip langchain's own check,
    # which embeds a probe string and so needs network access at startup.
    return QdrantVectorStore(
        client=client,
        collection_name=name,
        embedding=embeddings,
        validate_collection_config=False,
    )


def collection_is_empty(client: QdrantClient, name: str) -> bool:
    return client.count(name, exact=True).count == 0
