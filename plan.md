# PDF RAG Chat Modernization: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the app into `backend/` + `frontend/`, replace Chroma with Qdrant, add SSE strea ming and a light UI refresh, and run everything with one `docker compose up`.

**Architecture:** A FastAPI backend (`backend/app/{api,rag,storage}`) with a typed `Settings` and a `Services` container injected through `app.state`, so tests swap in an in-memory Qdrant, fake LLM and embeddings, and an in-memory chat repo. A React frontend talks only to relative `/api/...`; nginx serves it and proxies `/api` to the backend. Compose runs `frontend`, `backend`, `qdrant` and `mongo`.

**Tech Stack:**
- **Backend:** Python 3.12, uv, FastAPI, pydantic-settings, LangChain (`langchain-core`, `-openai`, `-qdrant`, `-community`, `-text-splitters`), qdrant-client, pymongo (async), pytest.
- **Frontend:** React 19, Vite, TypeScript, Tailwind 4, Zustand, React Router, vitest.
- **Runtime:** Docker Compose.

**Spec:** [docs/superpowers/specs/2026-10-28-modernize-design.md](docs/superpowers/specs/2026-10-28-modernize-design.md)

## Progress

| Phase | Tasks | Status |
|---|---|---|
| 0. Setup: branch, spec, plan | — | ✅ |
| 1. Backend skeleton | 1 | ✅ |
| 2. Chat storage | 2, 3 | ✅ |
| 3. Ingestion into Qdrant | 4, 5 | ✅ |
| 4. RAG chain and streaming | 6, 7 | ✅ |
| 5. Compose (backend services) and old-backend removal | 8 | ✅ |
| 6. Frontend cleanup and API layer | 9, 10 | ✅ |
| 7. Frontend features and refresh | 11, 12 | 🟡 Task 11 done; Task 12 code done, live check pending |
| 8. Frontend container, full stack | 13 | ⬜ |
| 9. Docs | 14 | ⬜ |

> **Resume here (2026-10-28):** Task 12 is implemented and committed, plus two bugs found by the browser checklist: (1) a first question sent from Home was wiped by a history reload under React StrictMode — fixed in `useChatStream` with a regression test; (2) the rewrite step answered long requests ("write an essay…") instead of rephrasing them (17 s to first token) — rewrite is now capped at 128 tokens, the prompt is stricter, and over-long rewrites fall back to the original question. **Remaining for Task 12:** rebuild the backend (`docker compose up -d --build backend`), confirm a follow-up essay request now streams within ~2–3 s, re-run the browser checklist (Tasks 11 + 12 items), then mark Phase 7 ✅. Then Phases 8–9.

**Checkpoint rule:** at the end of each phase, run its verification, commit, update this table, and **stop for the user's review** before starting the next phase.

## Global Constraints

- All work is on branch `modernize`. Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Python 3.12. Dependencies are managed with `uv` in `backend/pyproject.toml`; `backend/uv.lock` is committed.
- All HTTP routes live under the `/api` prefix.
- Settings defaults (spec §4.1): `openai_model="gpt-4o-mini"`, `embedding_model="text-embedding-3-small"`, `qdrant_url="http://localhost:6333"`, `qdrant_collection="documents"`, `mongo_uri="mongodb://localhost:27017"`, `mongo_db="pdf_rag"`, `upload_dir="./data/uploads"`, `chunk_size=1000`, `chunk_overlap=200`, `retrieval_k=4`, `history_window=10`, `max_upload_mb=10`. `openai_api_key` is required.
- **Plan-level additions to the spec:**
  - `embedding_dim: int = 1536`, so the collection can be created without a probe API call.
  - SSE is written by hand with Starlette's `StreamingResponse` instead of `sse-starlette`, avoiding that library's event-loop quirks in tests.
- The Mongo collection name is `chats`. Roles are `"user"` and `"assistant"`.
- Chat title = first user message truncated to **60** characters. Source snippet = first **200** characters of the chunk.
- Chunk metadata is exactly `{"filename": str, "page": int}`, with pages counted from 1.
- The frontend uses only relative `/api/...` URLs. No `localhost` strings in `frontend/src`.
- Only port **8080** is published to the host in the final compose file.
- PDF size limit: **10 MB per file** (`max_upload_mb`), enforced by the backend and mirrored in the dropzone; nginx allows 50 MB per request so multi-file uploads work.

## Review Focus

1. **Large PDFs through nginx.** nginx's default `client_max_body_size` (1m) returns 413. Expected: an upload up to 10 MB reaches the backend; a file over 10 MB is reported in `errors` as `"File exceeds 10 MB limit"`, not a 413 or 500. Pinned in Task 5 and by the smoke script in Task 13.
2. **A corrupt or non-text file named `.pdf`.** Expected: it appears in `errors` while other files in the same request are still ingested, with no 500. Pinned in Task 5.
3. **File names with path parts, spaces, Unicode, or `.PDF`** (for example `../../evil.pdf`, `Q3 Report ü.PDF`). Expected: saved as the base name inside `UPLOAD_DIR` and accepted case-insensitively. Pinned in Task 5.
4. **The LLM fails mid-stream** (rate limit, bad key). Expected: an `error` event, with the user message and the partial assistant text persisted, and the chat still usable afterwards. Pinned in Task 7.
5. **Switching chats or leaving the page during a stream.** Expected: the in-flight request is aborted, and tokens never appear in the other chat. Pinned in Task 11.

---

## Phase 1: Backend skeleton

### Task 1: Backend project, settings, app factory, health, Dockerfile

**Files:**
- Create: `backend/pyproject.toml`, `backend/uv.lock`, `backend/app/__init__.py`, `backend/app/config.py`, `backend/app/services.py`, `backend/app/deps.py`, `backend/app/main.py`, `backend/app/api/__init__.py`, `backend/app/api/health.py`, `backend/Dockerfile`, `backend/.dockerignore`
- Test: `backend/tests/conftest.py`, `backend/tests/test_health.py`, `backend/tests/test_config.py`

**Interfaces:**
- Produces:
  - `Settings(BaseSettings)` with the Global Constraints fields. It loads `.env` from the CWD, and its env names are the uppercase field names.
  - `get_settings() -> Settings` (cached with `lru_cache`).
  - `@dataclass Services: chat_repo: ChatRepository; qdrant: QdrantClient; vector_store: VectorStore; rag_chain: RagChain`. Fields are typed `Any` until Tasks 2, 4 and 6 tighten them.
  - `async def build_services(settings) -> Services` and `async def close_services(services) -> None` in `app/services.py`. Both are stubs that raise `NotImplementedError` until Task 8.
  - `create_app(settings: Settings | None = None, services: Services | None = None) -> FastAPI`. If `services` is given, it is set on `app.state.services` immediately and the lifespan does nothing. Otherwise the lifespan calls `build_services` on startup and `close_services` on shutdown.
  - In `app/deps.py`: `get_services(request) -> Services`, `get_app_settings(request) -> Settings` (from `app.state.settings`).
  - Run command: `uvicorn app.main:create_app --factory`.

