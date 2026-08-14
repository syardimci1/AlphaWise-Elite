"""
ALPHAWISE - Derin Web Arastirma Servisi
SearXNG (arama) + Newspaper4k/Trafilatura (metin cikarma, birbirini yedekler).
Amac: MAA'ya "web'de bu konuda ne var" turu canli arastirma yetenegi eklemek.
"""
import httpx
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="ALPHAWISE - Web Research Service")

SEARXNG_URL = "http://searxng:8080"


def extract_article_text(url: str) -> dict:
    """Once Trafilatura, olmazsa Newspaper4k dener (birbirini yedekler)."""
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            if text and len(text) > 100:
                return {"text": text[:3000], "method": "trafilatura"}
    except Exception:
        pass

    try:
        import newspaper
        article = newspaper.article(url)
        if article.text and len(article.text) > 100:
            return {"text": article.text[:3000], "method": "newspaper4k"}
    except Exception:
        pass

    return {"text": None, "method": "basarisiz"}


class ResearchRequest(BaseModel):
    query: str
    max_results: int = 5
    extract_full_text: bool = True


@app.get("/health")
def health():
    return {"service": "Web Research", "status": "ok"}


@app.post("/research")
def research(req: ResearchRequest):
    """
    SearXNG ile arama yapar, istege bagli olarak ilk N sonucun
    tam metnini cikarir (Trafilatura/Newspaper4k ile).
    """
    try:
        resp = httpx.get(
            f"{SEARXNG_URL}/search",
            params={"q": req.query, "format": "json", "language": "en"},
            timeout=20.0,
        )
        data = resp.json()
    except Exception as e:
        return {"error": f"SearXNG hatasi: {e}"}

    results = data.get("results", [])[:req.max_results]
    output = []
    for r in results:
        item = {
            "title": r.get("title"),
            "url": r.get("url"),
            "snippet": r.get("content"),
        }
        if req.extract_full_text and r.get("url"):
            extracted = extract_article_text(r["url"])
            item["full_text"] = extracted["text"]
            item["extraction_method"] = extracted["method"]
        output.append(item)

    return {"query": req.query, "count": len(output), "results": output}
