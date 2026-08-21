import base64
import gc
import json
import mimetypes
import os
import re
import shutil
import time
import uuid
from pathlib import Path

import chromadb
from pypdf import PdfReader
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"
CHAT_UPLOADS_DIR = BASE_DIR / "tmp" / "chats"
CHAT_UPLOAD_TTL_SECONDS = int(os.getenv("CHAT_UPLOAD_TTL_SECONDS", "86400"))
ALLOWED_VENDORS = {
    "aws", "azure", "gcp", "cisco", "nutanix", "vmware", "arista",
    "hp", "lenovo", "dell", "other",
}
IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


def _safe_filename(filename: str) -> str:
    name = Path(filename or "upload").name
    return re.sub(r"[^A-Za-z0-9._-]", "_", name) or "upload"


def _vendor_for_pdf(filename: str, text: str) -> str:
    haystack = f"{filename} {text}".lower()
    for vendor in ALLOWED_VENDORS:
        if re.search(rf"\b{re.escape(vendor)}\b", haystack):
            return vendor
    return "other"


def _vector_store() -> Chroma:
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    # Kubernetes Chroma server configuration:
    #client = chromadb.HttpClient(
    #     host=os.getenv("CHROMA_HOST", "chroma-service"),
    #     port=int(os.getenv("CHROMA_PORT", 8000)),
    #)

    # Local ChromaDB configuration for uploads made from this repository.
    client = chromadb.PersistentClient(
        path=str(BASE_DIR / "chroma_db"),
    )
    return Chroma(client=client, embedding_function=embeddings)


def ingest_pdf(file_path: Path, chat_id: str) -> int:
    documents = PyPDFLoader(str(file_path)).load()
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    ).split_documents(documents)
    chunk_count = len(chunks)
    if chunks:
        chunk_ids = [str(uuid.uuid4()) for _ in chunks]
        for chunk in chunks:
            chunk.metadata["chat_id"] = chat_id
        _vector_store().add_documents(chunks, ids=chunk_ids)
        manifest_path = CHAT_UPLOADS_DIR / chat_id / ".vector_ids.json"
        existing_ids = []
        if manifest_path.is_file():
            try:
                existing_ids = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                existing_ids = []
        manifest_path.write_text(json.dumps(existing_ids + chunk_ids), encoding="utf-8")
    del documents, chunks
    gc.collect()
    return chunk_count


def save_pdf(upload_file, filename: str, chat_id: str, ingest: bool = True) -> dict:
    contents = upload_file.file.read()
    return save_pdf_contents(contents, filename, chat_id, ingest=ingest)


def save_pdf_contents(contents: bytes, filename: str, chat_id: str, ingest: bool = True) -> dict:
    cleanup_expired_chat_uploads()
    safe_chat_id = re.sub(r"[^A-Za-z0-9_-]", "_", chat_id)[:100] or "anonymous"
    safe_name = _safe_filename(filename)
    staging_path = CHAT_UPLOADS_DIR / safe_chat_id / "docs" / "other" / safe_name
    staging_path.parent.mkdir(parents=True, exist_ok=True)
    staging_path.write_bytes(contents)

    destination = staging_path
    try:
        reader = PdfReader(str(staging_path))
        first_page = reader.pages[0].extract_text() if reader.pages else ""
        vendor = _vendor_for_pdf(safe_name, first_page)
        destination = CHAT_UPLOADS_DIR / safe_chat_id / "docs" / vendor / safe_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination != staging_path:
            shutil.move(staging_path, destination)
        chunks = ingest_pdf(destination, safe_chat_id) if ingest else None
        return {
            "filename": safe_name,
            "kind": "pdf",
            "vendor": vendor,
            "chunks": chunks,
            "temporary": True,
            "processing": not ingest,
        }
    except Exception:
        staging_path.unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
        raise


def cleanup_expired_chat_uploads() -> None:
    if not CHAT_UPLOADS_DIR.exists():
        return
    cutoff = time.time() - CHAT_UPLOAD_TTL_SECONDS
    for chat_dir in CHAT_UPLOADS_DIR.iterdir():
        if chat_dir.is_dir() and chat_dir.stat().st_mtime < cutoff:
            delete_chat_uploads(chat_dir.name)


def save_image(upload_file, filename: str, chat_id: str) -> dict:
    cleanup_expired_chat_uploads()
    safe_chat_id = re.sub(r"[^A-Za-z0-9_-]", "_", chat_id)[:100] or "anonymous"
    safe_name = _safe_filename(filename)
    chat_dir = CHAT_UPLOADS_DIR / safe_chat_id
    chat_dir.mkdir(parents=True, exist_ok=True)
    destination = chat_dir / safe_name
    with destination.open("wb") as output:
        shutil.copyfileobj(upload_file.file, output)
    return {"filename": safe_name, "kind": "image"}


def chat_image_path(chat_id: str, filename: str) -> Path:
    safe_chat_id = re.sub(r"[^A-Za-z0-9_-]", "_", chat_id)[:100] or "anonymous"
    safe_name = _safe_filename(filename)
    chat_dir = (CHAT_UPLOADS_DIR / safe_chat_id).resolve()
    path = (chat_dir / safe_name).resolve()
    if path.parent != chat_dir:
        raise ValueError("Invalid chat attachment path")
    return path


def chat_pdf_path(chat_id: str, vendor: str, filename: str) -> Path:
    safe_chat_id = re.sub(r"[^A-Za-z0-9_-]", "_", chat_id)[:100] or "anonymous"
    safe_vendor = vendor if vendor in ALLOWED_VENDORS else "other"
    safe_name = _safe_filename(filename)
    return CHAT_UPLOADS_DIR / safe_chat_id / "docs" / safe_vendor / safe_name


def image_data_url(path: str) -> str:
    file_path = Path(path)
    mime_type = mimetypes.guess_type(file_path.name)[0] or "image/png"
    encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def delete_chat_uploads(chat_id: str) -> None:
    safe_chat_id = re.sub(r"[^A-Za-z0-9_-]", "_", chat_id)[:100]
    chat_dir = CHAT_UPLOADS_DIR / safe_chat_id
    manifest_path = chat_dir / ".vector_ids.json"
    if manifest_path.is_file():
        try:
            vector_ids = json.loads(manifest_path.read_text(encoding="utf-8"))
            if vector_ids:
                _vector_store().delete(ids=vector_ids)
        except Exception:
            pass
    shutil.rmtree(chat_dir, ignore_errors=True)