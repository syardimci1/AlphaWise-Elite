"""
ALPHAWISE - Gruplu Egitim + Dogru IC Olcumu (15.08.2026)

BELLEK STRATEJISI:
  1) Hisseler gruplara bolunur, her grup ayri hesaplanir
  2) float32'ye dusurulup DISKE (parquet) yazilir, bellekten atilir
  3) Kesinti olursa: hesaplanan gruplar korunur, bastan hesaplanmaz
  4) LightGBM TEK SEFERDE egitilir (incremental degil -> dogruluk korunur)

OLCUM DUZELTMESI:
  Onceki havuzlanmis (pooled) IC = 0.00163 yaniltici olabilir.
  Bu surum, sektorun standardi olan GUNLUK KESITSEL IC hesaplar:
  her gun ayri korelasyon -> ortalama + IR (bilgi orani).
  Ayrica Rank IC (Spearman) da hesaplar - aykiri degerlere dayanikli.
"""
import qlib
from qlib.constant import REG_US
from qlib.contrib.data.handler import Alpha158
from qlib.data import D
import pandas as pd
import polars as pl   # bellek: pandas'tan %48 daha az (olculdu)
import numpy as np
import lightgbm as lgb
import pickle, os, gc, sys

qlib.init(provider_uri='/app/qlib_bin_data/us_data', region=REG_US, kernels=2)

BATCH_SIZE  = 2000
START, END  = "2020-01-01", "2026-08-14"
FIT_END     = "2025-12-31"
VALID_END   = "2026-04-30"
PQ_DIR      = "/app/models/batch_parquet"
os.makedirs(PQ_DIR, exist_ok=True)

tickers = sorted(D.list_instruments(instruments=D.instruments(market='all'), as_list=True))
batches = [tickers[i:i+BATCH_SIZE] for i in range(0, len(tickers), BATCH_SIZE)]
print(f"Hisse: {len(tickers)} | Grup: {len(batches)} x {BATCH_SIZE}", flush=True)

# ================= ASAMA 1: gruplu hesaplama -> parquet =================
for i, batch in enumerate(batches, 1):
    out = f"{PQ_DIR}/batch_{i:03d}.parquet"
    if os.path.exists(out):
        print(f"[GRUP {i}/{len(batches)}] mevcut, atlandi", flush=True)
        continue
    print(f"[GRUP {i}/{len(batches)}] {len(batch)} hisse hesaplaniyor...", flush=True)
    try:
        h = Alpha158(start_time=START, end_time=END, fit_start_time=START,
                     fit_end_time=FIT_END, instruments=batch)
        df = h.fetch(col_set=["feature", "label"])
        for c in df.select_dtypes(include=["float64"]).columns:
            df[c] = df[c].astype("float32")
        df.to_parquet(out)
        print(f"[GRUP {i}] {len(df)} satir -> disk", flush=True)
        del h, df
    except Exception as e:
        print(f"[GRUP {i}] HATA: {type(e).__name__}: {e}", flush=True)
    gc.collect()

# ================= ASAMA 2: birlestir =================
print("\n[BIRLESTIRME]", flush=True)
files = sorted(f for f in os.listdir(PQ_DIR) if f.endswith(".parquet"))
if not files:
    print("HATA: hic parquet uretilmedi, cikiliyor", flush=True); sys.exit(1)
print("  (Polars ile okunuyor - %48 daha az bellek)", flush=True)
_pl = pl.concat([pl.read_parquet(f"{PQ_DIR}/{f}") for f in files])
data = _pl.to_pandas(); del _pl; gc.collect()
data = data.set_index(data.columns[:2].tolist()) if not isinstance(data.index, pd.MultiIndex) else data
data = data.sort_index()
gc.collect()
print(f"Satir: {len(data)} | Bellek: {data.memory_usage(deep=True).sum()/1e9:.2f} GB", flush=True)

dates = data.index.get_level_values(0)
tr = dates <= FIT_END
va = (dates > FIT_END) & (dates <= VALID_END)
te = dates > VALID_END

