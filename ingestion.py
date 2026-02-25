# import os
# from typing import List
# from pypdf import PdfReader
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain_openai import OpenAIEmbeddings
# from langchain_community.vectorstores import Chroma

# PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
# COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "rag_collection")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# # Reuse embedder globally
# EMBEDDER = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

# def fast_load_pdf(path):
#     reader = PdfReader(path)
#     docs = []
#     for i, page in enumerate(reader.pages):
#         text = page.extract_text() or ""
#         docs.append({"page": i, "text": text})
#     return docs

# def _split_documents(documents, chunk_size=1500, chunk_overlap=200):
#     splitter = RecursiveCharacterTextSplitter(
#         chunk_size=chunk_size,
#         chunk_overlap=chunk_overlap
#     )
#     return splitter.create_documents([d["text"] for d in documents])

# def ingest_pdf(file_path: str):
#     if not os.path.exists(file_path):
#         raise FileNotFoundError(file_path)

#     docs = fast_load_pdf(file_path)
#     chunks = _split_documents(docs)

#     vs = Chroma(
#         persist_directory=PERSIST_DIR,
#         collection_name=COLLECTION_NAME,
#         embedding_function=EMBEDDER,
#     )

#     vs.add_documents(chunks, batch_size=128)
#     vs.persist()

#     return {"file": os.path.basename(file_path), "chunks": len(chunks)}


# def ingest_pdfs(file_paths: List[str]):
#     results = []
#     for p in file_paths:
#         results.append(ingest_pdf(p))
#     return results




# ingest.py
import os
from dotenv import load_dotenv
load_dotenv()

from typing import List
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters.character  import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_experimental.text_splitter import SemanticChunker

PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "rag_collection")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")



def _split_documents(documents, chunk_size=1000, chunk_overlap=200):
    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

    # chunker = SemanticChunker(embeddings)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    
    return splitter.split_documents(documents)

def ingest_pdf(file_path: str, chunk_size=1000, chunk_overlap=200):
    """
    Load a single PDF, split into chunks, and add to Chroma (appends).
    Returns metadata about ingestion.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)
    loader = PyPDFLoader(file_path)
    docs = loader.load()

    chunks = _split_documents(docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
    # Use from_documents which will append to existing collection if present
    vs = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=PERSIST_DIR,
        collection_name=COLLECTION_NAME,
    )   
    vs.persist()
    return {"file": os.path.basename(file_path), "chunks": len(chunks)}

def ingest_pdfs(file_paths: List[str], chunk_size=1000, chunk_overlap=200):
    results = []
    for p in file_paths:
        results.append(ingest_pdf(p, chunk_size=chunk_size, chunk_overlap=chunk_overlap))
    return results

def reindex_all(upload_dir: str = "./uploaded_pdfs"):
    """
    Re-ingest all PDFs in upload_dir (clears and rebuilds collection).
    WARNING: This removes previous collection and rebuilds it from files present.
    """
    # Remove existing chroma dir (simple approach)
    if os.path.exists(PERSIST_DIR):
        # safe remove: remove only collection files inside PERSIST_DIR
        # For simplicity, remove whole directory and recreate
        import shutil
        shutil.rmtree(PERSIST_DIR)
    os.makedirs(PERSIST_DIR, exist_ok=True)

    paths = []
    for fname in os.listdir(upload_dir):
        if fname.lower().endswith(".pdf"):
            paths.append(os.path.join(upload_dir, fname))
    return ingest_pdfs(paths)
