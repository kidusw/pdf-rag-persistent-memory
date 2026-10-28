# PDF RAG Chat

A conversational Retrieval-Augmented Generation (RAG) app: upload PDFs, then have multi-turn conversations grounded in their content, with answers streamed token by token and the source pages cited.

## Overview

- **Upload** one or more PDFs (up to 10 MB each). They are split into chunks, embedded with OpenAI, and stored in Qdrant.
- **Chat** about them. Each question is first rewritten as a standalone question using the recent conversation, then the most relevant chunks are retrieved and passed to the chat model.
- **Streaming**: answers arrive over Server-Sent Events, with source chips (`file · p.N`) you can expand to see the snippet.
- **Persistence**: chats live in MongoDB, vectors in Qdrant, and uploaded files in a Docker volume, so everything survives restarts.

## Architecture

```
            browser
               │  http://localhost:8080
               ▼
   ┌────────────────────────┐
   │ frontend (nginx)       │  serves the React build,
   │ :80 → host :8080       │  proxies /api/* (SSE unbuffered, 50 MB body limit)
   └───────────┬────────────┘
               │ /api
               ▼
   ┌────────────────────────┐
   │ backend (FastAPI)      │  ingestion, RAG chain, SSE streaming
   │ :8000 (internal only)  │
   └──────┬──────────┬──────┘
          │          │
          ▼          ▼
   ┌──────────┐ ┌──────────┐
   │ qdrant   │ │ mongo    │
   │ vectors  │ │ chats    │
   └──────────┘ └──────────┘
```

Only the frontend publishes a port. Data lives in the `qdrant_data`, `mongo_data` and `uploads` volumes.

## Quick start

Requires Docker with Compose and an OpenAI API key.

```bash
cp .env.example .env        # then set OPENAI_API_KEY=sk-...
docker compose up -d --build
```

Open <http://localhost:8080>, drop a PDF on the home page, and ask a question.

Stop with `docker compose down`. Add `-v` to also delete the stored chats, vectors and uploads.

## Local development without Docker

Run Qdrant and Mongo in containers with their ports published temporarily, for example with a `docker-compose.override.yml`:

```yaml
services:
  qdrant:
    ports: ["127.0.0.1:6333:6333"]
  mongo:
    ports: ["127.0.0.1:27017:27017"]
```

```bash
docker compose up -d qdrant mongo
```

Backend (Python 3.12, [uv](https://docs.astral.sh/uv/)). It reads settings from the environment or from `backend/.env`, and its defaults point at `localhost`:

```bash
cd backend
uv sync
OPENAI_API_KEY=sk-... uv run uvicorn app.main:create_app --factory --reload
```

Frontend (Node 22). The Vite dev server proxies `/api` to `http://localhost:8000`:

```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173
```

## Configuration

Set these in `.env`. Compose overrides `QDRANT_URL`, `MONGO_URI` and `UPLOAD_DIR` for the containers.

| Variable | Default | Notes |
|---|---|---|
| `OPENAI_API_KEY` | none (required) | Startup fails with a clear message if missing |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat model |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | |
| `EMBEDDING_DIM` | `1536` | Vector size for the Qdrant collection; must match the embedding model |
| `QDRANT_URL` | `http://localhost:6333` | Compose sets `http://qdrant:6333` |
| `QDRANT_COLLECTION` | `documents` | |
| `MONGO_URI` | `mongodb://localhost:27017` | Compose sets `mongodb://mongo:27017` |
| `MONGO_DB` | `pdf_rag` | Chats are stored in the `chats` collection |
| `UPLOAD_DIR` | `./data/uploads` | Compose sets `/data/uploads` |
| `CHUNK_SIZE` | `1000` | Characters per chunk |
| `CHUNK_OVERLAP` | `200` | |
| `RETRIEVAL_K` | `4` | Chunks retrieved per question |
| `HISTORY_WINDOW` | `10` | Recent messages used by the rewrite and answer steps |
| `MAX_UPLOAD_MB` | `10` | Per-file PDF size limit |

If you change the embedding model to one with a different vector size, delete the Qdrant collection (or the `qdrant_data` volume) and re-upload your PDFs.

## API

All routes are under `/api`.

| Method | Path | Request | Response |
|---|---|---|---|
| `GET` | `/health` | none | `{"status":"ok"}` |
| `POST` | `/documents` | multipart `files` (one or more) | `{"results":[{"filename","pages","chunks"}], "errors":[{"filename","detail"}]}` |
| `GET` | `/documents` | none | `[{"filename","chunks"}]` |
| `POST` | `/chats` | none | the new chat: `{"id","title","created_at","updated_at","messages":[]}` |
| `GET` | `/chats` | none | `[{"id","title","updated_at"}]`, newest first |
| `GET` | `/chats/{id}` | none | the full chat; 404 if missing |
| `DELETE` | `/chats/{id}` | none | 204; 404 if missing |
| `POST` | `/chats/{id}/messages` | JSON `{"content":"..."}` | `text/event-stream` |

Uploads report problems per file, so one bad file doesn't fail the others: oversized files get `"File exceeds 10 MB limit"`, and unreadable or text-less PDFs also land in `errors`.

The messages stream sends:

```
event: sources   data: [{"filename","page","snippet"}]
event: token     data: {"text":"..."}          (repeated)
event: done      data: {"message_id":"..."}
```

If something fails after the stream starts, it sends `event: error` with `{"detail":"..."}` and closes. Before streaming, it returns 404 for an unknown chat, 422 for empty content, and 409 when no documents are indexed yet. The user message and the (possibly partial) answer are saved even if the client disconnects mid-stream.

Example:

```bash
curl -F "files=@report.pdf" http://localhost:8080/api/documents
id=$(curl -s -X POST http://localhost:8080/api/chats | sed -E 's/.*"id":"([^"]+)".*/\1/')
curl -N -H 'Content-Type: application/json' \
  -d '{"content":"What is this report about?"}' \
  http://localhost:8080/api/chats/$id/messages
```

## Testing

```bash
# Backend unit tests (in-memory Qdrant, fake LLM and embeddings) and lint
cd backend && uv run pytest && uv run ruff check .

# Backend integration tests against a real Mongo
docker compose run --rm backend-tests

# Frontend tests, lint and type-checked build
cd frontend && npm test && npm run lint && npm run build

# End-to-end smoke test against the running stack (needs a real OPENAI_API_KEY)
bash scripts/smoke.sh http://localhost:8080
```

## Project layout

```
├── docker-compose.yml        # frontend, backend, qdrant, mongo (+ backend-tests profile)
├── .env.example
├── backend/
│   ├── Dockerfile            # runtime and test targets
│   ├── pyproject.toml, uv.lock
│   ├── app/
│   │   ├── main.py           # app factory
│   │   ├── config.py         # typed settings
│   │   ├── services.py       # Qdrant, Mongo, OpenAI wiring
│   │   ├── api/              # health, documents, chats, messages (SSE)
│   │   ├── rag/              # vector store, ingestion, prompts, chain
│   │   └── storage/          # chat models and repositories
│   └── tests/
├── frontend/
│   ├── Dockerfile, nginx.conf
│   └── src/
│       ├── api/              # typed client and SSE parser
│       ├── components/       # sidebar, messages, composer, uploads
│       ├── hooks/            # useChatStream
│       ├── pages/            # HomePage, ChatPage
│       └── stores/           # Zustand chat and document stores
├── scripts/
│   ├── smoke.sh              # end-to-end check
│   └── fixtures/sample.pdf
└── docs/superpowers/specs/   # design spec
```
