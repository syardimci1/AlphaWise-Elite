"""
ALPHAWISE - 20 Gunluk Ufuk Testi (15.08.2026)
Hipotez: 1-2 gunluk getiri tahmini gurultuye cok yakin (kanitlandi:
neredeyse sifir/negatif sinyal). 20 gunluk (aylik) getiri, gercek
trendleri gurultuden ayirabilir. Ayni Alpha158+LightGBM, SADECE
etiket (label) degisiyor.
"""
import qlib
from qlib.constant import REG_US
from qlib.contrib.data.handler import Alpha158
from qlib.data.dataset import DatasetH
import pandas as pd, numpy as np, lightgbm as lgb
import pickle, os, gc

qlib.init(provider_uri='/app/qlib_bin_data/us_data', region=REG_US, kernels=2)

START, END, FIT_END, VALID_END = "2020-01-01", "2026-08-14", "2025-12-31", "2026-04-30"
CUSTOM_LABEL = ["Ref($close, -21)/Ref($close, -1) - 1"]
LABEL_NAMES = ["LABEL0"]

print("Alpha158 + 20-GUNLUK ETIKET hesaplaniyor...", flush=True)
handler = Alpha158(
    start_time=START, end_time=END, fit_start_time=START, fit_end_time=FIT_END,
    instruments="all", label=(CUSTOM_LABEL, LABEL_NAMES),
)
df = handler.fetch(col_set=["feature", "label"])
for c in df.select_dtypes(include=["float64"]).columns:
    df[c] = df[c].astype("float32")
print(f"Toplam satir: {len(df)}", flush=True)

dates = df.index.get_level_values(0)
tr, va, te = dates <= FIT_END, (dates > FIT_END) & (dates <= VALID_END), dates > VALID_END
Xtr, ytr = df[tr]["feature"], df[tr]["label"].iloc[:, 0]
Xva, yva = df[va]["feature"], df[va]["label"].iloc[:, 0]
Xte, yte = df[te]["feature"], df[te]["label"].iloc[:, 0]
test_dates = df[te].index.get_level_values(0)
m_tr, m_va = ytr.notna(), yva.notna()
Xtr, ytr = Xtr[m_tr], ytr[m_tr]
Xva, yva = Xva[m_va], yva[m_va]
del df; gc.collect()
print(f"Egitim: {len(Xtr)} | Dogrulama: {len(Xva)} | Test: {len(Xte)}", flush=True)

print("LightGBM egitiliyor...", flush=True)
model = lgb.train(
    {"objective": "regression", "num_leaves": 64, "learning_rate": 0.05,
     "feature_fraction": 0.8, "bagging_fraction": 0.8, "bagging_freq": 5,
     "min_data_in_leaf": 50, "verbose": -1},
    lgb.Dataset(Xtr, label=ytr), num_boost_round=500,
    valid_sets=[lgb.Dataset(Xva, label=yva)],
    callbacks=[lgb.early_stopping(50, verbose=False)],
)

pred = model.predict(Xte)
ev = pd.DataFrame({"date": test_dates, "pred": pred, "label": yte.to_numpy()}).dropna()
pooled = np.corrcoef(ev["pred"], ev["label"])[0, 1]
daily = ev.groupby("date").apply(lambda g: pd.Series({
    "ic": g["pred"].corr(g["label"]) if len(g) > 5 else np.nan,
    "ric": g["pred"].corr(g["label"], method="spearman") if len(g) > 5 else np.nan,
})).dropna()
ic_mean, ic_std = daily["ic"].mean(), daily["ic"].std()
ric_mean = daily["ric"].mean()
hit = (daily["ic"] > 0).mean()

print("\n" + "=" * 60, flush=True)
print("SONUC - ABD Alpha158, 20-GUNLUK UFUK", flush=True)
print("-" * 60, flush=True)
print(f"Havuzlanmis IC     : {pooled:.5f}", flush=True)
print(f"Gunluk kesitsel IC : {ic_mean:.5f} (std {ic_std:.4f})", flush=True)
print(f"Rank IC            : {ric_mean:.5f}", flush=True)
print(f"Pozitif gun orani  : {hit:.1%}", flush=True)
print(f"Test gunu sayisi   : {len(daily)}", flush=True)
print("-" * 60, flush=True)
print(f"KARSILASTIRMA -> 1-2 gunluk ufuk: IC=0.00456, Rank IC=-0.03584, %44.9 pozitif", flush=True)
print("=" * 60, flush=True)
