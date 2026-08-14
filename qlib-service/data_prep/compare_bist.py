"""BIST modelinin gercek IC'sini hesaplar."""
import qlib
from qlib.constant import REG_US
from qlib.contrib.data.handler import Alpha360
from qlib.data.dataset import DatasetH
import pickle
import numpy as np

qlib.init(provider_uri='/app/qlib_bin_data/bist_data', region=REG_US)

handler = Alpha360(
    start_time="2020-01-01", end_time="2026-08-13",
    fit_start_time="2020-01-01", fit_end_time="2025-12-31",
    instruments="all",
)
dataset = DatasetH(handler, segments={
    "train": ("2020-01-01", "2025-12-31"),
    "valid": ("2026-01-01", "2026-04-30"),
    "test": ("2026-05-01", "2026-08-13"),
})

with open("/app/models/lightgbm_bist.pkl", "rb") as f:
    model = pickle.load(f)

pred = model.predict(dataset, segment="test")
label = dataset.prepare("test", col_set="label")["LABEL0"]

common_idx = pred.index.intersection(label.index)
ic = np.corrcoef(pred.loc[common_idx], label.loc[common_idx])[0, 1]

print(f"BIST MODEL IC: {ic:.5f}")
print(f"Tahmin sayisi: {len(pred)}, ortak satir: {len(common_idx)}")
