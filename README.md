# PDF RAG Chat

A conversational Retrieval-Augmented Generation (RAG) application that lets you upload PDFs and ask questions about them with persistent chat history.

## Overview

Upload one or more PDFs, then have a multi-turn conversation grounded in their content. The backend indexes documents into a ChromaDB vector store and uses OpenAI to answer questions with awareness of the full conversation history. Sessions are persisted in MongoDB so conversations survive restarts.

## Tech Stack

**Backend**

- [FastAPI](https://fastapi.tiangolo.com/) — REST API server
- [LangChain](https://python.langchain.com/) — RAG chain orchestration
- [ChromaDB](https://www.trychroma.com/) — Local vector store for document embeddings
- [OpenAI](https://openai.com/) — Embeddings (`text-embedding-ada-002`) and chat (`gpt-4o-mini`)
- [MongoDB](https://www.mongodb.com/) — Persistent chat history storage

**Frontend**

- [React](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/) + [Vite](https://vitejs.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [React Router](https://reactrouter.com/) — Client-side routing
- [ReactMarkdown](https://github.com/remarkjs/react-markdown) — Renders AI responses as Markdown

## Project Structure

```
├── server.py          # FastAPI app and route handlers
├── ragchain.py        # LangChain RAG chain (history-aware retrieval)
├── ingestion.py       # PDF loading, chunking, and ChromaDB indexing
├── mongo_db.py        # MongoDB chat history CRUD
├── db.py              # SQLite fallback for chat history
├── src/               # React frontend
│   └── components/    # UI components (Sidebar, ChatHistory, upload forms, etc.)
├── uploaded_pdfs/     # Uploaded PDF storage
└── chroma_persist/    # ChromaDB persisted vector store
```

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- MongoDB instance (local or Atlas)
- OpenAI API key

### Backend

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...
API_KEY=mysecretapikey
MONGO_URI=mongodb://localhost:27017
MONGO_DB=rag_db
MONGO_COLLECTION=chat_history
CHROMA_PERSIST_DIR=./chroma_persist
CHROMA_COLLECTION_NAME=rag_collection
OPENAI_MODEL=gpt-4o-mini
UPLOAD_DIR=./uploaded_pdfs
```

Start the API server:

```bash
uvicorn server:app --reload --port 8000
```

### Frontend

```bash
cd src   # or use the frontend/ directory
npm install
npm run dev
```

The frontend runs on `http://localhost:5173` and proxies API calls to `http://localhost:8000`.

## API Reference

| Method   | Endpoint                | Description                                            |
| -------- | ----------------------- | ------------------------------------------------------ |
| `POST`   | `/upload-pdfs`          | Upload and ingest one or more PDFs into ChromaDB       |
| `POST`   | `/reindex`              | Rebuild the vector store from all PDFs in `UPLOAD_DIR` |
| `POST`   | `/query/conversational` | Ask a question with conversation history               |
| `GET`    | `/chat/all`             | List all chat sessions                                 |
| `GET`    | `/chat/{session_id}`    | Load messages for a session                            |
| `DELETE` | `/chat/{session_id}`    | Delete a chat session                                  |

### Example: Upload and Query

```bash
# Upload a PDF
curl -X POST http://localhost:8000/upload-pdfs \
  -F "files=@document.pdf"

# Ask a question
curl -X POST "http://localhost:8000/query/conversational?session_id=abc123" \
  -F "question=What is the main topic of this document?"
```

## How It Works

1. **Ingestion** — Uploaded PDFs are split into 1000-character chunks with 200-character overlap using LangChain's `RecursiveCharacterTextSplitter`, then embedded with OpenAI and stored in ChromaDB.

2. **Retrieval** — On each query, a history-aware retriever first reformulates the user's question as a standalone question using the conversation history, then retrieves relevant chunks from ChromaDB.

3. **Generation** — Retrieved chunks and the full conversation history are passed to `gpt-4o-mini`, which returns a Markdown-formatted answer.

4. **Persistence** — Each exchange is appended to the session's document in MongoDB, so conversations can be resumed across sessions.
