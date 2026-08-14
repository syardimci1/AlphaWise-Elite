from fastapi import FastAPI
import yfinance as yf
import numpy as np
import pandas as pd
from scipy import stats
import psycopg2
import redis
import os
from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta

load_dotenv()


def _period_to_dates(period: str):
    days_map = {"1mo": 31, "3mo": 91, "6mo": 182, "1y": 365, "5y": 365 * 5}
    days = days_map.get(period, 365)
    end = datetime.utcnow().date()
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()


def _fetch_from_tiingo(ticker: str, period: str):
    api_key = os.getenv("TIINGO_API_KEY")
    if not api_key:
        return None
    start, end = _period_to_dates(period)
    try:
        resp = requests.get(
            f"https://api.tiingo.com/tiingo/daily/{ticker}/prices",
            params={"startDate": start, "endDate": end, "token": api_key},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        df = df.rename(columns={"close": "Close"})
        return df[["Close"]]
    except Exception:
        return None


def _fetch_from_polygon(ticker: str, period: str):
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        return None
    start, end = _period_to_dates(period)
    try:
        resp = requests.get(
            f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}",
            params={"apiKey": api_key, "adjusted": "true", "sort": "asc", "limit": 5000},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results")
        if not results:
            return None
        df = pd.DataFrame(results)
        df["date"] = pd.to_datetime(df["t"], unit="ms")
        df = df.set_index("date").sort_index()
        df = df.rename(columns={"c": "Close"})
        return df[["Close"]]
    except Exception:
        return None


def _fetch_from_alphavantage(ticker: str, period: str):
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        return None
    try:
        resp = requests.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "TIME_SERIES_DAILY",
                "symbol": ticker,
                "outputsize": "full" if period == "5y" else "compact",
                "apikey": api_key,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        series = data.get("Time Series (Daily)")
        if not series:
            return None
        df = pd.DataFrame(series).T
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df = df.rename(columns={"4. close": "Close"})
        df["Close"] = df["Close"].astype(float)
        start, end = _period_to_dates(period)
        df = df[(df.index >= start) & (df.index <= end)]
        return df[["Close"]]
    except Exception:
        return None


def _fetch_from_central(ticker: str, period: str):
    """Fatih Bora onerisi (12.08.2026): merkezi Market Data Engine, zincirin basinda denenir."""
    try:
        resp = requests.get(f"http://market-data:8000/price/{ticker}", params={"limit": 260}, timeout=10)
        result = resp.json()
        rows = result.get("data", [])
        if not rows:
            return None
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        df = df.rename(columns={"close": "Close"})
        df["Close"] = df["Close"].astype(float)
        return df[["Close"]]
    except Exception:
        return None


def fetch_ohlcv_with_fallback(ticker: str, period: str):
    """
    Veri kaynagi zinciri: yfinance -> Tiingo -> Polygon.io -> Alpha Vantage.
    Ilk basarili olan kaynaktan (Close kolonu iceren) DataFrame ve kaynak adini dondurur.
    """
    df = _fetch_from_central(ticker, period)
    if df is not None and not df.empty:
        return df, "merkezi_depo"
    try:
        data = yf.download(ticker, period=period, progress=False)
        if not data.empty:
            return data, "yfinance"
    except Exception:
        pass

    df = _fetch_from_tiingo(ticker, period)
    if df is not None and not df.empty:
        return df, "tiingo"

    df = _fetch_from_polygon(ticker, period)
    if df is not None and not df.empty:
        return df, "polygon"

    df = _fetch_from_alphavantage(ticker, period)
    if df is not None and not df.empty:
        return df, "alpha_vantage"

    return None, None

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

from nixtla import NixtlaClient

TIMEGPT_API_KEY = os.getenv("TIMEGPT_API_KEY")


@app.get("/forecast/{ticker}")
def forecast_price(ticker: str, horizon_days: int = 30):
    """
    TimeGPT (Nixtla) kullanarak, gecmis 1 yillik fiyat verisine dayali,
    gelecek `horizon_days` gun icin istatistiksel bir fiyat tahmini uretir.
    Guven araligi (%80) dahildir - bu bir garanti degil, olasilik araligidir.
    """
    if not TIMEGPT_API_KEY:
        return {"error": "TIMEGPT_API_KEY tanimli degil"}

    try:
        data = yf.download(ticker, period="1y", progress=False)
        if data.empty:
            return {"error": f"{ticker} icin veri bulunamadi"}

        close = data["Close"]
        if hasattr(close, "iloc") and len(close.shape) > 1:
            close = close.iloc[:, 0]
        close = close.dropna()

        # Tam is gunu takvimine gore yeniden indeksle, tatil bosluklarini
        # bir onceki gunun fiyatiyla doldur (TimeGPT bosluksuz seri istiyor)
        full_bdays = pd.date_range(start=close.index.min(), end=close.index.max(), freq="B")
        close = close.reindex(full_bdays).ffill()

        df = pd.DataFrame({
            "unique_id": ticker,
            "ds": close.index,
            "y": close.values,
        })

        client = NixtlaClient(api_key=TIMEGPT_API_KEY)
        forecast = client.forecast(
            df=df, h=horizon_days, level=[80], freq="B",
            time_col="ds", target_col="y", id_col="unique_id",
            model="timegpt-1",
        )

        last_row = forecast.iloc[-1]
        first_row = forecast.iloc[0]

        return {
            "ticker": ticker,
            "horizon_days": horizon_days,
            "current_price": round(float(close.iloc[-1]), 2),
            "forecast_first_day": {
                "date": str(first_row["ds"])[:10],
                "predicted": round(float(first_row["TimeGPT"]), 2),
            },
            "forecast_last_day": {
                "date": str(last_row["ds"])[:10],
                "predicted": round(float(last_row["TimeGPT"]), 2),
                "lower_80pct": round(float(last_row.get("TimeGPT-lo-80", 0)), 2),
                "upper_80pct": round(float(last_row.get("TimeGPT-hi-80", 0)), 2),
            },
            "disclaimer": "Bu istatistiksel bir tahmindir, yatirim tavsiyesi degildir. Gercek fiyat bu araligin disinda da olusabilir.",
        }
    except Exception as e:
        return {"error": str(e)}


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
    data, data_source = fetch_ohlcv_with_fallback(ticker, period)
    if data is None or data.empty:
        return {"error": f"{ticker} için veri bulunamadı (tum kaynaklar denendi: yfinance/tiingo/polygon/alpha_vantage)"}

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
        hist5y, _ = fetch_ohlcv_with_fallback(ticker, "5y")
        if hist5y is not None and not hist5y.empty and len(hist5y) > 252:
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
        "data_source": data_source,
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
