import os
from dataclasses import asdict
from pathlib import Path, PurePosixPath

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.config import Settings
from app.deps import get_app_settings, get_services
from app.rag.ingest import EmptyDocumentError, ingest_pdf, list_documents
from app.services import Services

router = APIRouter(prefix="/documents", tags=["documents"])

READ_CHUNK = 1024 * 1024


class IngestedFile(BaseModel):
    filename: str
    pages: int
    chunks: int


class FileError(BaseModel):
    filename: str
    detail: str


class IngestResponse(BaseModel):
    results: list[IngestedFile]
    errors: list[FileError]


class DocumentOut(BaseModel):
    filename: str
    chunks: int


class FileTooLarge(Exception):
    pass


def safe_filename(raw: str | None) -> str:
    """Strip any directory parts (POSIX or Windows style) from a client-supplied name."""
    return PurePosixPath((raw or "").replace("\\", "/")).name


async def save_upload(upload: UploadFile, dest: Path, max_bytes: int) -> None:
    """Stream to a temp file and move it into place, so a rejected upload never
    clobbers a previously stored file of the same name."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    size = 0
    try:
        with tmp.open("wb") as out:
            while chunk := await upload.read(READ_CHUNK):
                size += len(chunk)
                if size > max_bytes:
                    raise FileTooLarge
                out.write(chunk)
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)


@router.post("")
async def upload_documents(
    files: list[UploadFile] = File(...),
    services: Services = Depends(get_services),
    settings: Settings = Depends(get_app_settings),
) -> IngestResponse:
    named = [(f, safe_filename(f.filename)) for f in files]
    if not any(name.lower().endswith(".pdf") for _, name in named):
        raise HTTPException(status_code=400, detail="No PDF files uploaded.")

    results: list[IngestedFile] = []
    errors: list[FileError] = []
    max_bytes = settings.max_upload_mb * 1024 * 1024
    for upload, name in named:
        if not name.lower().endswith(".pdf"):
            errors.append(FileError(filename=name, detail="Only PDF files are supported"))
            continue
        dest = Path(settings.upload_dir) / name
        try:
            await save_upload(upload, dest, max_bytes)
        except FileTooLarge:
            errors.append(
                FileError(filename=name, detail=f"File exceeds {settings.max_upload_mb} MB limit")
            )
            continue
        try:
            result = await run_in_threadpool(
                ingest_pdf, dest, name, services.vector_store, services.qdrant, settings
            )
        except EmptyDocumentError as e:
            errors.append(FileError(filename=name, detail=str(e)))
        except Exception as e:  # corrupt or unreadable PDF
            errors.append(FileError(filename=name, detail=f"Could not read PDF: {e}"))
        else:
            results.append(IngestedFile(**asdict(result)))
    return IngestResponse(results=results, errors=errors)


@router.get("")
def get_documents(
    services: Services = Depends(get_services),
    settings: Settings = Depends(get_app_settings),
) -> list[DocumentOut]:
    docs = list_documents(services.qdrant, settings.qdrant_collection)
    return [DocumentOut(filename=d.filename, chunks=d.chunks) for d in docs]
