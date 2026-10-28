# PDF RAG Chat: Modernization Design

**Date:** 2026-10-28
**Branch:** `modernize`
**Status:** Approved in conversation; awaiting written-spec review

## 1. Goal

Restructure the existing PDF RAG chat app into a clean, maintainable codebase that runs entirely with one `docker compose up`, replaces ChromaDB with Qdrant, adds streaming answers, and gives the UI a light refresh. Work is delivered incrementally, phase by phase, tracked in `plan.md`.

### What the user asked for
- Modernize and clean up the code; it is disorganized today.
- Dockerize everything so the app runs from a single command.
- Use Qdrant instead of Chroma.
- Streaming answers plus a modest UI refresh.
- A `plan.md` to track progress and build step by step.

### Decisions made during brainstorming
| Topic | Decision |
|---|---|
| Docker shape | Docker Compose, 4 services: `frontend`, `backend`, `qdrant`, `mongo` |
| Frontend scope | Clean up + SSE streaming + light visual refresh |
| RAG framework | Modern LangChain (`langchain-core`, `-openai`, `-qdrant`, `-text-splitters`) composed explicitly; no deprecated chain helpers |
| Chat storage | MongoDB stays |
| LLM provider | OpenAI stays |
| Auth | The half-applied `x-api-key` check is removed (the frontend never sent it) |
| Existing data | Not migrated; PDFs are re-uploaded once into the new stack |
| Dead code | Deleted (git history keeps it) |
| Document scope | Global: every chat searches all indexed PDFs, same as today |

### Non-goals
- Multi-user accounts or authentication.
- Per-chat document scoping.
- Switching LLM providers or adding local models.
- Production hosting, TLS, or cloud deployment.

## 2. Current state (problems this fixes)

**Backend:**
- 9 Python files at the repo root; only `server.py`, `ragchain.py`, `ingestion.py` and `mongo_db.py` are live. `main.py`, `conversational_rag_chain.py` and `ingest.py` are dead or commented out, and `db.py` is a half-used SQLite/Redis store.
- `DELETE /chat/{id}` calls the SQLite store, so chats are never deleted from MongoDB.
- The source file name is parsed with `split("\\")[1]`, which only works on Windows paths and breaks in a Linux container.
- `@app.post("query/new_chat")` is missing its leading slash and is unused.
- `ingestion.py` imports `langchain_experimental`, which is not a declared dependency.
- LangChain is pinned to 0.2.x and uses the deprecated `create_history_aware_retriever` and `create_retrieval_chain`.
- `pyproject.toml` and `requirements.txt` disagree.
- Messages are stored in Mongo as a JSON string.
- Re-uploading a PDF duplicates its chunks in the vector store.

**Frontend:**
- `src/` and `frontend/src/` are identical copies; the root `package.json` duplicates `frontend/package.json`.
- 10 of 14 components are dead and call `/api/...` endpoints that don't exist.
- Every request is hardcoded to `http://localhost:8000`.
- The sidebar imports a delete icon but there is no delete in the UI.

## 3. Architecture

### 3.1 Services (`docker-compose.yml`)

| Service | Image | Exposed port | Role | Volume |
|---|---|---|---|---|
| `frontend` | multi-stage: `node` build, then `nginx` | **8080** (the only host port) | Serves the built React app; proxies `/api/*` to `backend:8000` (with buffering off for SSE) | none |
| `backend` | `python:3.12-slim` + `uv` | internal | FastAPI app | `uploads` mounted at `/data/uploads` |
| `qdrant` | `qdrant/qdrant` (pinned tag) | internal (6333 optionally published for the dashboard) | Vector store | `qdrant_data` |
| `mongo` | `mongo:7` | internal | Chat history | `mongo_data` |

- `backend` uses `depends_on` with `condition: service_healthy` for `qdrant` and `mongo`.
- `frontend` depends on `backend` being healthy (`/api/health`).
- One `.env` at the repo root (the only required value is `OPENAI_API_KEY`); `.env.example` is committed.
- The browser and the API share one origin, so no CORS configuration is needed.

### 3.2 Repository layout

