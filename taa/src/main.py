from fastapi import FastAPI
import talib
import numpy as np
import yfinance as yf
import psycopg2
import redis
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ALPHAWISE - TAA (Technical Analysis Agent)")

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
    status = {"service": "TAA", "status": "ok", "checks": {}}
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


def calculate_fibonacci_levels(high: float, low: float):
    diff = high - low
    return {
        "fib_0": round(high, 2),
        "fib_23.6": round(high - diff * 0.236, 2),
        "fib_38.2": round(high - diff * 0.382, 2),
        "fib_50": round(high - diff * 0.5, 2),
        "fib_61.8": round(high - diff * 0.618, 2),
        "fib_100": round(low, 2),
    }


@app.get("/analyze/{ticker}")
def analyze(ticker: str, period: str = "6mo"):
    data = yf.download(ticker, period=period, progress=False)
    if data.empty:
        return {"error": f"{ticker} icin veri bulunamadi"}

    close = data["Close"].values.flatten().astype(float)
    high = data["High"].values.flatten().astype(float)
    low = data["Low"].values.flatten().astype(float)
    volume = data["Volume"].values.flatten().astype(float)

    rsi = talib.RSI(close, timeperiod=14)
    sma20 = talib.SMA(close, timeperiod=20)
    sma50 = talib.SMA(close, timeperiod=50)
    macd, macd_signal, macd_hist = talib.MACD(close)
    atr = talib.ATR(high, low, close, timeperiod=14)

    # 52 haftalik (ya da secilen period'daki) en yuksek/en dusuk - Fibonacci icin
    period_high = float(np.max(high))
    period_low = float(np.min(low))
    fib_levels = calculate_fibonacci_levels(period_high, period_low)

    # Hacim analizi - son hacmin ortalamaya orani
    avg_volume = float(np.mean(volume[-20:])) if len(volume) >= 20 else float(np.mean(volume))
    last_volume = float(volume[-1])
    volume_ratio = (last_volume / avg_volume) if avg_volume > 0 else None

    # Destek/Direnc: basit yontem - son N gunun local min/max noktalari
    recent_window = min(60, len(close))
    recent_high = float(np.max(high[-recent_window:]))
    recent_low = float(np.min(low[-recent_window:]))

    latest = {
        "ticker": ticker,
        "last_close": float(close[-1]),
        "rsi_14": float(rsi[-1]) if not np.isnan(rsi[-1]) else None,
        "sma_20": float(sma20[-1]) if not np.isnan(sma20[-1]) else None,
        "sma_50": float(sma50[-1]) if not np.isnan(sma50[-1]) else None,
        "macd": float(macd[-1]) if not np.isnan(macd[-1]) else None,
        "macd_signal": float(macd_signal[-1]) if not np.isnan(macd_signal[-1]) else None,
        "atr_14": float(atr[-1]) if not np.isnan(atr[-1]) else None,
        "volume_last": last_volume,
        "volume_avg_20d": round(avg_volume, 0),
        "volume_ratio": round(volume_ratio, 3) if volume_ratio is not None else None,
        "support_resistance": {
            "resistance": round(recent_high, 2),
            "support": round(recent_low, 2),
        },
        "fibonacci_levels": fib_levels,
    }
    return latest


import vectorbt as vbt


@app.get("/backtest/{ticker}")
def backtest_technical_strategy(ticker: str, period: str = "2y"):
    """
    TAA'nin kullandigi RSI+SMA kesisim mantigina dayali basit bir teknik
    stratejiyi, GERCEK gecmis fiyat verisiyle geriye donuk test eder.

    ONEMLI KAPSAM NOTU: Bu, sadece TEKNIK gostergelere (RSI, SMA) dayali bir
    backtest'tir. FAA/RAA/SAA'nin (temel, risk, duygu) katkisini icermez,
    cunku bu katmanlarin gecmise donuk (historical) hesaplama altyapisi
    henuz yok. Yani bu, MAA'nin tam 4-katmanli kararinin degil, sadece
    TAA'nin teknik mantiginin gecmis performansidir.
    """
    try:
        data = yf.download(ticker, period=period, progress=False)
        if data.empty:
            return {"error": f"{ticker} icin veri bulunamadi"}

        close = data["Close"]
        if isinstance(close, type(data)):
            close = close.iloc[:, 0]
        close = close.dropna()

        rsi = vbt.RSI.run(close, window=14).rsi
        sma20 = vbt.MA.run(close, window=20).ma
        sma50 = vbt.MA.run(close, window=50).ma

        entries = (rsi < 30) & (sma20 > sma50)
        exits = (rsi > 70) | (sma20 < sma50)

        portfolio = vbt.Portfolio.from_signals(
            close, entries, exits,
            init_cash=10000, fees=0.001, freq="1D"
        )

        stats = portfolio.stats()

        return {
            "ticker": ticker,
            "period": period,
            "strategy": "RSI(14) < 30 VE SMA20 > SMA50 iken AL; RSI > 70 VEYA SMA20 < SMA50 iken SAT",
            "scope_note": "Sadece teknik (TAA) mantigi test edildi, FAA/RAA/SAA dahil degil",
            "initial_cash": 10000,
            "final_value": round(float(stats.get("End Value", 0)), 2),
            "total_return_pct": round(float(stats.get("Total Return [%]", 0)), 2),
            "total_trades": int(stats.get("Total Trades", 0)),
            "win_rate_pct": round(float(stats.get("Win Rate [%]", 0)), 2) if stats.get("Win Rate [%]") is not None else None,
            "max_drawdown_pct": round(float(stats.get("Max Drawdown [%]", 0)), 2),
            "sharpe_ratio": round(float(stats.get("Sharpe Ratio", 0)), 3) if stats.get("Sharpe Ratio") is not None else None,
        }
    except Exception as e:
        return {"error": str(e)}