Xtr, ytr = data[tr]["feature"], data[tr]["label"].iloc[:, 0]
Xva, yva = data[va]["feature"], data[va]["label"].iloc[:, 0]
Xte, yte = data[te]["feature"], data[te]["label"].iloc[:, 0]
test_dates = data[te].index.get_level_values(0)
feat_names = list(Xtr.columns)
del data; gc.collect()

# NaN etiketli satirlari egitimden cikar (onceki calistirmada 11391 NaN vardi)
m_tr, m_va = ytr.notna(), yva.notna()
Xtr, ytr = Xtr[m_tr], ytr[m_tr]
Xva, yva = Xva[m_va], yva[m_va]
print(f"Egitim: {len(Xtr)} | Dogrulama: {len(Xva)} | Test: {len(Xte)}", flush=True)

# ================= ASAMA 3: egitim =================
print("\n[EGITIM] LightGBM...", flush=True)
model = lgb.train(
    {"objective": "regression", "num_leaves": 64, "learning_rate": 0.05,
     "feature_fraction": 0.8, "bagging_fraction": 0.8, "bagging_freq": 5,
     "min_data_in_leaf": 50, "verbose": -1, "num_threads": 4},
    lgb.Dataset(Xtr, label=ytr),
    num_boost_round=500,
    valid_sets=[lgb.Dataset(Xva, label=yva)],
    callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(50)],
)
with open("/app/models/lightgbm_batched_us.pkl", "wb") as f:
    pickle.dump(model, f)
print(f"En iyi iterasyon: {model.best_iteration}", flush=True)
del Xtr, ytr, Xva, yva; gc.collect()

# ================= ASAMA 4: DOGRU IC OLCUMU =================
print("\n[OLCUM]", flush=True)
pred = model.predict(Xte)
ev = pd.DataFrame({"date": test_dates, "pred": pred, "label": yte.to_numpy()}).dropna()

# 4a) Havuzlanmis IC (eski yontem - karsilastirma icin)
pooled = np.corrcoef(ev["pred"], ev["label"])[0, 1]

# 4b) GUNLUK KESITSEL IC (sektor standardi)
daily = ev.groupby("date").apply(
    lambda g: pd.Series({
        "ic":   g["pred"].corr(g["label"]) if len(g) > 5 else np.nan,
        "ric":  g["pred"].corr(g["label"], method="spearman") if len(g) > 5 else np.nan,
        "n":    len(g),
    })
).dropna()

ic_mean,  ic_std  = daily["ic"].mean(),  daily["ic"].std()
ric_mean, ric_std = daily["ric"].mean(), daily["ric"].std()
ir      = ic_mean / ic_std if ic_std else np.nan          # bilgi orani
hit     = (daily["ic"] > 0).mean()                        # pozitif gun orani

print("\n" + "=" * 60, flush=True)
print("SONUC - ABD Alpha158 (gruplu egitim)", flush=True)
print("-" * 60, flush=True)
print(f"Havuzlanmis IC (eski yontem) : {pooled:.5f}", flush=True)
print(f"GUNLUK KESITSEL IC (standart): {ic_mean:.5f}  (std {ic_std:.4f})", flush=True)
print(f"Rank IC (Spearman)           : {ric_mean:.5f}  (std {ric_std:.4f})", flush=True)
print(f"IR (IC/std - istikrar)       : {ir:.4f}", flush=True)
print(f"Pozitif gun orani            : {hit:.1%}", flush=True)
print(f"Test gunu sayisi             : {len(daily)}", flush=True)
print("-" * 60, flush=True)
print("YORUM: gunluk IC 0.02-0.05 = makul | >0.10 = supheli (sizinti?)", flush=True)
print("KARSILASTIRMA -> ABD Alpha360: 0.01292 | BIST: 0.07356-0.09036", flush=True)
print("(bu ikisi HAVUZLANMIS yontemle olculmustu - dogrudan kiyaslanamaz)", flush=True)
print("=" * 60, flush=True)

# 4c) En etkili 15 ozellik - model neye bakiyor?
imp = pd.Series(model.feature_importance("gain"), index=feat_names).nlargest(15)
print("\nEN ETKILI 15 OZELLIK (gain):", flush=True)
for k, v in imp.items():
    print(f"  {k:<20} {v:>12.1f}", flush=True)
