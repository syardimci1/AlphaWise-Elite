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

# ===== SINYAL KOLEKSIYONLARI (23.08.2026, Faz 5/C3) =====
# Mevcut alphawise_knowledge koleksiyonuna DOKUNULMAZ; bunlar AYRI
# koleksiyonlardir. Amac: MAA'nin RAG sorgusu yalnizca statik metodoloji
# belgelerini degil, CANLI piyasa gozlemlerini de gorebilsin.
SINYAL_KOLEKSIYONLARI = {
    "finra_darkpool": os.getenv("FINRA_URL", "http://finra-darkpool:8000"),
    "sec_edgar_13f": os.getenv("SEC13F_URL", "http://sec-edgar-13f:8000"),
    "news_monitor": os.getenv("NEWS_URL", "http://news-monitor:8000"),
}
_sinyal_kol = {}


def get_sinyal_collection(ad: str):
    if ad not in _sinyal_kol:
        _sinyal_kol[ad] = get_chroma_client().get_or_create_collection(name=ad)
    return _sinyal_kol[ad]

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


# ===== C3: CANLI SINYAL CIKTILARINI CHROMADB'YE INDEKSLE =====
import httpx as _httpx
from datetime import datetime as _dt


def _belge(baslik: str, govde: str) -> str:
    return f"{baslik}\n{govde}".strip()


@app.post("/index-sinyaller")
def index_sinyaller(tickers: str = "AAPL,MSFT,NVDA"):
    """finra-darkpool / sec-edgar-13f / news-monitor ciktilarini AYRI
    koleksiyonlara indeksler. alphawise_knowledge koleksiyonuna DOKUNMAZ.
    """
    liste = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    damga = _dt.utcnow().isoformat(timespec="seconds")
    sonuc = {}

    # --- 1) FINRA dark pool (haftalik ATS + gunluk Reg SHO) ---
    kol = get_sinyal_collection("finra_darkpool")
    d_belge, d_id, d_meta = [], [], []
    for t in liste:
        for yol, etiket in ((f"/darkpool/{t}", "haftalik_ats"),
                            (f"/regsho/{t}?gun=5", "gunluk_regsho")):
            try:
                r = _httpx.get(SINYAL_KOLEKSIYONLARI["finra_darkpool"] + yol, timeout=120.0)
                if r.status_code != 200:
                    continue
                d_belge.append(_belge(f"[FINRA {etiket}] {t}", str(r.json())[:4000]))
                d_id.append(f"finra::{etiket}::{t}::{damga}")
                d_meta.append({"kaynak": "finra-darkpool", "tur": etiket,
                               "ticker": t, "cekilme": damga})
            except Exception:
                continue
    if d_belge:
        kol.add(documents=d_belge, ids=d_id, metadatas=d_meta)
    sonuc["finra_darkpool"] = {"eklenen": len(d_belge), "toplam": kol.count()}

    # --- 2) SEC EDGAR 13F ---
    kol = get_sinyal_collection("sec_edgar_13f")
    s_belge, s_id, s_meta = [], [], []
    for t in liste:
        try:
            r = _httpx.get(SINYAL_KOLEKSIYONLARI["sec_edgar_13f"] + f"/holders/{t}?top=8",
                           timeout=180.0)
            if r.status_code != 200:
                continue
            s_belge.append(_belge(f"[SEC 13F kurumsal pozisyon] {t}", str(r.json())[:4000]))
            s_id.append(f"sec13f::{t}::{damga}")
            s_meta.append({"kaynak": "sec-edgar-13f", "ticker": t, "cekilme": damga})
        except Exception:
            continue
    if s_belge:
        kol.add(documents=s_belge, ids=s_id, metadatas=s_meta)
    sonuc["sec_edgar_13f"] = {"eklenen": len(s_belge), "toplam": kol.count()}

    # --- 3) news-monitor uyarilari ---
    kol = get_sinyal_collection("news_monitor")
    n_belge, n_id, n_meta = [], [], []
    try:
        r = _httpx.get(SINYAL_KOLEKSIYONLARI["news_monitor"] + "/alerts", timeout=60.0)
        if r.status_code == 200:
            for i, a in enumerate(r.json().get("alerts", [])):
                bas = a.get("headline") or ""
                if not bas:
                    continue
                duygu = a.get("sentiment") or {}
                n_belge.append(_belge(
                    f"[Haber] {a.get('ticker','?')} — {bas}",
                    f"kaynak={a.get('source')} duygu={duygu.get('label')} "
                    f"skor={duygu.get('score')} zaman={a.get('logged_at')}"))
                n_id.append(f"news::{a.get('ticker','?')}::{a.get('news_time', i)}::{i}")
                n_meta.append({"kaynak": "news-monitor", "ticker": a.get("ticker", "?"),
                               "duygu": str(duygu.get("label")), "cekilme": damga})
    except Exception:
        pass
    if n_belge:
        kol.add(documents=n_belge, ids=n_id, metadatas=n_meta)
    sonuc["news_monitor"] = {"eklenen": len(n_belge), "toplam": kol.count()}

    return {"indekslenen": sonuc, "tickers": liste, "zaman": damga}


@app.get("/query-sinyaller")
def query_sinyaller(q: str, n_results: int = 3, koleksiyon: str = None):
    """Sinyal koleksiyonlarinda arama. koleksiyon bos ise UCUNDE de arar."""
    adlar = ([koleksiyon] if koleksiyon else list(SINYAL_KOLEKSIYONLARI))
    cikti = {}
    for ad in adlar:
        try:
            kol = get_sinyal_collection(ad)
            if kol.count() == 0:
                cikti[ad] = {"uyari": "koleksiyon bos — once /index-sinyaller cagirin"}
                continue
            r = kol.query(query_texts=[q], n_results=min(n_results, kol.count()))
            cikti[ad] = [
                {"icerik": d[:400], "meta": m, "uzaklik": u}
                for d, m, u in zip(r["documents"][0], r["metadatas"][0], r["distances"][0])
            ]
        except Exception as e:
            cikti[ad] = {"hata": f"{type(e).__name__}: {e}"}
    return {"sorgu": q, "sonuclar": cikti}
