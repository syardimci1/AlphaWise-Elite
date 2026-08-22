"""
ALPHAWISE - Likit Olmayan Sembolleri Filtreleme (16.08.2026 - v4, Polars)
"""
import polars as pl
import os

DATA_DIR = "/app/csv_data/us_data"
LOG_DIR = "/app/csv_data"
MIN_AVG_VOLUME = 1000

silinecek = []
kontrol_edilen = 0

for fname in os.listdir(DATA_DIR):
    if not fname.endswith(".csv"):
        continue
    kontrol_edilen += 1
    try:
        df = pl.read_csv(f"{DATA_DIR}/{fname}")
        son60 = df.tail(60)
        ort_hacim = son60["volume"].mean()
        if ort_hacim is not None and ort_hacim < MIN_AVG_VOLUME:
            silinecek.append((fname, ort_hacim))
    except Exception as e:
        print(f"HATA ({fname}): {type(e).__name__}: {e}", flush=True)
        continue

print(f"Kontrol edilen: {kontrol_edilen}", flush=True)
print(f"Likit olmayan (silinecek): {len(silinecek)}", flush=True)
print("Ornekler:", silinecek[:10], flush=True)

with open(f"{LOG_DIR}/illiquid_removed_list.txt", "w") as f:
    for fname, vol in silinecek:
        f.write(f"{fname},{vol}\n")

for fname, _ in silinecek:
    os.remove(f"{DATA_DIR}/{fname}")

print(f"\n{len(silinecek)} dosya silindi. Kalan: {kontrol_edilen - len(silinecek)}", flush=True)
