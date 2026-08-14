"""
ALPHAWISE - FinBERT Sentiment Servisi
FinGPT'nin ucretsiz, GPU gerektirmeyen alternatifi.
ProsusAI/finbert (HuggingFace, gated degil, 110M parametre, CPU'da calisir)
kullanarak finansal metin sentiment analizi yapar.
"""
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline

app = FastAPI(title="ALPHAWISE - FinBERT Sentiment Service")

_classifier = None


def get_classifier():
    global _classifier
    if _classifier is None:
        _classifier = pipeline("sentiment-analysis", model="ProsusAI/finbert")
    return _classifier


class SentimentRequest(BaseModel):
    text: str


class BatchSentimentRequest(BaseModel):
    texts: list[str]


@app.get("/health")
def health():
    return {"service": "FinBERT", "status": "ok"}


@app.post("/sentiment")
def analyze_sentiment(req: SentimentRequest):
    """Tek bir finansal metnin sentiment'ini analiz eder (positive/negative/neutral)."""
    classifier = get_classifier()
    result = classifier(req.text)[0]
    return {
        "text": req.text,
        "label": result["label"],
        "score": round(result["score"], 4),
    }


@app.post("/sentiment/batch")
def analyze_sentiment_batch(req: BatchSentimentRequest):
    """Birden fazla metni tek seferde analiz eder (orn. SAA'nin haber basliklari)."""
    classifier = get_classifier()
    results = classifier(req.texts)
    return {
        "results": [
            {"text": t, "label": r["label"], "score": round(r["score"], 4)}
            for t, r in zip(req.texts, results)
        ]
    }