- [x] **Step 1: Initialize the uv project**

Run, in `backend/`:
- `uv init --app --python 3.12 --name pdf-rag-backend`
- `uv add fastapi "uvicorn[standard]" pydantic-settings python-multipart langchain-core langchain-openai langchain-qdrant langchain-community langchain-text-splitters qdrant-client pypdf pymongo`
- `uv add --dev pytest pytest-asyncio httpx ruff reportlab`

Then delete the generated `main.py`/`hello.py`. In `pyproject.toml`, set `[tool.pytest.ini_options]`:
- `asyncio_mode = "auto"`
- `markers = ["integration: needs running Mongo"]`
- `addopts = "-m 'not integration'"`

Expected: `uv.lock` exists.

- [x] **Step 2: Write failing tests**

```python
# tests/conftest.py
@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(openai_api_key="test", upload_dir=str(tmp_path / "uploads"), embedding_dim=32)

# tests/test_health.py
async def test_health_returns_ok(settings):
    app = create_app(settings, services=Services(chat_repo=None, qdrant=None, vector_store=None, rag_chain=None))
    async with AsyncClient(transport=ASGITransport(app), base_url="http://t") as c:
        r = await c.get("/api/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}

# tests/test_config.py
def test_missing_openai_key_fails(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)

def test_defaults():
    s = Settings(openai_api_key="x", _env_file=None)
    assert (s.openai_model, s.embedding_model, s.retrieval_k, s.history_window) == ("gpt-4o-mini", "text-embedding-3-small", 4, 10)
```

- [x] **Step 3: Run the tests to verify they fail**

Run: `cd backend && uv run pytest -v`. Expected: ImportError / FAIL.

- [x] **Step 4: Implement `config.py`, `services.py`, `deps.py`, `api/health.py` and `main.py`**

`create_app` stores `settings` on `app.state.settings` and includes the health router under `/api`. No CORS middleware.

- [x] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest -v && uv run ruff check .`. Expected: all pass, no lint errors.

- [x] **Step 6: Dockerfile with `runtime` and `test` targets**

- **`runtime`:**
  - Based on `python:3.12-slim`, with `COPY --from=ghcr.io/astral-sh/uv:<pinned tag> /uv /bin/uv`.
  - Runs `uv sync --frozen --no-dev`, copies `app/`, and sets `CMD ["uv","run","--no-sync","uvicorn","app.main:create_app","--factory","--host","0.0.0.0","--port","8000"]`.
- **`test`:** extends `runtime` with `uv sync --frozen` (dev deps), copies `tests/`, and sets `CMD ["uv","run","pytest"]`.
- **`.dockerignore`:** excludes `.venv`, `__pycache__` and `data/`.

Run: `docker build --target runtime -t pdf-rag-backend backend`. Expected: the build succeeds.

- [x] **Step 7: Commit**: `git add backend && git commit -m "Add backend skeleton: settings, app factory, health"`. Then update Progress and stop for review.

---

## Phase 2: Chat storage

### Task 2: Chat models and repositories

**Files:**
- Create: `backend/app/storage/__init__.py`, `backend/app/storage/models.py`, `backend/app/storage/chats.py`
- Test: `backend/tests/test_chat_repo.py`, `backend/tests/test_mongo_repo.py`

**Interfaces:**
- Produces, in `storage/models.py` (pydantic v2):
  - `Source(filename: str, page: int, snippet: str)`
  - `Message(id: str, role: Literal["user","assistant"], content: str, sources: list[Source] = [], created_at: datetime)`
  - `ChatSummary(id: str, title: str, updated_at: datetime)`
  - `Chat(id: str, title: str, created_at: datetime, updated_at: datetime, messages: list[Message])`
  - `new_message(role, content, sources=()) -> Message`, which fills in a uuid4 `id` and a UTC `created_at`.
- Produces, in `storage/chats.py`:
  - `class ChatRepository(Protocol)` with:
    - `async create() -> Chat`
    - `async list() -> list[ChatSummary]` (by `updated_at`, newest first)
    - `async get(chat_id) -> Chat | None`
    - `async append_messages(chat_id, messages: list[Message], title_if_empty: str) -> bool`
    - `async delete(chat_id) -> bool`
  - `InMemoryChatRepository()`.
  - `MongoChatRepository(db: AsyncDatabase)`, with `async ensure_indexes()` (index on `updated_at`). Documents use `_id` = chat id; the repository maps `_id` to and from `id`.

`append_messages` sets the title to `title_if_empty[:60]` only when the current title is `""`, appends with `$push`/`$each` (atomic), sets `updated_at`, and returns `False` if the chat is missing.

- [x] **Step 1: Write failing contract tests** in `test_chat_repo.py`, parametrized over a `repo` fixture (in-memory):

```python
async def test_create_then_get(repo):
    chat = await repo.create()
    got = await repo.get(chat.id)
    assert got.id == chat.id and got.title == "" and got.messages == []

async def test_append_sets_title_once_and_truncates(repo):
    chat = await repo.create()
    await repo.append_messages(chat.id, [new_message("user", "q1")], title_if_empty="x" * 80)
    await repo.append_messages(chat.id, [new_message("user", "q2")], title_if_empty="other")
    got = await repo.get(chat.id)
    assert got.title == "x" * 60 and [m.content for m in got.messages] == ["q1", "q2"]

async def test_list_newest_first(repo):
    a = await repo.create(); b = await repo.create()
    await repo.append_messages(a.id, [new_message("user", "hi")], "hi")
    assert [c.id for c in await repo.list()][:2] == [a.id, b.id]

async def test_delete_and_missing(repo):
    chat = await repo.create()
    assert await repo.delete(chat.id) is True
    assert await repo.get(chat.id) is None
    assert await repo.delete(chat.id) is False
    assert await repo.append_messages("nope", [], "") is False
