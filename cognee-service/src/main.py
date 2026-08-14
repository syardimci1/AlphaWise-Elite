"""
ALPHAWISE - Cognee Hafiza Servisi
MAA icin kalici, graf-tabanli uzun-vadeli hafiza.
Mem0'dan daha guclu: sadece vektor benzerligi degil, kavramlar arasi
iliskileri de (graf) tutuyor - "NVDA'nin son 3 kararinda ne oldu,
neden?" gibi baglantili sorular sorulabilir.
"""
import os
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ALPHAWISE - Cognee Memory Service")

# Cognee, OpenAI-uyumlu bir LLM saglayicisi ister - OpenRouter'i kullaniyoruz
os.environ.setdefault("LLM_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("LLM_ENDPOINT", "https://openrouter.ai/api/v1")
os.environ.setdefault("LLM_MODEL", "deepseek/deepseek-chat")


class RememberRequest(BaseModel):
    text: str
    dataset: str = "alphawise_memory"


class RecallRequest(BaseModel):
    query: str
    dataset: str = "alphawise_memory"


@app.get("/health")
def health():
    return {"service": "Cognee Memory", "status": "ok"}


@app.post("/remember")
async def remember(req: RememberRequest):
    """Yeni bir bilgiyi kalici hafizaya ekler (grafa isler)."""
    import cognee
    await cognee.add(req.text, dataset_name=req.dataset)
    await cognee.cognify([req.dataset])
    return {"status": "remembered", "dataset": req.dataset}


@app.post("/recall")
async def recall(req: RecallRequest):
    """Hafizadan, anlam+iliski temelli arama yapar."""
    import cognee
    from cognee.api.v1.search import SearchType
    results = await cognee.search(query_text=req.query, query_type=SearchType.CHUNKS)
    return {"query": req.query, "results": [str(r) for r in results]}
