from fastapi import FastAPI
from pydantic import BaseModel
import yfinance as yf
import psycopg2
import redis
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ALPHAWISE - SAA (Sentiment Analysis Agent)")

_sentiment_pipeline = None

def get_sentiment_pipeline():
    global _sentiment_pipeline
    if _sentiment_pipeline is None:
        from transformers import pipeline
        _sentiment_pipeline = pipeline(
            "sentiment-analysis",
            model="ProsusAI/finbert"
        )
    return _sentiment_pipeline

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        dbname=os.getenv("DB_NAME"),
    )

def get_redis_connection():
    return redis.Redis(
        host=os.getenv("REDIS_HOST"),
        port=os.getenv("REDIS_PORT"),
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True,
    )

@app.get("/health")
def health():
    status = {"service": "SAA", "status": "ok", "checks": {}}
    try:
        conn = get_db_connection()
        conn.close()
        status["checks"]["database"] = "connected"
    except Exception as e:
        status["checks"]["database"] = f"error: {str(e)}"
        status["status"] = "degraded"
    try:
        r = get_redis_connection()
        r.ping()
        status["checks"]["redis"] = "connected"
    except Exception as e:
        status["checks"]["redis"] = f"error: {str(e)}"
        status["status"] = "degraded"
    status["checks"]["model_loaded"] = _sentiment_pipeline is not None
    return status

class TextInput(BaseModel):
    text: str

@app.post("/analyze")
def analyze_text(input: TextInput):
    pipe = get_sentiment_pipeline()
    result = pipe(input.text)
    return {"text": input.text, "sentiment": result[0]}

@app.get("/analyze/{ticker}")
def analyze_ticker(ticker: str, max_news: int = 10):
    stock = yf.Ticker(ticker)
    news_items = stock.news[:max_news] if stock.news else []

    if not news_items:
        return {
            "ticker": ticker,
            "news_count": 0,
            "overall_sentiment": "neutral",
            "average_score": 0.0,
            "details": [],
        }

    pipe = get_sentiment_pipeline()
    details = []
    scores = []

    for item in news_items:
        title = item.get("content", {}).get("title") or item.get("title", "")
        if not title:
            continue
        result = pipe(title)[0]
        label = result["label"].lower()
        score = result["score"]
        signed_score = score if label == "positive" else (-score if label == "negative" else 0.0)
        scores.append(signed_score)
        details.append({"title": title, "label": label, "score": round(score, 4)})

    avg_score = sum(scores) / len(scores) if scores else 0.0

    if avg_score > 0.15:
        overall = "positive"
    elif avg_score < -0.15:
        overall = "negative"
    else:
        overall = "neutral"

    return {
        "ticker": ticker,
        "news_count": len(details),
        "overall_sentiment": overall,
        "average_score": round(avg_score, 4),
        "details": details,
    }