```

In `test_mongo_repo.py`, mark the module `pytestmark = pytest.mark.integration`. It reuses the same four tests (import and re-parametrize) against `MongoChatRepository` on a throwaway DB named `pdf_rag_test_<uuid>`, which is dropped afterwards. `MONGO_URI` comes from the environment.

- [x] **Step 2: Run the tests to verify they fail.** Run: `uv run pytest tests/test_chat_repo.py -v`. Expected: ImportError.
- [x] **Step 3: Implement `models.py` and `chats.py`.**
- [x] **Step 4: Run the tests to verify they pass.** Run: `uv run pytest -v`. Expected: PASS. The Mongo tests are deselected for now and run in Task 8.
- [x] **Step 5: Commit**: `git commit -m "Add chat models and repositories"`.

### Task 3: Chat endpoints

**Files:**
- Create: `backend/app/api/chats.py`
- Modify: `backend/app/main.py` (include the router)
- Test: `backend/tests/test_api_chats.py`; add `services` and `client` fixtures to `conftest.py`

**Interfaces:**
- Consumes: `ChatRepository`, `Chat`, `ChatSummary` (Task 2); `get_services` (Task 1).
- Produces these routes:
  - `POST /api/chats` → 201 `Chat`
  - `GET /api/chats` → `list[ChatSummary]`
  - `GET /api/chats/{chat_id}` → `Chat` / 404
  - `DELETE /api/chats/{chat_id}` → 204 / 404
- Produces the conftest fixture `services` (`Services` with `InMemoryChatRepository()`; the other fields are set in Tasks 4 and 6) and `client` (an httpx `AsyncClient` over `create_app(settings, services)`).

- [x] **Step 1: Write failing tests**

```python
async def test_create_list_get_delete(client):
    created = (await client.post("/api/chats")).json()
    assert created["messages"] == [] and created["title"] == ""
    assert [c["id"] for c in (await client.get("/api/chats")).json()] == [created["id"]]
    assert (await client.get(f"/api/chats/{created['id']}")).status_code == 200
    assert (await client.delete(f"/api/chats/{created['id']}")).status_code == 204
    assert (await client.get(f"/api/chats/{created['id']}")).status_code == 404

async def test_delete_missing_is_404(client):
    assert (await client.delete("/api/chats/missing")).status_code == 404

async def test_list_omits_messages(client):
    await client.post("/api/chats")
    assert set((await client.get("/api/chats")).json()[0]) == {"id", "title", "updated_at"}
```

- [x] **Step 2: Run, verify FAIL.** Run: `uv run pytest tests/test_api_chats.py -v`.
- [x] **Step 3: Implement `api/chats.py`** and register it in `create_app`.
- [x] **Step 4: Run, verify PASS.** Run: `uv run pytest -v && uv run ruff check .`.
- [x] **Step 5: Commit**: `git commit -m "Add chat CRUD endpoints"`. Then update Progress and stop for review.

---

## Phase 3: Ingestion into Qdrant

### Task 4: Vector store setup and PDF ingestion

**Files:**
- Create: `backend/app/rag/__init__.py`, `backend/app/rag/vectorstore.py`, `backend/app/rag/ingest.py`
- Test: `backend/tests/test_vectorstore.py`, `backend/tests/test_ingest.py`; add fixtures to `conftest.py`

**Interfaces:**
- Produces, in `rag/vectorstore.py`:
  - `class CollectionDimensionMismatch(RuntimeError)`
  - `ensure_collection(client: QdrantClient, name: str, dim: int) -> None`: creates the collection with cosine distance plus a keyword payload index on `metadata.filename`. On a size mismatch it raises with the message `f"Collection '{name}' has vector size {actual}, expected {dim}. Delete the collection (or the qdrant_data volume) and re-upload your PDFs."`
  - `make_vector_store(client, name, embeddings: Embeddings) -> QdrantVectorStore`
  - `collection_is_empty(client, name) -> bool`
- Produces, in `rag/ingest.py`:
  - `class EmptyDocumentError(ValueError)`
  - `@dataclass IngestResult(filename: str, pages: int, chunks: int)`
  - `@dataclass DocumentInfo(filename: str, chunks: int)`
  - `ingest_pdf(path: Path, filename: str, vector_store: QdrantVectorStore, client: QdrantClient, settings: Settings) -> IngestResult`
  - `list_documents(client, collection) -> list[DocumentInfo]`, sorted by filename.
- Produces these conftest fixtures:
  - `qdrant` (`QdrantClient(":memory:")` with `ensure_collection(..., dim=32)`)
  - `embeddings` (`DeterministicFakeEmbedding(size=32)`)
  - `vector_store`
  - `make_pdf(pages: list[str], name="doc.pdf") -> Path`, which uses reportlab and writes one page per string; an empty string produces a blank page.
  - `services` now includes `qdrant` and `vector_store`.

`ingest_pdf` steps, in order:
1. `PyPDFLoader(path).load()`
2. Replace the metadata with `{"filename": filename, "page": doc.metadata["page"] + 1}`.
3. Split with `RecursiveCharacterTextSplitter(settings.chunk_size, settings.chunk_overlap)`.
4. Drop whitespace-only chunks. If none remain, raise `EmptyDocumentError`.
5. `client.delete(collection, Filter(must=[FieldCondition(key="metadata.filename", match=MatchValue(value=filename))]))`
6. `vector_store.add_documents(chunks)`

- [x] **Step 1: Write failing tests**

```python
# test_vectorstore.py
def test_ensure_collection_idempotent_and_detects_mismatch():
    c = QdrantClient(":memory:")
    ensure_collection(c, "docs", 32); ensure_collection(c, "docs", 32)
    with pytest.raises(CollectionDimensionMismatch):
        ensure_collection(c, "docs", 64)

# test_ingest.py
def test_ingest_sets_filename_and_page(make_pdf, vector_store, qdrant, settings):
    r = ingest_pdf(make_pdf(["alpha text", "beta text"]), "doc.pdf", vector_store, qdrant, settings)
    assert (r.filename, r.pages) == ("doc.pdf", 2) and r.chunks >= 2
    hits = vector_store.similarity_search("beta text", k=10)
    assert {(h.metadata["filename"], h.metadata["page"]) for h in hits} >= {("doc.pdf", 1), ("doc.pdf", 2)}

def test_reupload_replaces_not_duplicates(make_pdf, vector_store, qdrant, settings):
    p = make_pdf(["alpha", "beta"])
    first = ingest_pdf(p, "doc.pdf", vector_store, qdrant, settings)
    ingest_pdf(p, "doc.pdf", vector_store, qdrant, settings)
    assert list_documents(qdrant, settings.qdrant_collection) == [DocumentInfo("doc.pdf", first.chunks)]

def test_blank_pdf_raises(make_pdf, vector_store, qdrant, settings):
    with pytest.raises(EmptyDocumentError):
        ingest_pdf(make_pdf([""]), "blank.pdf", vector_store, qdrant, settings)

