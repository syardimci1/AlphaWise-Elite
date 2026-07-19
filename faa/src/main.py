from fastapi import FastAPI
import yfinance as yf
import psycopg2
import redis
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ALPHAWISE - FAA (Fundamental Analysis Agent)")

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
    status = {"service": "FAA", "status": "ok", "checks": {}}
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
    return status


def get_fundamentals(ticker: str):
    stock = yf.Ticker(ticker)
    info = stock.info

    return {
        "ticker": ticker,
        "company_name": info.get("longName"),
        "sector": info.get("sector"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "pb_ratio": info.get("priceToBook"),
        "dividend_yield": info.get("dividendYield"),
        "payout_ratio": info.get("payoutRatio"),
        "roe": info.get("returnOnEquity"),
        "roa": info.get("returnOnAssets"),
        "debt_to_equity": info.get("debtToEquity"),
        "current_ratio": info.get("currentRatio"),
        "profit_margin": info.get("profitMargins"),
        "ebitda_margin": info.get("ebitdaMargins"),
        "revenue_growth": info.get("revenueGrowth"),
        "earnings_growth": info.get("earningsGrowth"),
        "beta": info.get("beta"),
        "market_cap": info.get("marketCap"),
        "free_cash_flow": info.get("freeCashflow"),
        # Analist konsensusu (yeni eklenen)
        "analyst_consensus": {
            "recommendation": info.get("recommendationKey"),
            "recommendation_mean": info.get("recommendationMean"),
            "number_of_analysts": info.get("numberOfAnalystOpinions"),
            "target_mean_price": info.get("targetMeanPrice"),
            "target_high_price": info.get("targetHighPrice"),
            "target_low_price": info.get("targetLowPrice"),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        },
    }


@app.get("/analyze/{ticker}")
def analyze(ticker: str):
    return get_fundamentals(ticker)


@app.get("/compare/{ticker}")
def compare(ticker: str, peers: str):
    """
    Rakip karsilastirmasi. peers = virgul ile ayrilmis ticker listesi.
    Ornek: /compare/NVDA?peers=AMD,AVGO,INTC
    """
    peer_list = [p.strip().upper() for p in peers.split(",") if p.strip()]
    main_data = get_fundamentals(ticker)

    comparisons = []
    for peer in peer_list:
        try:
            comparisons.append(get_fundamentals(peer))
        except Exception as e:
            comparisons.append({"ticker": peer, "error": str(e)})

    return {
        "main": main_data,
        "peers": comparisons,
    }
