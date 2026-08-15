import qlib
from qlib.constant import REG_US
from qlib.contrib.data.handler import Alpha158
from qlib.data.dataset import DatasetH
import numpy as np
import pickle

qlib.init(provider_uri='/app/qlib_bin_data/us_data', region=REG_US, kernels=2)

handler = Alpha158(
    start_time="2020-01-01", end_time="2026-08-14",
    fit_start_time="2020-01-01", fit_end_time="2025-12-31",
    instruments="all",
)
dataset = DatasetH(handler, segments={
    "train": ("2020-01-01", "2025-12-31"),
    "valid": ("2026-01-01", "2026-04-30"),
    "test": ("2026-05-01", "2026-08-14"),
})

with open("/app/models/lightgbm_alpha158_us.pkl", "rb") as f:
    model = pickle.load(f)

pred = model.predict(dataset, segment="test")
label = dataset.prepare("test", col_set="label")["LABEL0"]

print(f"Tahmin sayisi: {len(pred)}, NaN tahmin sayisi: {pred.isna().sum()}")
print(f"Etiket sayisi: {len(label)}, NaN etiket sayisi: {label.isna().sum()}")
