"""
ALPHAWISE - Toplu ABD Hisse Veri Cekme (dayanikli, cok-anahtarli)
7111 hisse icin 5 yillik veri Tiingo'dan cekilir, Qlib CSV formatina cevrilir.
- Kac TIINGO_TOKEN_N anahtari varsa OTOMATIK algilar, hiza gore olceklenir
- ILERLEME KAYDEDILIR (progress.json) - kesinti olursa kaldigi yerden devam eder
- Her anahtar icin 50/saat siniri round-robin ile paylastirilir
"""
import os
import csv
import json
import time
import httpx
from datetime import datetime, timezone

UNIVERSE_FILE = "/app/data_prep/us_stock_universe.txt"
OUTPUT_DIR = "/app/csv_data/us_data"
PROGRESS_FILE = "/app/csv_data/progress.json"
REQUESTS_PER_KEY_PER_HOUR = 45  # 50'nin altinda tutuyoruz, guvenlik payi

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


def fetch_ticker(ticker: str, api_key: str):
    try:
        resp = httpx.get(
            f"https://api.tiingo.com/tiingo/daily/{ticker}/prices",
            params={"startDate": "2020-01-01", "token": api_key},
            timeout=30.0,
        )
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        return None


def write_qlib_csv(ticker: str, data: list):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = f"{OUTPUT_DIR}/{ticker}.csv"
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


def run():
    keys = get_tiingo_keys()
    if not keys:
        print("HATA: Hic Tiingo anahtari bulunamadi")
        return

    with open(UNIVERSE_FILE) as f:
        universe = [line.strip() for line in f if line.strip()]

    progress = load_progress()
    done = set(progress["completed"]) | set(progress["failed"])
    remaining = [t for t in universe if t not in done]

    print(f"Toplam: {len(universe)}, Tamamlanan: {len(progress['completed'])}, Kalan: {len(remaining)}")
    print(f"Kullanilan anahtar sayisi: {len(keys)} ({len(keys) * REQUESTS_PER_KEY_PER_HOUR}/saat)")

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
            print(f"[{datetime.now(timezone.utc).isoformat()}] {i+1}/{len(remaining)} islendi "
                  f"(basarili: {len(progress['completed'])}, basarisiz: {len(progress['failed'])})")

        time.sleep(delay_seconds)

    save_progress(progress)
    print(f"TAMAMLANDI. Basarili: {len(progress['completed'])}, Basarisiz: {len(progress['failed'])}")


if __name__ == "__main__":
    run()
