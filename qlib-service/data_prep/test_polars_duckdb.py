"""GERCEK veri uzerinde Polars/DuckDB vs Pandas karsilastirmasi."""
import time, os, glob
import pandas as pd, polars as pl, duckdb

CSV_DIR = "/app/csv_data/us_data"
files = sorted(glob.glob(f"{CSV_DIR}/*.csv"))[:300]
print(f"Test dosyasi: {len(files)} gercek hisse CSV'si\n", flush=True)

def mem_mb(df):
    if isinstance(df, pd.DataFrame): return df.memory_usage(deep=True).sum()/1e6
    return df.estimated_size("mb")

# --- PANDAS (mevcut yontem) ---
t = time.time()
pdf = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
t_pandas, m_pandas = time.time()-t, mem_mb(pdf)
print(f"PANDAS  : {t_pandas:6.2f} sn | {m_pandas:8.1f} MB | {len(pdf):,} satir", flush=True)

# --- POLARS (yeni) ---
t = time.time()
ldf = pl.concat([pl.read_csv(f, infer_schema_length=1000) for f in files])
t_polars, m_polars = time.time()-t, mem_mb(ldf)
print(f"POLARS  : {t_polars:6.2f} sn | {m_polars:8.1f} MB | {len(ldf):,} satir", flush=True)

# --- DUCKDB (bellege hic almadan, diskten dogrudan SQL) ---
t = time.time()
res = duckdb.sql(f"SELECT COUNT(*) c, AVG(close) a FROM read_csv_auto('{CSV_DIR}/*.csv')").fetchone()
t_duck = time.time()-t
print(f"DUCKDB  : {t_duck:6.2f} sn | ~0 MB (bellek disi) | {res[0]:,} satir (TUM dosyalar!)", flush=True)

print(f"\nKAZANIM: Polars pandas'tan {t_pandas/t_polars:.1f}x hizli, "
      f"bellek {(1-m_polars/m_pandas)*100:.0f}% daha az", flush=True)
print(f"DUCKDB: {len(glob.glob(f'{CSV_DIR}/*.csv')):,} dosyayi belleğe HIC almadan sorguladi", flush=True)
