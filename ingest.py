import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.embeddings import FakeEmbeddings

load_dotenv()


def build_embeddings():
    """Create embeddings with OpenAI when available, otherwise fall back locally."""
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

    # 1. Load documents from the docs folder
    # The docs folder can include AWS, GCP, Azure, Nutanix, VMware and other infrastructure documentation.
    if not docs_dir.exists() or not any(docs_dir.iterdir()):
        raise FileNotFoundError("The 'docs/' folder is missing or empty. Please add your markdown files.")

    loader = DirectoryLoader(str(docs_dir), glob="**/*.md", loader_cls=TextLoader)
    documents = loader.load()
    print(f"📄 Loaded {len(documents)} raw document source(s).")

    # 2. Chunk text with optimal structural overlap
    # We use a 400-token chunk size to ensure networking syntax (like tables/bullet points) stays intact
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=50,
        length_function=len,
        is_separator_regex=False,
    )
    chunks = text_splitter.split_documents(documents)
    print(f"✂️ Split documents into {len(chunks)} distinct vector chunks.")

    # 3. Embed chunks and save to a local database directory
    embeddings = build_embeddings()

    print("💾 Vectorizing chunks and saving to local ChromaDB instance...")
    persist_dir.mkdir(parents=True, exist_ok=True)
    db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(persist_dir),
    )
    print(f"✅ Ingestion complete! Local vector store initialized at '{persist_dir}'")


if __name__ == "__main__":
    run_ingestion()