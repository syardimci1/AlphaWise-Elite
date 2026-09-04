"""
ALPHAWISE - Merkezi Market Data Servisi
Fatih Bora'nin elestirisine cozum: TAA/RAA/FAA artik yfinance/Tiingo'yu
dogrudan cagirmiyor, hepsi BU servisi cagirir.
- Once Qlib'in zaten topladigi merkezi veriyi kontrol eder (hizli, API cagrisi yok)
- Yoksa/eskiyse, Tiingo'dan (coklu-anahtar havuzu) ceker VE merkezi depoya yazar
  (bir sonraki istek + Qlib egitimi icin kalici hale gelir)
"""
import os
import csv
import time
import httpx
from datetime import datetime, timezone
from fastapi import FastAPI

app = FastAPI(title="ALPHAWISE - Market Data Service (Merkezi)")

CENTRAL_DATA_DIR = "/app/csv_data/us_data"  # Qlib ile PAYLASILAN volume


def get_tiingo_keys():
    keys = []
    i = 1
    while True:
        k = os.getenv(f"TIINGO_TOKEN_{i}")
        if not k:
            break
        keys.append(k)
        i += 1
    return keys


_key_index = 0


def next_tiingo_key(keys):
    global _key_index
    if not keys:
        return None
    key = keys[_key_index % len(keys)]
    _key_index += 1
    return key


def bar_butunlugu_gecerli(row: dict) -> bool:
    """Bar ici tutarlilik: high tum fiyatlarin ustunde, low altinda olmali.

    04.09.2026 DUZELTME: qlib'in merkezi deposunda (bu servisin de okudugu
    ayni CSV'ler) 4.649 imkansiz bar bulundu (high < max(open,close) veya
    low > min(open,close)) - kok neden donmus on-yayin barlar, bkz.
    data-fetcher/scripts/incremental_update.py. Kaynaktaki dosyalar
    yeniden yazilarak onarildi, ancak (a) bazi barlar sadece saglayicinin
    kendi bozuk verisi oldugu icin onarilmadan kaldi, (b) TAA'nin protected
    taa/src/main.py dosyasina bu kontrol EKLENEMEZ. Bu yuzden ayni kural,
    /price'in OKUMA yolunda tekrarlanir: TAA'nin formasyon modulu
    (ust_golge = High - max(Open,Close)) bu tur barlarda negatif golge
    uretiyor ve ATR'yi bozuyor - imkansiz bar, eksik bardan daha kotudur.
    Kural incremental_update.py'deki bar_butunlugu_gecerli() ile AYNIDIR.
    """
    try:
        o, h, l, c = (float(row["open"]), float(row["high"]),
                      float(row["low"]), float(row["close"]))
    except (KeyError, TypeError, ValueError):
        return False
    if any(x != x for x in (o, h, l, c)):  # NaN
        return False
    return h >= max(o, c) and l <= min(o, c) and h >= l


def read_central_csv(ticker: str, limit: int = 60):
    """Once merkezi depoyu (Qlib'in topladigi veri) dener - hizli, API cagrisi yok."""
    path = f"{CENTRAL_DATA_DIR}/{ticker.upper()}.csv"
    if not os.path.exists(path):
        return None
    with open(path) as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return None
    rows = [r for r in rows if bar_butunlugu_gecerli(r)]
    if not rows:
        return None
    return rows[-limit:]


def fetch_and_cache_from_tiingo(ticker: str):
    """Merkezi depoda yoksa, Tiingo'dan ceker VE merkezi depoya yazar (kalici olsun)."""
    keys = get_tiingo_keys()
    key = next_tiingo_key(keys)
    if not key:
        return None
    try:
        resp = httpx.get(
            f"https://api.tiingo.com/tiingo/daily/{ticker.upper()}/prices",
            params={"startDate": "2020-01-01", "token": key},
            timeout=30.0,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not isinstance(data, list) or not data:
            return None
    except Exception:
        return None

    os.makedirs(CENTRAL_DATA_DIR, exist_ok=True)
    path = f"{CENTRAL_DATA_DIR}/{ticker.upper()}.csv"
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "open", "close", "high", "low", "volume", "factor"])
        for row in data:
            close = row.get("close")
            adj_close = row.get("adjClose", close)
            factor = round(adj_close / close, 8) if close else 1.0
            writer.writerow([
                row["date"][:10],
                row.get("adjOpen", row.get("open")),
                adj_close,
                row.get("adjHigh", row.get("high")),
                row.get("adjLow", row.get("low")),
                row.get("adjVolume", row.get("volume")),
                factor,
            ])
    return read_central_csv(ticker)


@app.get("/health")
def health():
    keys = get_tiingo_keys()
    cached_count = 0
    if os.path.exists(CENTRAL_DATA_DIR):
        cached_count = len([f for f in os.listdir(CENTRAL_DATA_DIR) if f.endswith(".csv")])
    return {
        "service": "Market Data (Merkezi)",
        "status": "ok",
        "tiingo_keys": len(keys),
        "cached_tickers": cached_count,
    }


@app.get("/price/{ticker}")
def get_price(ticker: str, limit: int = 60):
    """
    TAA/RAA/FAA'nin ARTIK cagirmasi gereken TEK endpoint.
    Once merkezi depo (hizli), yoksa Tiingo'dan cek+kaydet (yavas ama sadece 1 kez).
    """
    rows = read_central_csv(ticker, limit)
    if rows:
        return {"ticker": ticker.upper(), "source": "merkezi_depo", "count": len(rows), "data": rows}

    rows = fetch_and_cache_from_tiingo(ticker)
    if rows:
        return {"ticker": ticker.upper(), "source": "tiingo_canli_cekildi_ve_kaydedildi", "count": len(rows), "data": rows[-limit:]}

    return {"ticker": ticker.upper(), "error": "veri bulunamadi", "data": []}