def test_collection_is_empty(qdrant, settings, make_pdf, vector_store):
    assert collection_is_empty(qdrant, settings.qdrant_collection)
    ingest_pdf(make_pdf(["x"]), "a.pdf", vector_store, qdrant, settings)
    assert not collection_is_empty(qdrant, settings.qdrant_collection)
```

- [x] **Step 2: Run, verify FAIL.** Run: `uv run pytest tests/test_vectorstore.py tests/test_ingest.py -v`.
- [x] **Step 3: Implement `vectorstore.py` and `ingest.py`.**
- [x] **Step 4: Run, verify PASS.** Run: `uv run pytest -v`.
- [x] **Step 5: Commit**: `git commit -m "Add Qdrant collection setup and PDF ingestion"`.

### Task 5: Document endpoints

**Files:**
- Create: `backend/app/api/documents.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_api_documents.py`

**Interfaces:**
- Consumes: `ingest_pdf`, `list_documents`, `EmptyDocumentError`, `IngestResult`, `DocumentInfo` (Task 4).
- Produces:
  - `POST /api/documents` (multipart field `files`, one or more) → 200 `{"results":[{"filename","pages","chunks"}], "errors":[{"filename","detail"}]}`. Returns 400 if none of the files has a `.pdf` extension (case-insensitive).
  - `GET /api/documents` → `[{"filename","chunks"}]`.

Per file:
- `safe = Path(upload.filename).name`; skip it with an error if it doesn't end in `.pdf` (case-insensitive).
- Stream the upload to disk in 1 MB chunks; if it exceeds `settings.max_upload_mb * 1024 * 1024` bytes, delete the partial file and add the error `f"File exceeds {settings.max_upload_mb} MB limit"`.
- Write it to `Path(settings.upload_dir) / safe`, creating the directory if needed.
- Call `ingest_pdf` in a thread (`run_in_threadpool`).
- Any exception from ingestion (`EmptyDocumentError`, pypdf errors) goes into `errors` with `str(e)` or `"No extractable text"`.

- [x] **Step 1: Write failing tests**

```python
async def test_upload_and_list(client, make_pdf):
    p = make_pdf(["hello world"])
    r = await client.post("/api/documents", files=[("files", ("doc.pdf", p.read_bytes(), "application/pdf"))])
    assert r.status_code == 200 and r.json()["results"][0]["filename"] == "doc.pdf" and r.json()["errors"] == []
    assert (await client.get("/api/documents")).json()[0]["filename"] == "doc.pdf"

async def test_non_pdf_only_is_400(client):
    r = await client.post("/api/documents", files=[("files", ("notes.txt", b"hi", "text/plain"))])
    assert r.status_code == 400

async def test_corrupt_pdf_reported_others_ingested(client, make_pdf):   # Review Focus 2
    good = make_pdf(["fine"])
    r = await client.post("/api/documents", files=[
        ("files", ("bad.pdf", b"not a pdf at all", "application/pdf")),
        ("files", ("good.pdf", good.read_bytes(), "application/pdf"))])
    body = r.json()
    assert r.status_code == 200
    assert [e["filename"] for e in body["errors"]] == ["bad.pdf"]
    assert [x["filename"] for x in body["results"]] == ["good.pdf"]

async def test_oversized_file_rejected(client, make_pdf, settings):   # Review Focus 1
    big = b"%PDF-1.4
" + b"0" * (settings.max_upload_mb * 1024 * 1024)
    good = make_pdf(["fine"])
    r = await client.post("/api/documents", files=[
        ("files", ("big.pdf", big, "application/pdf")),
        ("files", ("good.pdf", good.read_bytes(), "application/pdf"))])
    assert r.json()["errors"] == [{"filename": "big.pdf", "detail": "File exceeds 10 MB limit"}]
    assert [x["filename"] for x in r.json()["results"]] == ["good.pdf"]
    assert not (Path(settings.upload_dir) / "big.pdf").exists()

async def test_filename_sanitized_and_case_insensitive(client, make_pdf, settings):   # Review Focus 3
    p = make_pdf(["x"])
    r = await client.post("/api/documents", files=[("files", ("../../Q3 Report ü.PDF", p.read_bytes(), "application/pdf"))])
    assert r.json()["results"][0]["filename"] == "Q3 Report ü.PDF"
    assert (Path(settings.upload_dir) / "Q3 Report ü.PDF").exists()
    assert not (Path(settings.upload_dir).parent.parent / "Q3 Report ü.PDF").exists()
```

- [x] **Step 2: Run, verify FAIL.**
- [x] **Step 3: Implement `api/documents.py`** and register it.
- [x] **Step 4: Run, verify PASS.** Run: `uv run pytest -v && uv run ruff check .`.
- [x] **Step 5: Commit**: `git commit -m "Add document upload and listing endpoints"`. Then update Progress and stop for review.

---

## Phase 4: RAG chain and streaming

### Task 6: RAG chain

**Files:**
- Create: `backend/app/rag/prompts.py`, `backend/app/rag/chain.py`
- Test: `backend/tests/test_chain.py`; add a fake LLM fixture to `conftest.py`

**Interfaces:**
- Consumes: `QdrantVectorStore` (Task 4).
- Produces, in `rag/prompts.py`: `CONTEXTUALIZE_PROMPT` and `QA_PROMPT` (`ChatPromptTemplate`s with `MessagesPlaceholder("chat_history")` and `("human", "{input}")`). `QA_PROMPT`'s system text is the old Markdown guidance plus `"Answer only from the provided context. If the context does not contain the answer, say so plainly."` and `Context:\n{context}`.
- Produces, in `rag/chain.py`:
  - `format_context(docs: list[Document]) -> str`: blocks of `[{filename} p.{page}]\n{page_content}` joined by blank lines.
  - `to_lc_history(messages: list[Message]) -> list[BaseMessage]`: maps `user` to `HumanMessage` and `assistant` to `AIMessage`.
  - `class RagChain(llm: BaseChatModel, vector_store: VectorStore, k: int)` with:
    - `async retrieve(question: str, history: list[BaseMessage]) -> list[Document]`: rewrites the question only when `history` is non-empty, then calls `similarity_search(q, k)`.
    - `stream_answer(question, history, docs) -> AsyncIterator[str]`: yields non-empty text chunks from `(QA_PROMPT | llm).astream(...)`.
  - `services.rag_chain` is set to a `RagChain` in the conftest `services` fixture.
- Produces the conftest fixture `RecordingFakeLLM`: a `GenericFakeChatModel` subclass that records each prompt's message list in `self.calls`. The fixture `fake_llm(*responses: str)` builds one over `iter([AIMessage(r) for r in responses])`.

- [x] **Step 1: Write failing tests**

```python
async def test_no_history_skips_rewrite(fake_llm, vector_store, make_pdf, qdrant, settings):
    ingest_pdf(make_pdf(["cats purr"]), "c.pdf", vector_store, qdrant, settings)
    llm = fake_llm("unused")
    docs = await RagChain(llm, vector_store, k=4).retrieve("cats?", [])
    assert llm.calls == [] and docs[0].metadata["filename"] == "c.pdf"

