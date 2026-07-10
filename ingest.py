import os
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

load_dotenv()

def run_ingestion():
    print("⏳ Initializing Data Ingestion Pipeline...")
    
    # 1. Load documents from the docs folder
    if not os.path.exists("docs") or not os.listdir("docs"):
        raise FileNotFoundError("The 'docs/' folder is missing or empty. Please add your markdown files.")
        
    loader = DirectoryLoader("docs/", glob="**/*.md", loader_cls=TextLoader)
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
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    print("💾 Vectorizing chunks and saving to local ChromaDB instance...")
    db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory="./chroma_db"
    )
    print("✅ Ingestion complete! Local vector store initialized at './chroma_db'")

if __name__ == "__main__":
    run_ingestion()