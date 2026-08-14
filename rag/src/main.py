"""
ALPHAWISE RAG Servisi.
Finans metodolojisi + 6 dis trading-skill reposunu ChromaDB'ye indeksler,
MAA'nin sorgulayabilecegi bir /query endpoint'i sunar.
Embedding: ChromaDB'nin varsayilan modeli (sentence-transformers/all-MiniLM-L6-v2,
hafif, ~80MB, Contabo'nun 32GB RAM'inde sorunsuz calisir).
"""
import os
import glob
import chromadb
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ALPHAWISE - RAG Service")

CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))
DATA_ROOT = os.getenv("DATA_ROOT", "/data")
COLLECTION_NAME = "alphawise_knowledge"

_client = None
_collection = None


def get_chroma_client():
    global _client
    if _client is None:
        _client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    return _client


def get_collection():
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(name=COLLECTION_NAME)
    return _collection


def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 200):
    """Basit sabit-boyutlu, ortusen (overlap) parcalama."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
        if start < 0 or end >= len(text):
            break
    return [c for c in chunks if c.strip()]


@app.get("/health")
def health():
    try:
        col = get_collection()
        count = col.count()
        return {"service": "RAG", "status": "ok", "indexed_chunks": count}
    except Exception as e:
        return {"service": "RAG", "status": "error", "detail": str(e)}


@app.post("/index")
def index_knowledge_base():
    """
    DATA_ROOT altindaki tum .md dosyalarini tarar, parcalar, ChromaDB'ye yazar.
    Idempotent degildir - tekrar cagrilirsa mukerrer kayit olusabilir,
    bu yuzden once collection'i temizler.
    """
    client = get_chroma_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    global _collection
    _collection = client.get_or_create_collection(name=COLLECTION_NAME)

    md_files = glob.glob(f"{DATA_ROOT}/**/*.md", recursive=True)
    total_chunks = 0
    indexed_files = 0
    errors = []

    for filepath in md_files:
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            if not text.strip():
                continue
            chunks = chunk_text(text)
            if not chunks:
                continue

            rel_path = filepath.replace(DATA_ROOT, "")
            ids = [f"{rel_path}::chunk{i}" for i in range(len(chunks))]
            metadatas = [{"source": rel_path, "chunk_index": i} for i in range(len(chunks))]

            _collection.add(documents=chunks, ids=ids, metadatas=metadatas)
            total_chunks += len(chunks)
            indexed_files += 1
        except Exception as e:
            errors.append({"file": filepath, "error": str(e)})

    return {
        "indexed_files": indexed_files,
        "total_chunks": total_chunks,
        "total_md_files_found": len(md_files),
        "errors": errors[:10],
    }


@app.get("/query")
def query_knowledge_base(q: str, n_results: int = 5):
    """Verilen sorguya en yakin n_results parcayi doner."""
    col = get_collection()
    results = col.query(query_texts=[q], n_results=n_results)
    hits = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    for doc, meta, dist in zip(docs, metas, distances):
        hits.append({"content": doc, "source": meta.get("source"), "distance": dist})
    return {"query": q, "results": hits}