async def test_history_triggers_rewrite(fake_llm, vector_store, make_pdf, qdrant, settings):
    ingest_pdf(make_pdf(["cats purr"]), "c.pdf", vector_store, qdrant, settings)
    llm = fake_llm("do cats purr?")
    await RagChain(llm, vector_store, k=4).retrieve("do they?", [HumanMessage("cats"), AIMessage("ok")])
    assert len(llm.calls) == 1

async def test_stream_answer_yields_tokens_with_context(fake_llm, vector_store):
    llm = fake_llm("Cats purr loudly")
    docs = [Document("cats purr", metadata={"filename": "c.pdf", "page": 2})]
    tokens = [t async for t in RagChain(llm, vector_store, k=4).stream_answer("q", [], docs)]
    assert len(tokens) > 1 and "".join(tokens) == "Cats purr loudly"
    assert "[c.pdf p.2]" in llm.calls[0][0].content
```

- [x] **Step 2: Run, verify FAIL.**
- [x] **Step 3: Implement `prompts.py` and `chain.py`.**
- [x] **Step 4: Run, verify PASS.**
- [x] **Step 5: Commit**: `git commit -m "Add history-aware RAG chain with streaming"`.

### Task 7: Streaming messages endpoint

**Files:**
- Create: `backend/app/api/messages.py`, `backend/app/api/sse.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_api_messages.py`; add the `parse_sse(text) -> list[tuple[str, Any]]` helper to `conftest.py`

**Interfaces:**
- Consumes: `ChatRepository`, `new_message`, `Source` (Task 2); `collection_is_empty` (Task 4); `RagChain` and `to_lc_history` (Task 6).
- Produces:
  - `format_sse(event: str, data: Any) -> str`, which returns `f"event: {event}\ndata: {json.dumps(data)}\n\n"`.
  - `POST /api/chats/{chat_id}/messages` with body `{"content": str}` (stripped, `min_length=1`, else 422):
    - unknown chat → 404
    - empty collection → 409 `{"detail":"No documents indexed yet. Upload a PDF first."}`
    - otherwise → `StreamingResponse(media_type="text/event-stream", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})`

Generator flow:
1. `history = to_lc_history(chat.messages[-settings.history_window:])`.
2. `docs = await rag_chain.retrieve(...)`; yield `sources` (`[Source(filename, page, page_content[:200])]`).
3. Yield a `token` event for each chunk while accumulating `answer`.
4. Yield `done` with `{"message_id": assistant_id}`.
5. On `Exception`, yield `error` with `{"detail": str(e)}`.
6. In `finally`, `await asyncio.shield(repo.append_messages(chat_id, [user_msg] + ([assistant_msg] if answer else []), title_if_empty=content))`. `assistant_id` is generated up front so `done` and the saved message agree.

- [x] **Step 1: Write failing tests** (the fixture lets tests set `services.rag_chain.llm`, or pass in a new `RagChain` with a chosen fake)

```python
async def test_stream_order_and_persistence(client, services, upload_sample):
    chat = (await client.post("/api/chats")).json()
    r = await client.post(f"/api/chats/{chat['id']}/messages", json={"content": "what purrs?"})
    events = parse_sse(r.text)
    assert r.headers["content-type"].startswith("text/event-stream")
    assert events[0][0] == "sources" and events[0][1][0]["filename"] == "c.pdf"
    assert {e for e, _ in events[1:-1]} == {"token"} and events[-1][0] == "done"
    saved = (await client.get(f"/api/chats/{chat['id']}")).json()
    assert [m["role"] for m in saved["messages"]] == ["user", "assistant"]
    assert saved["messages"][1]["id"] == events[-1][1]["message_id"]
    assert saved["title"] == "what purrs?" and saved["messages"][1]["sources"][0]["page"] == 1

async def test_409_when_no_documents(client):
    chat = (await client.post("/api/chats")).json()
    r = await client.post(f"/api/chats/{chat['id']}/messages", json={"content": "hi"})
    assert r.status_code == 409 and "Upload a PDF first" in r.json()["detail"]

async def test_404_and_422(client, upload_sample):
    assert (await client.post("/api/chats/nope/messages", json={"content": "hi"})).status_code == 404
    chat = (await client.post("/api/chats")).json()
    assert (await client.post(f"/api/chats/{chat['id']}/messages", json={"content": "   "})).status_code == 422

async def test_llm_failure_mid_stream(client, services, upload_sample):   # Review Focus 4
    services.rag_chain = RagChain(FailingAfterFirstTokenLLM(), services.vector_store, k=4)
    chat = (await client.post("/api/chats")).json()
    events = parse_sse((await client.post(f"/api/chats/{chat['id']}/messages", json={"content": "q"})).text)
    assert events[-1][0] == "error"
    saved = (await client.get(f"/api/chats/{chat['id']}")).json()
    assert [m["role"] for m in saved["messages"]] == ["user", "assistant"]
    assert saved["messages"][1]["content"] != ""