```
backend/
  app/
    __init__.py
    main.py            # create_app(): routers, lifespan (clients, ensure collection)
    config.py          # Settings (pydantic-settings)
    deps.py            # FastAPI dependencies: settings, chat repo, vector store, chain
    api/
      chats.py         # /api/chats CRUD
      documents.py     # /api/documents upload + list
      messages.py      # /api/chats/{id}/messages (SSE)
      health.py        # /api/health
    rag/
      vectorstore.py   # Qdrant client, collection setup, dimension check
      ingest.py        # PDF -> chunks -> Qdrant
      chain.py         # rewrite -> retrieve -> stream
      prompts.py       # prompt templates
    storage/
      chats.py         # ChatRepository protocol + MongoChatRepository
  tests/
    conftest.py
    test_ingest.py
    test_chain.py
    test_api_chats.py
    test_api_messages.py
    test_api_documents.py
    test_mongo_repo.py     # marked integration
  pyproject.toml           # uv-managed, pinned; uv.lock committed
  Dockerfile
  .dockerignore
frontend/
  src/ ... (see section 5)
  Dockerfile
  nginx.conf
  .dockerignore
docker-compose.yml
.env.example
plan.md
README.md
docs/superpowers/specs/2026-10-28-modernize-design.md
```

**Removed by the end:**
- Root `server.py`, `main.py`, `ragchain.py`, `conversational_rag_chain.py`, `ingestion.py`, `ingest.py`, `db.py`, `mongo_db.py`, `requirements.txt` and the root `pyproject.toml`/`.python-version`.
- Root `src/`, `public/`, `index.html`, `package.json`, `package-lock.json`, `vite.config.ts`, `tsconfig*.json` and `eslint.config.js`.
- Dead frontend components: `AskQuestion`, `Charts`, `Question`, `StreamQuestion`, `Upload`, `UploadAndQueryStream`, `UploadAndQuestion`, `UploadOnly`, `UploadQuery`, `UploadQuestion`, plus `useLLMStream`, `useChats` and the old `ChatPage`.

## 4. Backend

### 4.1 Configuration (`app/config.py`)

| Variable | Default | Notes |
|---|---|---|
| `OPENAI_API_KEY` | none (required) | Startup fails with a clear message if missing |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat model |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | 1536 dimensions |
| `QDRANT_URL` | `http://localhost:6333` | Compose sets `http://qdrant:6333` |
| `QDRANT_COLLECTION` | `documents` | |
| `MONGO_URI` | `mongodb://localhost:27017` | Compose sets `mongodb://mongo:27017` |
| `MONGO_DB` | `pdf_rag` | Collection name is fixed: `chats` |
| `UPLOAD_DIR` | `./data/uploads` | Compose sets `/data/uploads` |
| `CHUNK_SIZE` | `1000` | |
| `CHUNK_OVERLAP` | `200` | |
| `RETRIEVAL_K` | `4` | |
| `HISTORY_WINDOW` | `10` | Messages passed to the rewrite and answer steps |

The defaults point at `localhost` so the backend can also run outside Docker against containerized Qdrant and Mongo.

### 4.2 Vector store (`rag/vectorstore.py`)
- `QdrantClient(url=settings.qdrant_url)`; the tests pass `":memory:"`.
- `ensure_collection(client, name, dim)`: creates the collection with cosine distance if it is missing. If it exists with a different vector size, it raises `CollectionDimensionMismatch` and startup stops with a message telling the user to delete the collection and re-upload.
- A payload index on `metadata.filename` (keyword) supports delete-by-file and listing.
- It is wrapped in `langchain_qdrant.QdrantVectorStore` for add and search.

### 4.3 Ingestion (`rag/ingest.py`)
`ingest_pdf(path, filename, vector_store, settings) -> IngestResult(filename, pages, chunks)`
1. Load with `PyPDFLoader` (one Document per page).
2. Set the metadata to `{"filename": filename, "page": page_number_1_based}` and drop absolute paths.
3. Split with `RecursiveCharacterTextSplitter(chunk_size, chunk_overlap)`.
4. Delete existing points whose `metadata.filename == filename`.
5. Add the chunks.
6. Raise `EmptyDocumentError` if no text was extracted (for example, a scanned PDF).

`list_documents(client, collection) -> list[DocumentInfo(filename, chunks)]` scrolls the payloads and groups them by filename.

The upload endpoint sanitizes the file name (`pathlib.Path(name).name`, PDF extension required) before writing it to `UPLOAD_DIR`.

