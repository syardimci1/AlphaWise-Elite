"""
ALPHAWISE - defeatbeta-api ile ABD hisseleri veri toplama (16.08.2026)
Gercek Yahoo Finance verisi (Hugging Face uzerinden), API anahtari
gerektirmiyor, rate limit yok. FMP/Tiingo'nun kapsayamadigi sembolleri
(CFR gibi) basariyla getirdi (7979 satir, 1994'ten bugune).
"""
from defeatbeta_api.data.ticker import Ticker
import json, os

PROGRESS_FILE = "/app/csv_data/progress.json"
DATA_DIR = "/app/csv_data/us_data"

with open(PROGRESS_FILE) as f:
    progress = json.load(f)

with open("/app/data_prep/us_stock_universe.txt") as f:
    all_tickers = set(line.strip() for line in f if line.strip())

already_done = set(progress["completed"])
to_fetch = sorted(all_tickers - already_done)

print(f"Toplam evren: {len(all_tickers)} | Zaten tamamlanan: {len(already_done)} | Denenecek: {len(to_fetch)}", flush=True)

completed_now = []
still_failed = []

for i, ticker in enumerate(to_fetch):
    try:
        t = Ticker(ticker)
        df = t.price()
        if df is None or len(df) == 0:
            still_failed.append(ticker)
            continue

        df = df.rename(columns={"report_date": "date"})
        df["factor"] = 1.0
        df = df[["date", "open", "high", "low", "close", "volume", "factor"]]
        df.to_csv(f"{DATA_DIR}/{ticker}.csv", index=False)
        completed_now.append(ticker)

    except Exception:
        still_failed.append(ticker)

    if (i + 1) % 50 == 0:
        progress["completed"] = list(set(progress["completed"]) | set(completed_now))
        progress["failed"] = still_failed
        with open(PROGRESS_FILE, "w") as f:
            json.dump(progress, f)
        print(f"  {i+1}/{len(to_fetch)} islendi | toplam basarili: {len(progress['completed'])}", flush=True)

progress["completed"] = list(set(progress["completed"]) | set(completed_now))
progress["failed"] = still_failed
with open(PROGRESS_FILE, "w") as f:
    json.dump(progress, f)

print(f"\nTAMAMLANDI. Bu turda ek basarili: {len(completed_now)}", flush=True)
print(f"TOPLAM tamamlanan: {len(progress['completed'])}", flush=True)
