import base64
import gc
import mimetypes
import os
import re
import shutil
import time
from pathlib import Path

import chromadb
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"
CHAT_UPLOADS_DIR = BASE_DIR / "tmp" / "chats"
CHAT_UPLOAD_TTL_SECONDS = int(os.getenv("CHAT_UPLOAD_TTL_SECONDS", "86400"))
ALLOWED_VENDORS = {"aws", "azure", "gcp", "nutanix", "vmware"}
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
    client = chromadb.HttpClient(
        host=os.getenv("CHROMA_HOST", "chroma-service"),
        port=int(os.getenv("CHROMA_PORT", 8000)),
    )
    return Chroma(client=client, embedding_function=embeddings)


def ingest_pdf(file_path: Path) -> int:
    documents = PyPDFLoader(str(file_path)).load()
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    ).split_documents(documents)
    chunk_count = len(chunks)
    if chunks:
        _vector_store().add_documents(chunks)
    del documents, chunks
    gc.collect()
    return chunk_count


def save_pdf(upload_file, filename: str) -> dict:
    safe_name = _safe_filename(filename)
    staging_path = DOCS_DIR / ".uploads" / safe_name
    staging_path.parent.mkdir(parents=True, exist_ok=True)
    with staging_path.open("wb") as destination:
        shutil.copyfileobj(upload_file.file, destination)

    try:
        first_page = PyPDFLoader(str(staging_path)).load()[0].page_content
        vendor = _vendor_for_pdf(safe_name, first_page)
        destination = DOCS_DIR / vendor / safe_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(staging_path, destination)
        chunks = ingest_pdf(destination)
        return {"filename": safe_name, "kind": "pdf", "vendor": vendor, "chunks": chunks}
    finally:
        staging_path.unlink(missing_ok=True)


def cleanup_expired_chat_uploads() -> None:
    if not CHAT_UPLOADS_DIR.exists():
        return
    cutoff = time.time() - CHAT_UPLOAD_TTL_SECONDS
    for chat_dir in CHAT_UPLOADS_DIR.iterdir():
        if chat_dir.is_dir() and chat_dir.stat().st_mtime < cutoff:
            shutil.rmtree(chat_dir, ignore_errors=True)


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


def image_data_url(path: str) -> str:
    file_path = Path(path)
    mime_type = mimetypes.guess_type(file_path.name)[0] or "image/png"
    encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def delete_chat_uploads(chat_id: str) -> None:
    safe_chat_id = re.sub(r"[^A-Za-z0-9_-]", "_", chat_id)[:100]
    shutil.rmtree(CHAT_UPLOADS_DIR / safe_chat_id, ignore_errors=True)