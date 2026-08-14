"""
ALPHAWISE - SAA (Sentiment Analysis Agent) v2
DEGISIKLIK (11.08.2026, Opus): 
- Haber kaynagi yfinance (resmi degil, guvenilmez) -> Finnhub (resmi, 4-anahtarli havuz)
- Sentiment motoru: kendi transformers modeli -> merkezi FinBERT servisi (8070)
  (tek dogruluk kaynagi, model-drift yok, halusinasyona kapali siniflandirici)
- Veri kalite kontrolu: bos/eski haber -> durust "sentiment atlandi" (uydurma yok)
"""
from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import os
import time
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ALPHAWISE - SAA (Sentiment Analysis Agent) v2")

FINBERT_URL = os.getenv("FINBERT_URL", "http://finbert:8000")

# --- Finnhub 4-anahtarli havuz (rate-limit dayanikligi icin rotasyon) ---
def _get_finnhub_keys():
    keys = []
    for i in range(1, 5):
        k = os.getenv(f"FINNHUB_API_KEY_{i}")
        if k:
            keys.append(k)
    return keys

_finnhub_keys = _get_finnhub_keys()
_key_index = 0


def _next_finnhub_key():
    """Sirayla anahtar dondurur (round-robin rotasyon)."""
    global _key_index
    if not _finnhub_keys:
        return None
    key = _finnhub_keys[_key_index % len(_finnhub_keys)]
    _key_index += 1
    return key


def fetch_finnhub_news(ticker: str, max_news: int = 10):
    """
    Finnhub'dan son 7 gunun haberlerini ceker.
    Bir anahtar rate-limit'e (429) takilirsa otomatik digerine gecer.
    """
    if not _finnhub_keys:
        return {"error": "Finnhub anahtari tanimli degil"}

    to_date = datetime.now(timezone.utc).date()
    from_date = to_date - timedelta(days=7)

    last_error = None
    # Her anahtari bir kez dene (hepsini tuketene kadar)
    for _ in range(len(_finnhub_keys)):
        key = _next_finnhub_key()
        try:
            resp = httpx.get(
                "https://finnhub.io/api/v1/company-news",
                params={
                    "symbol": ticker.upper(),
                    "from": str(from_date),
                    "to": str(to_date),
                    "token": key,
                },
                timeout=15.0,
            )
            if resp.status_code == 429:
                last_error = "rate_limit"
                continue  # sonraki anahtara gec
            if resp.status_code != 200:
                last_error = f"HTTP {resp.status_code}"
                continue
            data = resp.json()
            if isinstance(data, list):
                # KIRLILIK FILTRESI: sadece hedef ticker'in gercekten ilgili
                # oldugu haberleri tut (related alaninda sembol geçmeli).
                # Finnhub sektor haberlerini de karistirdigi icin bu sart.
                target = ticker.upper()
                filtered = []
                for item in data:
                    related = str(item.get("related", "")).upper()
                    # related virgulle ayrik olabilir: "NVDA,AMD" gibi
                    related_symbols = [s.strip() for s in related.split(",")]
                    if target in related_symbols:
                        filtered.append(item)
                return {"news": filtered[:max_news], "raw_count": len(data), "filtered_count": len(filtered)}
            last_error = "beklenmeyen_format"
        except Exception as e:
            last_error = str(e)
            continue

    return {"error": f"Tum anahtarlar basarisiz: {last_error}"}


def score_with_finbert(texts: list):
    """Metinleri merkezi FinBERT servisine gonderir, sentiment skorlari alir."""
    try:
        resp = httpx.post(
            f"{FINBERT_URL}/sentiment/batch",
            json={"texts": texts},
            timeout=30.0,
        )
        if resp.status_code != 200:
            return {"error": f"FinBERT HTTP {resp.status_code}"}
        return resp.json()
    except Exception as e:
        return {"error": f"FinBERT baglanti hatasi: {str(e)}"}


class TextInput(BaseModel):
    text: str


@app.get("/health")
def health():
    return {
        "service": "SAA",
        "status": "ok",
        "sentiment_engine": "FinBERT (merkezi servis)",
        "news_source": f"Finnhub ({len(_finnhub_keys)} anahtar havuzu)",
    }


@app.post("/analyze")
def analyze_text(input: TextInput):
    """Tek bir metnin sentiment'ini analiz eder (FinBERT uzerinden)."""
    result = score_with_finbert([input.text])
    if "error" in result:
        return {"text": input.text, "error": result["error"]}
    r = result["results"][0]
    return {"text": input.text, "sentiment": {"label": r["label"], "score": r["score"]}}


@app.get("/analyze/{ticker}")
def analyze_ticker(ticker: str, max_news: int = 10):
    """
    Bir hisse icin haber-tabanli sentiment analizi.
    MAA kaskadinin cagirdigi ana endpoint - cikti formati korunmustur.
    """
    # 1. Haber cek (Finnhub, cok-anahtarli)
    news_result = fetch_finnhub_news(ticker, max_news)
    if "error" in news_result:
        # DURUST BOSLUK: veri yoksa uydurma yapma, atla
        return {
            "ticker": ticker.upper(),
            "news_count": 0,
            "average_score": 0.0,
            "overall": "neutral",
            "data_status": f"sentiment_atlandi: {news_result['error']}",
        }

    news_items = news_result["news"]

    # 2. KALITE KONTROLU: haber yoksa durust bosluk
    if not news_items:
        return {
            "ticker": ticker.upper(),
            "news_count": 0,
            "average_score": 0.0,
            "overall": "neutral",
            "data_status": "sentiment_atlandi: son 7 gunde haber yok",
        }

    # 3. Basliklari topla
    titles = []
    for item in news_items:
        title = item.get("headline", "")
        if title:
            titles.append(title)

    if not titles:
        return {
            "ticker": ticker.upper(),
            "news_count": 0,
            "average_score": 0.0,
            "overall": "neutral",
            "data_status": "sentiment_atlandi: baslik bulunamadi",
        }

    # 4. FinBERT ile skorla
    finbert_result = score_with_finbert(titles)
    if "error" in finbert_result:
        return {
            "ticker": ticker.upper(),
            "news_count": 0,
            "average_score": 0.0,
            "overall": "neutral",
            "data_status": f"sentiment_atlandi: {finbert_result['error']}",
        }

    # 5. Skorlama mantigi (eski koddan korundu: signed_score, ortalama, +-0.15 esik)
    scores = []
    details = []
    for r in finbert_result["results"]:
        label = r["label"].lower()
        score = r["score"]
        signed_score = score if label == "positive" else (-score if label == "negative" else 0.0)
        scores.append(signed_score)
        details.append({"title": r["text"], "label": label, "score": round(score, 4)})

    avg_score = sum(scores) / len(scores) if scores else 0.0

    if avg_score > 0.15:
        overall = "positive"
    elif avg_score < -0.15:
        overall = "negative"
    else:
        overall = "neutral"

    return {
        "ticker": ticker.upper(),
        "news_count": len(details),
        "average_score": round(avg_score, 4),
        "overall": overall,
        "details": details,
        "data_status": "ok",
    }
