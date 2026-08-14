#!/usr/bin/env python3
"""
ALPHAWISE - Z-K Aralığı ABD Hisseleri 5 Yıllık Tiingo Veri Çekme
- 7 Tiingo anahtarı (TIINGO_TOKEN_1...N) otomatik algılar, round-robin kullanır
- NASDAQ evreninden Z-K harfiyle başlayan common stock'ları filtreler
- Her hisse için Qlib uyumlu CSV, ayrı klasörde: {OUTPUT_DIR}/{TICKER}/{TICKER}.csv
- İlerleme progress_Z_K.json'da tutulur, kaldığı yerden devam eder
"""
import os
import csv
import json
import time
import httpx
from datetime import datetime, timedelta
from pathlib import Path

# Docker içi yollar (host mount'larıyla eşleşmeli)
UNIVERSE_FILE = "/app/data_prep/us_stock_universe_Z_K.txt"
OUTPUT_DIR = "/app/csv_data/us_data"
PROGRESS_FILE = "/app/csv_data/progress_Z_K.json"
REQUESTS_PER_KEY_PER_HOUR = 45  # 50 altında güvenli
START_DATE = (datetime.now() - timedelta(days=5*365)).strftime("%Y-%m-%d")

# Z'den K'ya ters alfabetik aralık
LETTERS = list("ZYXWVUTSRQPONMLK")


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


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"completed": [], "failed": []}


def save_progress(progress):
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f)


def create_universe_from_existing_or_nasdaq():
    """Önce mevcut tam evreni okur, Z-K aralığını filtreler. Yoksa NASDAQ'tan indirir."""
    if os.path.exists(UNIVERSE_FILE):
        with open(UNIVERSE_FILE) as f:
            return [line.strip() for line in f if line.strip()]

    # Mevcut tam evren dosyası varsa onu kullan, yoksa NASDAQ'tan oluştur
    full_universe = "/app/data_prep/us_stock_universe.txt"
    if os.path.exists(full_universe):
        with open(full_universe) as f:
            all_symbols = [line.strip() for line in f if line.strip()]
    else:
        import urllib.request
        url = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt"
        urllib.request.urlretrieve(url, "/tmp/nasdaqtraded.txt")
        with open("/tmp/nasdaqtraded.txt") as f:
            lines = f.readlines()[1:]
        all_symbols = []
        for line in lines:
            parts = line.split('|')
            if len(parts) > 2:
                ticker = parts[1].strip()
                etf = parts[2].strip()
                if ticker and etf == 'N':
                    all_symbols.append(ticker)

    # Z-K filtrele
    filtered = [s for s in all_symbols if s and s[0] in LETTERS]
    filtered = sorted(filtered, reverse=True)

    os.makedirs(os.path.dirname(UNIVERSE_FILE), exist_ok=True)
    with open(UNIVERSE_FILE, "w") as f:
        f.write("\n".join(filtered))
    return filtered


def fetch_ticker(ticker: str, api_key: str):
    try:
        resp = httpx.get(
            f"https://api.tiingo.com/tiingo/daily/{ticker}/prices",
            params={"startDate": START_DATE, "token": api_key},
            timeout=30.0,
        )
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        return None


def write_qlib_csv(ticker: str, data: list):
    ticker_dir = Path(OUTPUT_DIR) / ticker
    ticker_dir.mkdir(parents=True, exist_ok=True)
    path = ticker_dir / f"{ticker}.csv"
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "open", "close", "high", "low", "volume", "factor"])
        for row in data:
            # Qlib için düzeltilmiş fiyatları yaz, factor=1
            adj_open = row.get("adjOpen", row.get("open"))
            adj_close = row.get("adjClose", row.get("close"))
            adj_high = row.get("adjHigh", row.get("high"))
            adj_low = row.get("adjLow", row.get("low"))
            adj_volume = row.get("adjVolume", row.get("volume"))
            writer.writerow([
                row["date"][:10],
                adj_open,
                adj_close,
                adj_high,
                adj_low,
                adj_volume,
                1.0
            ])


def run():
    keys = get_tiingo_keys()
    if not keys:
        print("HATA: Hic Tiingo anahtari bulunamadi")
        return

    universe = create_universe_from_existing_or_nasdaq()
    progress = load_progress()
    done = set(progress["completed"]) | set(progress["failed"])
    remaining = [t for t in universe if t not in done]

    print(f"Toplam Z-K evreni: {len(universe)}")
    print(f"Tamamlanan: {len(progress['completed'])}, Kalan: {len(remaining)}")
    print(f"Kullanilacak anahtar sayisi: {len(keys)}")

    key_index = 0
    delay_seconds = 3600 / (len(keys) * REQUESTS_PER_KEY_PER_HOUR)

    for i, ticker in enumerate(remaining):
        api_key = keys[key_index % len(keys)]
        key_index += 1

        data = fetch_ticker(ticker, api_key)
        if data and isinstance(data, list) and len(data) > 0:
            write_qlib_csv(ticker, data)
            progress["completed"].append(ticker)
        else:
            progress["failed"].append(ticker)

        if (i + 1) % 20 == 0:
            save_progress(progress)

        time.sleep(delay_seconds)

    save_progress(progress)
    print("Tamamlandi.")


if __name__ == "__main__":
    run()
