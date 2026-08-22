"""
ALPHAWISE - Artimli Veri Guncelleme (16.08.2026 - v3, Polars)
Tarih karsilastirmasi Polars'in kendi datetime tipiyle DEGIL, guvenli
string->Python datetime cevrimiyle yapilir (Polars/pandas datetime
etkilesiminde sessiz hata riskini onlemek icin).
"""
import polars as pl
import pandas as pd  # sadece defeatbeta_api'nin pandas DataFrame donmesi icin
import json, os
from datetime import datetime

PROGRESS_FILE = "/app/csv_data/progress.json"
DATA_DIR = "/app/csv_data/us_data"

with open(PROGRESS_FILE) as f:
    progress = json.load(f)

completed = progress["completed"]
print(f"Artimli guncelleme icin kontrol edilecek: {len(completed)} hisse", flush=True)

guncellenen = 0
zaten_guncel = 0
hata = 0

for i, ticker in enumerate(completed):
    csv_path = f"{DATA_DIR}/{ticker}.csv"
    if not os.path.exists(csv_path):
        continue
    try:
        mevcut = pl.read_csv(csv_path)
        if mevcut.is_empty():
            continue

        son_tarih_str = str(mevcut["date"].max())
        son_tarih = datetime.strptime(son_tarih_str[:10], "%Y-%m-%d")

        if (datetime.now() - son_tarih).days <= 2:
            zaten_guncel += 1
            continue

        from defeatbeta_api.data.ticker import Ticker
        t = Ticker(ticker)
        yeni = t.price()
        if yeni is None or yeni.empty:
            continue
        yeni = yeni.rename(columns={"report_date": "date"})
        yeni["date"] = pd.to_datetime(yeni["date"])
        yeni["factor"] = 1.0
        yeni = yeni[yeni["date"] > son_tarih][["date", "open", "high", "low", "close", "volume", "factor"]]

        if len(yeni) > 0:
            yeni.to_csv(csv_path, mode="a", header=False, index=False)
            guncellenen += 1

    except Exception as e:
        print(f"HATA ({ticker}): {type(e).__name__}: {e}", flush=True)
        hata += 1
        continue

    if (i + 1) % 500 == 0:
        print(f"  {i+1}/{len(completed)} kontrol edildi | guncellenen: {guncellenen}", flush=True)

print(f"\nTAMAMLANDI. Guncellenen: {guncellenen} | Zaten guncel: {zaten_guncel} | Hata: {hata}", flush=True)