```

The test helpers live in conftest:
- `upload_sample` ingests `make_pdf(["cats purr"])` as `c.pdf`.
- `FailingAfterFirstTokenLLM` streams one chunk, then raises `RuntimeError("rate limited")`.

- [x] **Step 2: Run, verify FAIL.**
- [x] **Step 3: Implement `sse.py` and `messages.py`.**
- [x] **Step 4: Run, verify PASS.** Run: `uv run pytest -v && uv run ruff check .`.
- [x] **Step 5: Commit**: `git commit -m "Add SSE streaming messages endpoint"`. Then update Progress and stop for review.

---

## Phase 5: Compose (backend services) and old-backend removal

### Task 8: Real service wiring, compose, smoke test, delete the old backend

**Files:**
- Modify: `backend/app/services.py` (real `build_services` / `close_services`)
- Create: `docker-compose.yml`, `.env.example`, `scripts/smoke.sh`, `scripts/fixtures/sample.pdf`, `scripts/make_fixture.py`
- Delete: `server.py`, `main.py`, `ragchain.py`, `conversational_rag_chain.py`, `ingestion.py`, `ingest.py`, `db.py`, `mongo_db.py`, `requirements.txt`, root `pyproject.toml`, `.python-version`
- Modify: `.gitignore` (add `data/`, `backend/.venv/`, `node_modules/`; remove the Chroma entries)

**Interfaces:**
- Consumes: everything from Tasks 2 to 7.
- `build_services(settings)`:
  1. `QdrantClient(url=settings.qdrant_url)`, then `ensure_collection(client, settings.qdrant_collection, settings.embedding_dim)`.
  2. `OpenAIEmbeddings(model=settings.embedding_model, api_key=...)`, then `make_vector_store`.
  3. `AsyncMongoClient(settings.mongo_uri)[settings.mongo_db]`, then `MongoChatRepository` with `await ensure_indexes()`.
  4. `ChatOpenAI(model=settings.openai_model, api_key=..., temperature=0.2, streaming=True)`, then `RagChain(llm, vector_store, settings.retrieval_k)`.

  `close_services` closes the Mongo and Qdrant clients.

- [x] **Step 1: Implement `build_services` / `close_services`.** Run: `uv run pytest -v`. Expected: still PASS (the tests inject services).

- [x] **Step 2: Write `docker-compose.yml`**
  - **`qdrant`:** `qdrant/qdrant:<pinned tag>`, volume `qdrant_data:/qdrant/storage`, healthcheck `bash -c ':> /dev/tcp/127.0.0.1/6333'`.
  - **`mongo`:** `mongo:7`, volume `mongo_data:/data/db`, healthcheck `mongosh --quiet --eval "db.adminCommand('ping')"`.
  - **`backend`:**
    - build `./backend`, target `runtime`; `env_file: .env`.
    - environment `QDRANT_URL=http://qdrant:6333`, `MONGO_URI=mongodb://mongo:27017`, `UPLOAD_DIR=/data/uploads`.
    - volume `uploads:/data/uploads`; `depends_on` qdrant and mongo `service_healthy`.
    - healthcheck `python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/api/health')"`.
    - **temporary** `ports: ["127.0.0.1:8000:8000"]`, removed in Task 13.
  - **`backend-tests`:** `profiles: ["test"]`, build target `test`, env `MONGO_URI=mongodb://mongo:27017`, depends on mongo healthy, command `uv run pytest -m integration -v`.

  `.env.example` contains `OPENAI_API_KEY=` and the optional overrides from spec §4.1, commented out.

