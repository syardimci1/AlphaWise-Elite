"""
ALPHAWISE - Toplu BIST Hisse Veri Cekme (yfinance, .IS uzantisi)
622 BIST hissesi icin 5 yillik veri, ABD'deki bulk_fetch.py ile AYNI
dayanikli mimari: ilerleme kaydi, kesintide devam, kalici volume.
Kaynak: yfinance (resmi, herkese acik Yahoo Finance verisi, .IS = Istanbul).
"""
import os
import csv
import json
import time
import yfinance as yf
from datetime import datetime, timezone

UNIVERSE_FILE = "/app/data_prep/bist_universe.txt"
OUTPUT_DIR = "/app/csv_data/bist_data"
PROGRESS_FILE = "/app/csv_data/progress_bist.json"
DELAY_SECONDS = 2  # yfinance'e nazik davran, rate-limit yok ama saygili olalim


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"completed": [], "failed": []}


def save_progress(progress):
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f)


def fetch_ticker(ticker: str):
    try:
        yf_ticker = f"{ticker}.IS"
        data = yf.download(yf_ticker, start="2020-01-01", progress=False, auto_adjust=False)
        if data is None or data.empty:
            return None
        return data
    except Exception:
        return None


def write_qlib_csv(ticker: str, df):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = f"{OUTPUT_DIR}/{ticker}.csv"
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "open", "close", "high", "low", "volume", "factor"])
        for date, row in df.iterrows():
            try:
                close = float(row["Close"].iloc[0]) if hasattr(row["Close"], "iloc") else float(row["Close"])
                adj_close = float(row["Adj Close"].iloc[0]) if hasattr(row["Adj Close"], "iloc") else float(row["Adj Close"])
                factor = round(adj_close / close, 8) if close else 1.0
                writer.writerow([
                    date.strftime("%Y-%m-%d"),
                    float(row["Open"].iloc[0]) if hasattr(row["Open"], "iloc") else float(row["Open"]),
                    adj_close,
                    float(row["High"].iloc[0]) if hasattr(row["High"], "iloc") else float(row["High"]),
                    float(row["Low"].iloc[0]) if hasattr(row["Low"], "iloc") else float(row["Low"]),
                    float(row["Volume"].iloc[0]) if hasattr(row["Volume"], "iloc") else float(row["Volume"]),
                    factor,
                ])
            except Exception:
                continue


def run():
    with open(UNIVERSE_FILE) as f:
        universe = [line.strip() for line in f if line.strip()]

    progress = load_progress()
    done = set(progress["completed"]) | set(progress["failed"])
    remaining = [t for t in universe if t not in done]

    print(f"Toplam BIST evreni: {len(universe)}, Tamamlanan: {len(progress['completed'])}, Kalan: {len(remaining)}")

    for i, ticker in enumerate(remaining):
        df = fetch_ticker(ticker)
        if df is not None and not df.empty:
            write_qlib_csv(ticker, df)
            progress["completed"].append(ticker)
        else:
            progress["failed"].append(ticker)

        if (i + 1) % 20 == 0:
            save_progress(progress)
            print(f"[{datetime.now(timezone.utc).isoformat()}] {i+1}/{len(remaining)} islendi "
                  f"(basarili: {len(progress['completed'])}, basarisiz: {len(progress['failed'])})")

        time.sleep(DELAY_SECONDS)

    save_progress(progress)
    print(f"TAMAMLANDI. Basarili: {len(progress['completed'])}, Basarisiz: {len(progress['failed'])}")


if __name__ == "__main__":
    run()
