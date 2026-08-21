import os
import gc
import re
import chromadb
from pathlib import Path
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.embeddings import FakeEmbeddings

load_dotenv()

DOCS_BASE_URL = os.getenv("DOCS_BASE_URL", "http://192.168.122.1/docs/")

# nginx autoindex emits plain <a href="...">entry</a> rows for each file/dir.
_HREF_RE = re.compile(r'href="([^"]+)"')


def fetch_docs(base_url: str, dest_dir: Path) -> None:
    """
    Mirror an nginx-autoindex-served docs/ folder into dest_dir, recursing
    into subdirectories. Only .md and .pdf files are downloaded.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)

    resp = requests.get(base_url, timeout=30)
    resp.raise_for_status()

    hrefs = _HREF_RE.findall(resp.text)
    for href in hrefs:
        # Skip parent-directory links and anything that isn't a relative path
        if href in ("../", "/") or href.startswith(("http://", "https://")) and not href.startswith(base_url):
            continue

        full_url = urljoin(base_url, href)

        if href.endswith("/"):
            # Subdirectory listing — recurse into it
            fetch_docs(full_url, dest_dir / href.rstrip("/"))
            continue

        if not href.lower().endswith((".md", ".pdf")):
            continue

        file_resp = requests.get(full_url, timeout=60)
        file_resp.raise_for_status()
        target_path = dest_dir / href
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(file_resp.content)
        print(f"   ⬇️  Downloaded {href}")


def build_embeddings():
    try:
        from langchain_openai import OpenAIEmbeddings
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set")
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        embeddings.embed_query("warmup")
        return embeddings
    except Exception as exc:
        print(f"⚠️ Falling back to local embeddings: {exc}")
        return FakeEmbeddings(size=1536)


def run_ingestion():
    print("⏳ Initializing Data Ingestion Pipeline...")

    base_dir = Path(__file__).resolve().parent
    docs_dir = base_dir / "docs"
    persist_dir = base_dir / "chroma_db"

    # 1. Fetch documents from the control plane
    try:
        fetch_docs(DOCS_BASE_URL, docs_dir)
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not reach docs server at {DOCS_BASE_URL}: {exc}") from exc

    if not docs_dir.exists() or not any(docs_dir.iterdir()):
        raise FileNotFoundError("The 'docs/' folder is missing or empty after fetch.")

    # 2. Initialize ChromaDB and Embeddings once
    embeddings = build_embeddings()

    # Local ChromaDB configuration — matches graph.py / uploads.py so ingestion,
    # retrieval, and chat uploads all read/write the same on-disk store.
    chroma_client = chromadb.PersistentClient(
        path=str(persist_dir),
    )

    # --- Kubernetes Chroma server configuration (swap in for cluster deployment) ---
    # chroma_client = chromadb.HttpClient(
    #     host=os.getenv("CHROMA_HOST", "chroma-service"),
    #     port=int(os.getenv("CHROMA_PORT", 8000)),
    # )

    db = Chroma(
        client=chroma_client,
        embedding_function=embeddings,
    )

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
    )

    # 3. Process documents file-by-file (Memory-Safe Streaming)
    all_files = [f for f in docs_dir.rglob("*") if f.suffix in (".md", ".pdf")]
    print(f"📄 Found {len(all_files)} documentation files to ingest.")

    for idx, file_path in enumerate(all_files, 1):
        try:
            print(f"🔄 [{idx}/{len(all_files)}] Processing: {file_path.name}...")

            if file_path.suffix == ".md":
                loader = TextLoader(str(file_path))
            elif file_path.suffix == ".pdf":
                loader = PyPDFLoader(str(file_path))
            else:
                continue

            # Load, split, and ingest ONE file at a time
            file_docs = loader.load()
            file_chunks = text_splitter.split_documents(file_docs)

            if file_chunks:
                # Add to Chroma in sub-batches if the individual PDF is huge
                BATCH_SIZE = 1000
                for i in range(0, len(file_chunks), BATCH_SIZE):
                    sub_batch = file_chunks[i : i + BATCH_SIZE]
                    db.add_documents(documents=sub_batch)

                print(f"   ↳ Ingested {len(file_chunks)} chunks into ChromaDB.")

            # Garbage collect memory immediately after processing each file
            del file_docs, file_chunks
            gc.collect()

        except Exception as err:
            print(f"⚠️ Error processing {file_path.name}: {err}")

    print(f"✅ Ingestion complete! Local vector store initialized at '{persist_dir}'")


if __name__ == "__main__":
    run_ingestion()