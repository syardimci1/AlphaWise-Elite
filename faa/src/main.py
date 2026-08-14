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


def _get_fundamentals_from_fmp(ticker: str):
    """FMP fallback (13.08.2026) - yfinance basarisiz olursa devreye girer."""
    import httpx
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        return None
    try:
        profile = httpx.get("https://financialmodelingprep.com/stable/profile",
                             params={"symbol": ticker, "apikey": api_key}, timeout=15.0).json()
        ratios = httpx.get("https://financialmodelingprep.com/stable/ratios-ttm",
                            params={"symbol": ticker, "apikey": api_key}, timeout=15.0).json()
        metrics = httpx.get("https://financialmodelingprep.com/stable/key-metrics-ttm",
                             params={"symbol": ticker, "apikey": api_key}, timeout=15.0).json()
        target = httpx.get("https://financialmodelingprep.com/stable/price-target-consensus",
                            params={"symbol": ticker, "apikey": api_key}, timeout=15.0).json()

        if not profile or not isinstance(profile, list):
            return None
        p = profile[0]
        r = ratios[0] if ratios and isinstance(ratios, list) else {}
        m = metrics[0] if metrics and isinstance(metrics, list) else {}
        t = target[0] if target and isinstance(target, list) else {}

        return {
            "ticker": ticker,
            "company_name": p.get("companyName"),
            "sector": p.get("sector"),
            "pe_ratio": r.get("priceToEarningsRatioTTM"),
            "forward_pe": None,
            "pb_ratio": r.get("priceToBookRatioTTM"),
            "dividend_yield": r.get("dividendYieldTTM"),
            "payout_ratio": r.get("dividendPayoutRatioTTM"),
            "roe": m.get("returnOnEquityTTM"),
            "roa": m.get("returnOnAssetsTTM"),
            "debt_to_equity": r.get("debtToEquityRatioTTM"),
            "current_ratio": r.get("currentRatioTTM"),
            "profit_margin": r.get("netProfitMarginTTM"),
            "ebitda_margin": r.get("ebitdaMarginTTM"),
            "revenue_growth": None,
            "earnings_growth": None,
            "beta": p.get("beta"),
            "market_cap": p.get("marketCap"),
            "free_cash_flow": None,
            "analyst_consensus": {
                "recommendation": None,
                "recommendation_mean": None,
                "number_of_analysts": None,
                "target_mean_price": t.get("targetConsensus"),
                "target_high_price": t.get("targetHigh"),
                "target_low_price": t.get("targetLow"),
                "current_price": p.get("price"),
            },
            "data_source": "fmp_fallback",
        }
    except Exception:
        return None


def get_fundamentals(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if not info or not info.get("longName"):
            raise ValueError("yfinance bos/eksik veri dondu")
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
            "analyst_consensus": {
                "recommendation": info.get("recommendationKey"),
                "recommendation_mean": info.get("recommendationMean"),
                "number_of_analysts": info.get("numberOfAnalystOpinions"),
                "target_mean_price": info.get("targetMeanPrice"),
                "target_high_price": info.get("targetHighPrice"),
                "target_low_price": info.get("targetLowPrice"),
                "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            },
            "data_source": "yfinance",
        }
    except Exception:
        fmp_result = _get_fundamentals_from_fmp(ticker)
        if fmp_result:
            return fmp_result
        return {"ticker": ticker, "error": "yfinance ve FMP ikisi de basarisiz oldu"}


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