- [x] **Step 3: Write the fixture and the smoke script**
  - `scripts/make_fixture.py` (run once with `uv run --with reportlab python scripts/make_fixture.py`) writes `scripts/fixtures/sample.pdf`, a 2-page PDF about a fictional "Zebra Protocol". Commit the PDF.
  - `scripts/smoke.sh [BASE_URL=http://localhost:8000]` uses `set -euo pipefail`, curl and grep:
    1. `GET /api/health` returns ok.
    2. Upload `sample.pdf` and expect `"chunks"` in the response.
    3. `head -c 2000000 /dev/urandom > "$tmp/corrupt.pdf"`, upload it, and expect HTTP 200 with `corrupt.pdf` listed under `errors` (2 MB passes the size limit but isn't a valid PDF). Then `head -c 11000000 /dev/urandom > "$tmp/big.pdf"`, upload it, and expect HTTP 200 with `File exceeds 10 MB limit`.
    4. `POST /api/chats`, then capture the id.
    5. `curl -N` the messages endpoint with "What is the Zebra Protocol?" and expect `event: sources`, `event: token` and `event: done`.
    6. `GET /api/chats` contains the id.
    7. `DELETE` returns 204.
    8. Print `SMOKE OK`.

- [x] **Step 4: Bring the stack up and verify**

Run:
- `docker compose up -d --build qdrant mongo backend`
- `docker compose run --rm backend-tests`
- `bash scripts/smoke.sh`

Expected: the integration tests pass (the Mongo contract tests from Task 2), and `SMOKE OK` prints. This needs a real `OPENAI_API_KEY` in `.env`.

- [x] **Step 5: Delete the old root Python files** listed above and update `.gitignore`. Run: `git status`. Expected: only the listed deletions, with no new backend breakage (`cd backend && uv run pytest`).

- [x] **Step 6: Commit**: `git commit -m "Wire real services, add compose and smoke test, remove old backend"`. Then update Progress and stop for review.

---

## Phase 6: Frontend cleanup and API layer

### Task 9: Consolidate the frontend, types, API client, dev proxy

**Files:**
- Delete:
  - Root: `src/`, `public/`, `index.html`, `package.json`, `package-lock.json`, `vite.config.ts`, `tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json`, `eslint.config.js`
  - In `frontend/src/components/`: `AskQuestion`, `Charts`, `Question`, `StreamQuestion`, `Upload`, `UploadAndQueryStream`, `UploadAndQuestion`, `UploadOnly`, `UploadQuery`, `UploadQuestion`, `ChatHistory`, `LangQuestion`, `LangUpload`, `types.ts`
  - In `frontend/src/`: `hooks/useLLMStream.ts`, `hooks/useChats.tsx`, `pages/ChatPage.tsx`, `pages/Home.tsx`, `App.css`, `assets/react.svg`
- Create: `frontend/src/types.ts`, `frontend/src/api/client.ts`, a temporary placeholder `frontend/src/pages/HomePage.tsx`
- Modify: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/src/App.tsx`, `frontend/src/stores/chatStore.ts`, `frontend/src/components/Sidebar.tsx` (switch to the new store and types only)

**Interfaces:**
- Produces, in `types.ts` (mirroring the backend):
  - `Source {filename; page; snippet}`
  - `Message {id; role: "user"|"assistant"; content; sources: Source[]; created_at}`
  - `ChatSummary {id; title; updated_at}`
  - `Chat extends ChatSummary {created_at; messages: Message[]}`
  - `DocumentInfo {filename; chunks}`
  - `IngestResponse {results: {filename; pages; chunks}[]; errors: {filename; detail}[]}`
- Produces, in `api/client.ts`:
  - `class ApiError extends Error {status: number}`
  - `listChats(): Promise<ChatSummary[]>`
  - `getChat(id): Promise<Chat>`
  - `createChat(): Promise<Chat>`
  - `deleteChat(id): Promise<void>`
  - `listDocuments(): Promise<DocumentInfo[]>`
  - `uploadDocument(file: File): Promise<IngestResponse>`

  All of these use relative `/api/...` and throw `ApiError` with the backend's `detail` on non-2xx responses.
- Produces, in `stores/chatStore.ts`: `useChatStore` with `{chats: ChatSummary[]; loadChats(); addChat(c: ChatSummary); removeChat(id); touchChat(id, title?: string)}`. `touchChat` moves the chat to the top, sets `updated_at` to now, and sets the title if it was empty.

- [x] **Step 1: Delete the files listed above.**
- [x] **Step 2: Update dependencies.** Run, in `frontend/`:
  - `npm uninstall recharts`
  - `npm install react@latest react-dom@latest react-router-dom@latest zustand@latest react-markdown@latest remark-gfm@latest lucide-react@latest react-dropzone@latest tailwindcss@latest @tailwindcss/vite@latest`
  - `npm install -D vitest @testing-library/react jsdom @tailwindcss/typography`
  - Add the `"test": "vitest run"` script.
- [x] **Step 3: Set up Vite.** In `vite.config.ts`, set `server.proxy = {"/api": "http://localhost:8000"}` and `test: {environment: "jsdom"}`.
- [x] **Step 4: Write `types.ts`, `client.ts` and the store.** Point `App.tsx` routes at `HomePage` (a placeholder) and `/chat/:id` (a placeholder that renders the id).
- [x] **Step 5: Verify.** Run: `npm run build && npm run lint`, then `grep -r "localhost" frontend/src`. Expected: the build and lint pass, and grep finds nothing.
- [x] **Step 6: Commit**: `git commit -m "Consolidate frontend, add typed API client and dev proxy"`.

### Task 10: SSE parser and `streamMessage`

**Files:**
- Create: `frontend/src/api/sse.ts`
- Test: `frontend/src/api/sse.test.ts`

**Interfaces:**
- Produces:
  - `type SSEEvent = {event: string; data: unknown}`
  - `parseSSE(stream: ReadableStream<Uint8Array>): AsyncGenerator<SSEEvent>`: buffers text, splits on a blank line (`\n\n`), and reads the `event:` and `data:` lines (`data` is JSON-parsed).
  - `type StreamEvent = {type:"sources"; sources: Source[]} | {type:"token"; text: string} | {type:"done"; messageId: string} | {type:"error"; detail: string}`
  - `streamMessage(chatId: string, content: string, signal: AbortSignal): AsyncGenerator<StreamEvent>`: `fetch` POST JSON, throws `ApiError` on non-2xx, then maps `parseSSE` events to `StreamEvent`.

- [x] **Step 1: Write failing tests**

```ts
const streamOf = (...chunks: string[]) => new ReadableStream({ start(c) { chunks.forEach(s => c.enqueue(new TextEncoder().encode(s))); c.close(); } });
const collect = async (s: ReadableStream) => { const out = []; for await (const e of parseSSE(s)) out.push(e); return out; };

test("event split across chunks", async () => {
  expect(await collect(streamOf('event: tok', 'en\ndata: {"text":"Hi"}', '\n\n'))).toEqual([{ event: "token", data: { text: "Hi" } }]);
});
test("multiple events in one chunk", async () => {
  const s = streamOf('event: token\ndata: {"text":"a"}\n\nevent: done\ndata: {"message_id":"m1"}\n\n');
  expect((await collect(s)).map(e => e.event)).toEqual(["token", "done"]);
});
test("streamMessage maps error event and throws ApiError on 409", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(new Response(streamOf('event: error\ndata: {"detail":"boom"}\n\n'), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Upload a PDF first." }), { status: 409 })));
  const evs = []; for await (const e of streamMessage("c1", "q", new AbortController().signal)) evs.push(e);
  expect(evs).toEqual([{ type: "error", detail: "boom" }]);
  await expect(streamMessage("c1", "q", new AbortController().signal).next()).rejects.toMatchObject({ status: 409 });
});
```

- [x] **Step 2: Run, verify FAIL.** Run: `npm test`.
- [x] **Step 3: Implement `sse.ts`.**
- [x] **Step 4: Run, verify PASS.** Run: `npm test && npm run build`.
- [x] **Step 5: Commit**: `git commit -m "Add SSE parser and streamMessage"`. Then update Progress and stop for review.

---

## Phase 7: Frontend features and refresh

### Task 11: Chat experience (sidebar, messages, streaming, sources, composer)

**Files:**
- Create: `frontend/src/hooks/useChatStream.ts`, `frontend/src/hooks/useChatStream.test.tsx`, `frontend/src/components/{MessageList,MessageBubble,SourceList,Composer}.tsx`, `frontend/src/pages/ChatPage.tsx`
- Modify: `frontend/src/components/Sidebar.tsx`, `frontend/src/App.tsx`, `frontend/src/index.css` (Tailwind typography plugin, `dark:` follows the system setting)

**Interfaces:**
- Consumes: `api/client.ts`, `chatStore` (Task 9); `streamMessage` (Task 10).
- Produces: `useChatStream(chatId: string): {messages: Message[]; isStreaming: boolean; error: string | null; send(content: string): Promise<void>; stop(): void; retry(): void}`.
  - It loads the chat with `getChat` when `chatId` changes.
  - `send` adds an optimistic user message and an empty assistant message, then:
    - `sources` sets the assistant message's sources
    - each `token` appends to its content
    - `done` sets its id
    - `error` (or a thrown error) sets `error`
  - On success it calls `chatStore.touchChat(chatId, content)`.
  - `stop` and a `chatId` change or unmount abort the controller. Tokens from an aborted stream are ignored, guarded by a per-request token.
  - `retry` resends the last user message without adding it to the list again.
- `ChatPage`:
  - Reads `location.state?.initialMessage`. If present, it calls `send` once (guarded by a `useRef` against StrictMode's double effect), then `navigate(location.pathname, {replace: true, state: null})`.
- Components:
  - **`MessageBubble`:** user messages are right-aligned bubbles; assistant messages are full-width `prose dark:prose-invert` with ReactMarkdown and GFM, plus a blinking cursor while streaming.
  - **`SourceList`:** chips reading `filename · p.N`; clicking one toggles its snippet.
  - **`Composer`:** an auto-growing textarea (Enter sends, Shift+Enter adds a newline), a Stop button while streaming, a `disabled` prop with a hint, and an `onAttach` callback (the paperclip).
  - **`Sidebar`:**
    - New chat button, chats with relative time, the active chat highlighted.
    - Trash button with a `window.confirm`; it calls `deleteChat`, then `removeChat`, and navigates to `/` if the chat was active.
    - Collapses on desktop and becomes a drawer below `md` (hamburger in the top bar).

- [x] **Step 1: Write the failing hook test** (Review Focus 5)

```tsx
test("switching chatId aborts the in-flight stream and drops its tokens", async () => {
  // getChat mocked to return empty chats; streamMessage mocked to an async generator that awaits a deferred
  // before yielding {type:"token", text:"LATE"} and records the AbortSignal it received.
  const { result, rerender } = renderHook(({ id }) => useChatStream(id), { initialProps: { id: "a" } });
  act(() => { void result.current.send("q"); });
  rerender({ id: "b" });
  releaseDeferred();
  await waitFor(() => expect(recordedSignal.aborted).toBe(true));
  expect(result.current.messages.some(m => m.content.includes("LATE"))).toBe(false);
});
```

- [x] **Step 2: Run, verify FAIL.** Run: `npm test`.
- [x] **Step 3: Implement `useChatStream`.** Run: `npm test`. Expected: PASS.
- [x] **Step 4: Implement the components, `ChatPage` and the Sidebar refresh.**
- [x] **Step 5: Verify**

Run: `npm run build && npm run lint && npm test`. Then, with the Task 8 compose backend running, run `npm run dev` and go through this checklist:
- Open an existing chat and see its history.
- Ask a question: tokens stream in, and sources appear and expand.
- Stop mid-answer: the partial text stays, and it is still there after a reload.
- Switch chats mid-stream: no tokens leak into the other chat.
- Delete the active chat: you land on `/`.
- At phone width, the drawer opens and closes.
- Dark mode follows the OS setting.

- [x] **Step 6: Commit**: `git commit -m "Add streaming chat UI with sources and sidebar refresh"`.

### Task 12: Home page, uploads, document list

**Files:**
- Create: `frontend/src/stores/documentStore.ts`, `frontend/src/components/UploadPanel.tsx`, `frontend/src/components/DocumentList.tsx`
- Modify: `frontend/src/pages/HomePage.tsx`, `frontend/src/pages/ChatPage.tsx` (paperclip opens the upload modal)

**Interfaces:**
- Consumes: `uploadDocument`, `listDocuments`, `createChat` (Task 9); `Composer` (Task 11); `chatStore.addChat`.
- Produces: `useDocumentStore` with `{documents: DocumentInfo[]; loaded: boolean; loadDocuments()}`.
- Components:
  - **`UploadPanel`:** react-dropzone, PDFs only, `maxSize: 10 * 1024 * 1024` (oversized files show "File exceeds 10 MB limit" without uploading). Each dropped file gets a row with the status `uploading` → `indexed (N chunks)` or `error: detail`. Each file is uploaded in its own request. It calls `loadDocuments()` after every response.
  - **`DocumentList`:** filename plus chunk count, with an empty state.
- `HomePage`:
  - Shows a hero/empty state, `UploadPanel`, `DocumentList` and a `Composer`. The composer is disabled with the hint "Upload a PDF to start" while `documents.length === 0`.
  - On send: `createChat()`, then `addChat`, then `navigate(`/chat/${id}`, {state: {initialMessage}})`.
- `ChatPage`: the paperclip opens `UploadPanel` in a modal (closed with Esc or a backdrop click).

- [x] **Step 1: Implement the store, `UploadPanel`, `DocumentList` and `HomePage`,** plus the modal on `ChatPage`.
- [ ] **Step 2: Verify**

Run: `npm run build && npm run lint && npm test`. Then, with `npm run dev` against the compose backend:
- With no documents, the composer is disabled.
- Dropping a PDF over 10 MB shows the size error immediately.
- Drop two PDFs and one `.txt`: the `.txt` is rejected by the dropzone, and the PDFs show per-file progress, then "indexed".
- Ask from home: you land on the chat page and the answer streams.
- The paperclip modal uploads from inside a chat.

- [ ] **Step 3: Commit**: `git commit -m "Add home page with uploads and document list"`. Then update Progress and stop for review.

---

## Phase 8: Frontend container, full stack

### Task 13: Frontend Dockerfile, nginx, four-service compose

**Files:**
- Create: `frontend/Dockerfile`, `frontend/nginx.conf`, `frontend/.dockerignore`
- Modify: `docker-compose.yml`

**Interfaces:**
- `frontend/Dockerfile`: stage `node:22-alpine` runs `npm ci && npm run build`, then stage `nginx:<pinned>-alpine` copies `dist/` to `/usr/share/nginx/html` and `nginx.conf` to `/etc/nginx/conf.d/default.conf`.
- `nginx.conf`:
  - `listen 80`; `client_max_body_size 50m`.
  - `location /api/`: `proxy_pass http://backend:8000`, `proxy_http_version 1.1`, `proxy_buffering off`, `proxy_read_timeout 300s`.
  - `location /`: `try_files $uri /index.html`.
- `docker-compose.yml`:
  - Add a `frontend` service (`ports: ["8080:80"]`, `depends_on: backend: service_healthy`).
  - **Remove** the temporary backend `ports`.

- [ ] **Step 1: Write the Dockerfile, `nginx.conf` and `.dockerignore`;** update compose.
- [ ] **Step 2: Verify the full stack**

Run:
- `docker compose down && docker compose up -d --build`
- `bash scripts/smoke.sh http://localhost:8080`
- `docker compose ps`

Expected:
- `SMOKE OK`. This includes the 2 MB and 11 MB uploads returning 200 with per-file errors, not 413 (Review Focus 1), and SSE events arriving through nginx.
- Only `frontend` publishes a port (`0.0.0.0:8080->80`).

Then open `http://localhost:8080`, run the Task 11 and 12 checklists once more, and confirm that answers stream token by token rather than arriving in one block, which would mean buffering.

- [ ] **Step 3: Check persistence.** Run: `docker compose restart`, then reload the page. Expected: chats and documents survive.
- [ ] **Step 4: Commit**: `git commit -m "Add frontend container and nginx proxy; full compose stack"`. Then update Progress and stop for review.

---

## Phase 9: Docs

### Task 14: README and final cleanup

**Files:**
- Modify: `README.md`, `.env.example`, `frontend/README.md` (delete it or replace it with a short dev note)

- [ ] **Step 1: Rewrite `README.md`:**
  - overview
  - architecture diagram (text) of the four services
  - quick start (`cp .env.example .env`, set the key, `docker compose up -d --build`, open `http://localhost:8080`)
  - local development without Docker (backend `uv run uvicorn app.main:create_app --factory --reload` against `docker compose up qdrant mongo` with temporary ports; frontend `npm run dev`)
  - configuration table (spec §4.1 plus `EMBEDDING_DIM`)
  - API table (spec §4.6)
  - testing commands (`uv run pytest`, `docker compose run --rm backend-tests`, `npm test`, `scripts/smoke.sh`)
  - project layout
- [ ] **Step 2: Final check.**
  - Run: `git ls-files | grep -E '^(src|public)/|chroma|requirements'`. Expected: no output.
  - Run: `cd backend && uv run pytest && uv run ruff check .`, then `cd ../frontend && npm test && npm run lint && npm run build`. Expected: all green.
- [ ] **Step 3: Commit**: `git commit -m "Rewrite README for the Docker/Qdrant stack"`. Then mark every phase ✅ in Progress and hand off to `superpowers:finishing-a-development-branch`.
