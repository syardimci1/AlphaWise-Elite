from fastapi import FastAPI
import talib
import numpy as np
import yfinance as yf
import httpx
import pandas as pd

MARKET_DATA_URL = "http://market-data:8000"

_PERIOD_TO_LIMIT = {"1mo": 22, "3mo": 65, "6mo": 130, "1y": 260, "2y": 520, "5y": 1300}


def get_price_data(ticker: str, period: str = "6mo"):
    """
    Fatih Bora'nin merkezi Market Data Engine onerisi geregi eklendi (12.08.2026).
    ARTIK dogrudan yfinance CAGIRMIYOR - merkezi market-data servisinden okuyor
    (Qlib'in topladigi 7000+ hisselik depo). Ayni format (Open/High/Low/Close/Volume
    sutunlu DataFrame) donduruyor, geri kalan kod degismiyor.
    """
    limit = _PERIOD_TO_LIMIT.get(period, 130)
    try:
        resp = httpx.get(f"{MARKET_DATA_URL}/price/{ticker}", params={"limit": limit}, timeout=30.0)
        result = resp.json()
        rows = result.get("data", [])
        if not rows:
            raise ValueError("merkezi depo bos, yfinance'e dusuluyor")
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        df = df.rename(columns={
            "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "volume": "Volume",
        })
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception:
        # Merkezi depo basarisiz olursa, eski yontem (yfinance) yedek olarak kalir
        return yf.download(ticker, period=period, progress=False)
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
    data = get_price_data(ticker, period=period)
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

from . import walkforward as wf
from . import formasyon as fm