### 4.4 RAG chain (`rag/chain.py`)
The chain is built from three explicit steps:
1. **Rewrite**: only if `history` is non-empty. LLM call with the contextualize prompt, `StrOutputParser`, producing a standalone question.
2. **Retrieve**: `vector_store.similarity_search(standalone_question, k=RETRIEVAL_K)`.
3. **Answer**: the QA prompt (system prompt with `{context}`, then the history, then the question), streamed with `llm.astream(...)`.

Public interface:
```python
class RagChain:
    def __init__(self, llm: BaseChatModel, vector_store: VectorStore, k: int): ...
    async def retrieve(self, question: str, history: list[BaseMessage]) -> list[Document]: ...
    def stream_answer(self, question: str, history: list[BaseMessage], docs: list[Document]) -> AsyncIterator[str]: ...
```
The endpoint calls `retrieve` (to emit `sources` first) and then iterates `stream_answer`.

The QA system prompt keeps the existing Markdown guidance and adds: "Answer only from the provided context. If the context does not contain the answer, say so plainly."

The context is formatted as `[filename p.N]\n<chunk>` blocks so the model can attribute its answers.

### 4.5 Chat storage (`storage/chats.py`)
Mongo document in the `chats` collection:
```json
{
  "_id": "<uuid4 string>",
  "title": "<first user message, truncated to 60 chars; '' until then>",
  "created_at": "<UTC datetime>",
  "updated_at": "<UTC datetime>",
  "messages": [
    {"id": "<uuid4>", "role": "user" | "assistant", "content": "...",
     "sources": [{"filename": "a.pdf", "page": 3, "snippet": "..."}],
     "created_at": "<UTC datetime>"}
  ]
}
```
`ChatRepository` protocol: `create() -> Chat`, `list() -> list[ChatSummary]`, `get(id) -> Chat | None`, `append_messages(id, messages, title_if_empty)`, `delete(id) -> bool`.

There are two implementations: `MongoChatRepository` (pymongo `AsyncMongoClient`) and `InMemoryChatRepository` (used in tests). An index on `updated_at` keeps the list newest first.

### 4.6 HTTP API (all under `/api`)

| Method | Path | Request | Response |
|---|---|---|---|
| `GET` | `/health` | none | `{"status":"ok"}` |
| `POST` | `/documents` | multipart `files[]` | `{"results":[{"filename","pages","chunks"}], "errors":[{"filename","detail"}]}` |
| `GET` | `/documents` | none | `[{"filename","chunks"}]` |
| `POST` | `/chats` | none | `{"id", "title", "created_at", "updated_at", "messages": []}` |
| `GET` | `/chats` | none | `[{"id","title","updated_at"}]`, newest first |
| `GET` | `/chats/{id}` | none | full chat; 404 if missing |
| `DELETE` | `/chats/{id}` | none | 204; 404 if missing |
| `POST` | `/chats/{id}/messages` | JSON `{"content": "..."}` | `text/event-stream` |

**SSE event sequence** for `POST /chats/{id}/messages`:
```
event: sources   data: [{"filename","page","snippet"}]
event: token     data: {"text": "..."}          (repeated)
event: done      data: {"message_id": "..."}
```
On failure after the stream has started: `event: error  data: {"detail": "..."}`, then the stream closes.

Validation errors before streaming starts return normal HTTP errors:
- 404: unknown chat.
- 422: empty content.
- 409 `{"detail":"No documents indexed yet. Upload a PDF first."}`: the collection is empty.

**Persistence:** the user message and the assistant message (with its sources) are appended after the stream ends, including when the client disconnects mid-stream, in which case the partial text is saved. If zero tokens were produced, nothing is saved for the assistant and the user message is still saved.

Response header `X-Accel-Buffering: no` keeps nginx from buffering the stream.

### 4.7 Dependencies (pinned in `pyproject.toml`)
`fastapi`, `uvicorn[standard]`, `pydantic-settings`, `python-multipart`, `langchain-core`, `langchain-openai`, `langchain-qdrant`, `langchain-community` (for `PyPDFLoader`), `langchain-text-splitters`, `qdrant-client`, `pypdf`, `pymongo`, `sse-starlette`.

Dev dependencies: `pytest`, `pytest-asyncio`, `httpx`, `ruff`.

Python 3.12. Exact versions are resolved and locked when the project is created.

## 5. Frontend

### 5.1 Stack
React 19, Vite, TypeScript, Tailwind CSS 4, React Router, Zustand, react-markdown with remark-gfm, lucide-react and react-dropzone, all at current versions. `recharts` is removed. `vitest` is added for unit tests.

