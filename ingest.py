# ingest.py
import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters.character import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

PERSIST_DIR = "./chroma_db"
COLLECTION_NAME = "rag_collection"

def ingest_pdf(file_path: str):
    """
    Load, split, embed, and store a PDF in ChromaDB.
    """
    print(f"📘 Ingesting PDF: {file_path}")

    # Step 1: Load the PDF
    loader = PyPDFLoader(file_path)
    documents = loader.load()

    # Step 2: Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = splitter.split_documents(documents)

    # Step 3: Create embeddings and store in Chroma
    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=PERSIST_DIR,
        collection_name=COLLECTION_NAME
    )

    vectorstore.persist()
    print(f"✅ Stored {len(chunks)} chunks in Chroma.")
    return {"message": "PDF ingested successfully", "chunks": len(chunks)}