@app.get("/backtest/{ticker}")
def backtest_technical_strategy(
    ticker: str,
    period: str = "5y",
    egitim_gun: int = wf.EGITIM_GUN,
    test_gun: int = wf.TEST_GUN,
    maliyet_yuzde: float = 0.20,
):
    """
    TAA'nin RSI+SMA kesisim mantigini GERCEK gecmis fiyat verisiyle
    geriye donuk test eder.

    23.08.2026 DEGISIKLIK — Anayasa §8.6 uyumu:
      §8.6: "Walk-Forward Optimization (VectorBT): Standard backtest yasak.
             Sadece expanding/rolling window. TCA: %0.20 slippage dahil."
    Onceki surum TUM gecmise tek seferde sabit parametre uyguluyordu
    (ornek-ICI) ve fees=0.001 / slippage=0 (yani %0.10) kullaniyordu —
    iki maddede de ihlal. Artik birincil olcum kayan pencereyle
    ORNEK-DISI yapilir ve islem basina toplam maliyet varsayilan %0.20'dir.

    API SOZLESMESI KORUNDU: eski alanlarin hicbiri kaldirilmadi veya tip
    degistirmedi; yalnizca DEGERLERI artik §8.6 uyumlu birincil olcumu
    yansitiyor. Ornek-ici eski olcum `referans_olcum_ornek_ici` altinda,
    "abartir" uyarisiyla birlikte ayrica donuyor.

    ONEMLI KAPSAM NOTU: Bu, sadece TEKNIK gostergelere (RSI, SMA) dayali bir
    backtest'tir. FAA/RAA/SAA'nin (temel, risk, duygu) katkisini icermez,
    cunku bu katmanlarin gecmise donuk (historical) hesaplama altyapisi
    henuz yok. Yani bu, MAA'nin tam 4-katmanli kararinin degil, sadece
    TAA'nin teknik mantiginin gecmis performansidir.
    """
    try:
        data = get_price_data(ticker, period=period)
        if data.empty:
            return {"error": f"{ticker} icin veri bulunamadi"}

        close = data["Close"]
        if isinstance(close, type(data)):
            close = close.iloc[:, 0]
        close = close.dropna().sort_index()

        fees, slip = wf.maliyetten_fees_slip(maliyet_yuzde)

        gerekli = max(egitim_gun, wf.ISINMA) + 10
        if len(close) < gerekli:
            return {
                "error": (f"{ticker}: walk-forward icin yetersiz veri "
                          f"({len(close)} bar, gereken >= {gerekli}). "
                          f"Daha uzun bir 'period' deneyin (or. 5y)."),
                "anayasa_8_6_uyumlu": False,
                "bar_sayisi": len(close),
            }

        birincil, secimler = wf.walk_forward(
            close, fees, slip, egitim_gun=egitim_gun, test_gun=test_gun)
        if birincil is None:
            return {
                "error": f"{ticker}: ornek-disi pencere olusturulamadi",
                "anayasa_8_6_uyumlu": False,
            }

        referans = wf.ornek_ici(close, fees, slip)
        al_tut = wf.al_tut_referansi(close, secimler)

        return {
            # --- eski sozlesme (alanlar ayni, degerler artik §8.6 uyumlu) ---
            "ticker": ticker,
            "period": period,
            "strategy": "RSI+SMA kesisimi; parametreler her egitim penceresinde yeniden secilir",
            "scope_note": "Sadece teknik (TAA) mantigi test edildi, FAA/RAA/SAA dahil degil",
            "initial_cash": 10000,
            "final_value": birincil["son_deger"],
            "total_return_pct": birincil["toplam_getiri_yuzde"],
            "total_trades": birincil["islem_sayisi"],
            "win_rate_pct": birincil["kazanma_orani_yuzde"],
            "max_drawdown_pct": birincil["maks_dusus_yuzde"],
            "sharpe_ratio": birincil["sharpe"],
            # --- §8.6 uyum bilgisi ---
            "anayasa_8_6_uyumlu": True,
            "yontem": "walk_forward_ornek_disi",
            "maliyet_yuzde": round(float(maliyet_yuzde), 4),
            "egitim_gun": egitim_gun,
            "test_gun": test_gun,
            "pencere_sayisi": len(secimler),
            "bar_sayisi": len(close),
            "birincil_olcum": birincil,
            "referans_olcum_ornek_ici": referans,
            "al_tut_referansi": al_tut,
            "secilen_parametreler_ornek": secimler[:3],
            # --- 3b.3: kullanici bilgilendirmesi ---
            "olcum_notu": (
                "Bu sonuc artik gercekci test sonucudur, onceki iyimser "
                "rakamlar degil. Onceki surum parametreleri tum gecmise tek "
                "seferde uyguluyor (ornek-ici) ve islem maliyetini eksik "
                "sayiyordu; ikisi de performansi sistematik olarak ABARTIR. "
                "Birincil olcum artik kayan pencereyle ornek-disi yapilir ve "
                f"islem basina %{maliyet_yuzde:.2f} maliyet dahildir, bu "
                "yuzden Sharpe ve getiri genellikle DAHA DUSUK cikar. "
                "'referans_olcum_ornek_ici' yalnizca karsilastirma icindir, "
                "karar dayanagi yapilamaz."
            ),
            "uyari": (
                "Gecmis performans gelecek icin garanti degildir. Bu ciktı "
                "yatirim tavsiyesi degildir."
            ),
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/formasyon/{ticker}")
def candlestick_formasyonlari(ticker: str, period: str = "6mo", gun: int = 10):
    """Klasik mum formasyonlarini OLGUSAL olarak tespit eder (23.08.2026).

    Fikir kaynagi anupama-srivastava/market-pattern-recognition (MIT); kod
    kopyalanmadi, yeniden yazildi ve kaynaktaki iki dogrulanmis hata
    giderildi (bkz. formasyon.py). Bilgisayarli goru sinifi port EDILMEDI.

    DIKKAT: Formasyonlarin bu sistemdeki ongoru gucu KALIBRE EDILMEMISTIR.
    Cikti karar koduna (EKLE/TUT/BEKLE/DIKKAT ET) baglanmaz, yalnizca
    gozlem/baglam katmanidir.
    """
    try:
        data = get_price_data(ticker, period=period)
        if data.empty:
            return {"error": f"{ticker} icin veri bulunamadi"}
        gerekli = {"Open", "High", "Low", "Close"}
        if not gerekli.issubset(data.columns):
            return {"error": f"eksik sutun: {sorted(gerekli - set(data.columns))}"}
        d = data[["Open", "High", "Low", "Close"]].dropna().sort_index()
        if len(d) < 25:
            return {"error": f"{ticker}: yetersiz bar ({len(d)}, gereken >= 25)"}
        ozet = fm.son_bar_ozeti(d, gun=gun)
        ozet["ticker"] = ticker.upper()
        ozet["period"] = period
        ozet["bar_sayisi"] = len(d)
        return ozet
    except Exception as e:
        return {"error": str(e)}