### 5.2 Layout
```
frontend/src/
  main.tsx, App.tsx, index.css
  types.ts               # Chat, ChatSummary, Message, Source, DocumentInfo
  api/
    client.ts            # listChats, getChat, createChat, deleteChat, listDocuments, uploadDocument
    sse.ts               # parseSSE(stream) -> AsyncIterable<{event, data}>; streamMessage(chatId, content, signal)
    sse.test.ts
  stores/chatStore.ts    # chat summaries: load, add, remove, touch (move to top, set title)
  hooks/useChatStream.ts # messages, isStreaming, error, send(content), stop()
  components/
    Sidebar.tsx, MessageList.tsx, MessageBubble.tsx, SourceList.tsx,
    Composer.tsx, UploadPanel.tsx, DocumentList.tsx
  pages/
    HomePage.tsx         # route "/"
    ChatPage.tsx         # route "/chat/:id"
```

### 5.3 Behavior
- **Home:**
  - Upload panel (drag-and-drop or click; each file is its own request, with a per-file status of uploading, then indexed or error) and the document list.
  - A composer, disabled with a hint until at least one document is indexed.
  - Sending creates a chat, adds it to the sidebar, navigates to `/chat/:id` and starts streaming the first message.
- **Chat page:**
  - Loads the chat and renders the messages. While streaming, the assistant bubble grows token by token with a cursor.
  - **Stop** aborts the request; the partial text is kept.
  - Each assistant message shows a sources row (chips reading `filename · p.N`, click to expand the snippet).
  - The composer's paperclip opens the upload panel in a modal.
- **Sidebar:**
  - New chat button and a list of chats (title, relative time) with the active chat highlighted.
  - Delete with a confirmation; deleting the active chat navigates to `/`.
  - Collapses on desktop and becomes a drawer below the `md` breakpoint.
- **Errors:** shown inline in the message list with a Retry button that resends the last user message.

### 5.4 Visual refresh
- Neutral palette with one accent color, following the system light or dark mode (Tailwind `dark:`).
- User messages are right-aligned bubbles; assistant answers are full-width with prose typography.
- Consistent spacing, focus rings, and empty and loading skeleton states.

### 5.5 API base
All calls use relative `/api/...` paths. Vite's dev server proxies `/api` to `http://localhost:8000`; in Docker, nginx proxies it to `backend:8000`.

## 6. Testing

| Layer | Tooling | What it covers |
|---|---|---|
| Ingestion | pytest, Qdrant `:memory:`, `DeterministicFakeEmbedding`, a generated sample PDF | chunk metadata (filename and page), re-upload replaces instead of duplicating, empty-PDF error, `list_documents` |
| Chain | pytest, fake chat model, Qdrant `:memory:` | rewrite skipped without history and used with it; retrieval returns the expected docs; the answer streams in tokens |
| API | pytest + httpx `AsyncClient`, `InMemoryChatRepository`, fakes | chat CRUD, 404s, delete; SSE order `sources`, `token`..., `done`; 409 when nothing is indexed; messages persisted after the stream; upload rejects non-PDF files |
| Mongo repo | pytest `-m integration` against the Compose Mongo | create, list order, append, delete |
| Frontend | vitest | the SSE parser handles events split across chunks, multiple events per chunk, and the `error` event |
| Frontend static | `tsc`, `eslint`, `vite build` | types, lint, build |
| End to end | `scripts/smoke.sh` against `docker compose up` | health, upload a sample PDF, create a chat, stream an answer, list chats, delete |

## 7. Delivery

Work happens on the `modernize` branch in the phases listed in `plan.md` (0 to 9). Each phase ends with its verification step and a commit, and work pauses for the user's review before the next phase. Old code is removed only after its replacement is verified (backend files in phase 5, frontend duplicates in phase 6).

## 8. Risks

| Risk | Mitigation |
|---|---|
| LangChain and Qdrant APIs drift | Exact versions are pinned with a lock file; adapters are kept thin (`rag/` only) |
| nginx buffers SSE | `proxy_buffering off` on `/api/` plus the `X-Accel-Buffering: no` header; verified in the phase 8 smoke test |
| Scanned PDFs with no text | `EmptyDocumentError` is surfaced per file in the upload results; OCR is out of scope |
| Changing the embedding model invalidates the index | Dimension check at startup with an actionable error |
