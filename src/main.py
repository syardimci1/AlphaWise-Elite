from fastapi import FastAPI
import yfinance as yf
import numpy as np
import pandas as pd
from scipy import stats
import psycopg2
import redis
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ALPHAWISE - RAA (Risk Analysis Agent)")

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
    status = {"service": "RAA", "status": "ok", "checks": {}}

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

@app.get("/analyze/{ticker}")
def analyze(ticker: str, period: str = "1y"):
    data = yf.download(ticker, period=period, progress=False)
    if data.empty:
        return {"error": f"{ticker} için veri bulunamadı"}

    close = data["Close"].values.flatten().astype(float)
    returns = np.diff(close) / close[:-1]

    # Yıllıklaştırılmış volatilite
    volatility = float(np.std(returns) * np.sqrt(252))

    # Sharpe Ratio (risksiz oran %4 varsayımıyla)
    risk_free_rate = 0.04
    mean_return_annual = float(np.mean(returns) * 252)
    sharpe = (mean_return_annual - risk_free_rate) / volatility if volatility > 0 else None

    # Sortino Ratio (sadece negatif getirilerin std'si)
    downside_returns = returns[returns < 0]
    downside_std = float(np.std(downside_returns) * np.sqrt(252)) if len(downside_returns) > 0 else 0
    sortino = (mean_return_annual - risk_free_rate) / downside_std if downside_std > 0 else None

    # Maximum Drawdown
    cumulative = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = float(np.min(drawdown))

    # Value at Risk (VaR) - %95 güven aralığı, tarihsel yöntem
    var_95 = float(np.percentile(returns, 5))

    # --- UZUN VADELI, SAGLAM GETIRI TAHMINI (budget-scenario icin) ---
    # Neden: yukaridaki "annualized_return" (aritmetik ortalama * 252) tek yillik
    # gurultulu veriden hesaplaniyor ve "volatility drag" nedeniyle gercek bileşik
    # buyumeyi abartiyor. Bunun yerine: (1) 5 yillik gercek CAGR hesapla,
    # (2) gerceksiz uc degerleri sinirla (winsorize), (3) genis piyasa ortalamasina
    # dogru "buzulme" (shrinkage) uygula - bu, portfoy teorisinde bilinen,
    # tek bir hissenin sansli/sanssiz donemine asiri guvenmeyi onleyen bir teknik.
    long_term_cagr = None
    long_term_cagr_capped = None
    long_term_cagr_shrunk = None
    long_term_years_used = None

    try:
        hist5y = yf.download(ticker, period="5y", progress=False)
        if not hist5y.empty and len(hist5y) > 252:
            close5y = hist5y["Close"].values.flatten().astype(float)
            years_available = len(close5y) / 252.0
            start_price = float(close5y[0])
            end_price = float(close5y[-1])
            if start_price > 0 and years_available > 0:
                cagr = (end_price / start_price) ** (1.0 / years_available) - 1.0
                long_term_cagr = round(float(cagr), 4)
                long_term_years_used = round(years_available, 2)

                # Sinirlama: yillik getiriyi gercekci bir araliga cek (-%15 ile +%35 arasi)
                CAP_LOW, CAP_HIGH = -0.15, 0.35
                capped = max(CAP_LOW, min(CAP_HIGH, cagr))
                long_term_cagr_capped = round(float(capped), 4)

                # Buzulme (shrinkage): hissenin kendi CAGR'ini genis piyasa
                # ortalamasina (%9, S&P500 tarihsel nominal ortalama) dogru cek.
                # Agirlik 0.55 = hissenin kendi gecmisine %55 guven, %45 piyasa ortalamasi.
                MARKET_PRIOR = 0.09
                SHRINKAGE_WEIGHT = 0.55
                shrunk = SHRINKAGE_WEIGHT * capped + (1 - SHRINKAGE_WEIGHT) * MARKET_PRIOR
                long_term_cagr_shrunk = round(float(shrunk), 4)
    except Exception:
        pass

    return {
        "ticker": ticker,
        "period": period,
        "annualized_volatility": round(volatility, 4),
        "annualized_return": round(mean_return_annual, 4),
        "sharpe_ratio": round(sharpe, 4) if sharpe is not None else None,
        "sortino_ratio": round(sortino, 4) if sortino is not None else None,
        "max_drawdown": round(max_drawdown, 4),
        "var_95_daily": round(var_95, 4),
        "long_term_cagr_5y_raw": long_term_cagr,
        "long_term_cagr_5y_capped": long_term_cagr_capped,
        "long_term_cagr_5y_shrunk_estimate": long_term_cagr_shrunk,
        "long_term_years_used": long_term_years_used,
        "methodology_note": (
            "shrunk_estimate = 0.55 * capped_5y_CAGR + 0.45 * market_prior(9%). "
            "capped_5y_CAGR, ham 5 yillik CAGR'in [-15%, +35%] araligina sinirlanmis halidir. "
            "Bu, tek bir olagandisi yilin abartili sekilde projekte edilmesini onlemek icindir."
        ),
    }
