"""
ALPHAWISE - Model B vs Model C: Gercek IC (Information Coefficient) Karsilastirmasi
IC = tahmin ile gerceklesen getiri arasindaki korelasyon.
Yuksek IC = gercek ongoru gucu. Sifira yakin = rastgele tahmin.
"""
import qlib
from qlib.constant import REG_US
from qlib.contrib.data.handler import Alpha360
from qlib.data.dataset.loader import NestedDataLoader
from qlib.data.dataset.handler import DataHandlerLP
from qlib.data.dataset import DatasetH
import pickle
import numpy as np

qlib.init(provider_uri='/app/qlib_bin_data/us_data', region=REG_US)

# --- Model B icin dataset (Alpha360) ---
handler_b = Alpha360(
    start_time="2020-01-01", end_time="2026-08-10",
    fit_start_time="2020-01-01", fit_end_time="2025-06-30",
    instruments="all",
)
dataset_b = DatasetH(handler_b, segments={
    "train": ("2020-01-01", "2025-06-30"),
    "valid": ("2025-07-01", "2025-12-31"),
    "test": ("2026-01-01", "2026-08-10"),
})

with open("/app/models/lightgbm_alpha360.pkl", "rb") as f:
    model_b = pickle.load(f)

pred_b = model_b.predict(dataset_b, segment="test")
label_b = dataset_b.prepare("test", col_set="label")["LABEL0"]

common_idx_b = pred_b.index.intersection(label_b.index)
ic_b = np.corrcoef(pred_b.loc[common_idx_b], label_b.loc[common_idx_b])[0, 1]

print(f"MODEL B (Alpha360) IC: {ic_b:.5f}")
print(f"Model B tahmin sayisi: {len(pred_b)}, ortak (label'li) satir: {len(common_idx_b)}")

# --- Model C icin dataset (Alpha158 + Ozel) ---
print("\n--- Model C hesaplaniyor ---")
custom_fields = [
    "(EMA($close, 12) - EMA($close, 26))",
    "EMA((EMA($close, 12) - EMA($close, 26)), 9)",
    "Mean(Abs($high - $low), 14)",
    "($close - Min($low, 20)) / (Max($high, 20) - Min($low, 20) + 1e-12)",
]
custom_names = ["CUSTOM_MACD", "CUSTOM_MACD_SIGNAL", "CUSTOM_ATR", "CUSTOM_PRICE_POSITION"]

nd = NestedDataLoader(
    dataloader_l=[
        {"class": "qlib.contrib.data.loader.Alpha158DL"},
        {"class": "qlib.data.dataset.loader.QlibDataLoader",
         "kwargs": {"config": {"feature": (custom_fields, custom_names),
                                "label": (["Ref($close, -2)/Ref($close, -1) - 1"], ["LABEL0"])}}},
    ]
)
handler_c = DataHandlerLP(
    instruments="all", start_time="2020-01-01", end_time="2026-08-10", data_loader=nd,
    infer_processors=[
        {"class": "RobustZScoreNorm", "kwargs": {"fields_group": "feature", "clip_outlier": True, "fit_start_time": "2020-01-01", "fit_end_time": "2025-06-30"}},
        {"class": "Fillna", "kwargs": {"fields_group": "feature"}},
    ],
    learn_processors=[{"class": "DropnaLabel"}, {"class": "CSZScoreNorm", "kwargs": {"fields_group": "label"}}],
)
dataset_c = DatasetH(handler_c, segments={
    "train": ("2020-01-01", "2025-06-30"), "valid": ("2025-07-01", "2025-12-31"), "test": ("2026-01-01", "2026-08-10"),
})

with open("/app/models/lightgbm_custom.pkl", "rb") as f:
    model_c = pickle.load(f)

pred_c = model_c.predict(dataset_c, segment="test")
label_c = dataset_c.prepare("test", col_set="label")["LABEL0"]
common_idx_c = pred_c.index.intersection(label_c.index)
ic_c = np.corrcoef(pred_c.loc[common_idx_c], label_c.loc[common_idx_c])[0, 1]

print(f"MODEL C (Alpha158+Ozel) IC: {ic_c:.5f}")
print(f"Model C tahmin sayisi: {len(pred_c)}, ortak (label'li) satir: {len(common_idx_c)}")

# --- Model C icin dataset (Alpha158 + Ozel) ---
print("\n--- Model C hesaplaniyor ---")
custom_fields = [
    "(EMA($close, 12) - EMA($close, 26))",
    "EMA((EMA($close, 12) - EMA($close, 26)), 9)",
    "Mean(Abs($high - $low), 14)",
    "($close - Min($low, 20)) / (Max($high, 20) - Min($low, 20) + 1e-12)",
]
custom_names = ["CUSTOM_MACD", "CUSTOM_MACD_SIGNAL", "CUSTOM_ATR", "CUSTOM_PRICE_POSITION"]

nd = NestedDataLoader(
    dataloader_l=[
        {"class": "qlib.contrib.data.loader.Alpha158DL"},
        {"class": "qlib.data.dataset.loader.QlibDataLoader",
         "kwargs": {"config": {"feature": (custom_fields, custom_names),
                                "label": (["Ref($close, -2)/Ref($close, -1) - 1"], ["LABEL0"])}}},
    ]
)
handler_c = DataHandlerLP(
    instruments="all", start_time="2020-01-01", end_time="2026-08-10", data_loader=nd,
    infer_processors=[
        {"class": "RobustZScoreNorm", "kwargs": {"fields_group": "feature", "clip_outlier": True, "fit_start_time": "2020-01-01", "fit_end_time": "2025-06-30"}},
        {"class": "Fillna", "kwargs": {"fields_group": "feature"}},
    ],
    learn_processors=[{"class": "DropnaLabel"}, {"class": "CSZScoreNorm", "kwargs": {"fields_group": "label"}}],
)
dataset_c = DatasetH(handler_c, segments={
    "train": ("2020-01-01", "2025-06-30"), "valid": ("2025-07-01", "2025-12-31"), "test": ("2026-01-01", "2026-08-10"),
})

with open("/app/models/lightgbm_custom.pkl", "rb") as f:
    model_c = pickle.load(f)

pred_c = model_c.predict(dataset_c, segment="test")
label_c = dataset_c.prepare("test", col_set="label")["LABEL0"]
common_idx_c = pred_c.index.intersection(label_c.index)
ic_c = np.corrcoef(pred_c.loc[common_idx_c], label_c.loc[common_idx_c])[0, 1]

print(f"MODEL C (Alpha158+Ozel) IC: {ic_c:.5f}")
print(f"Model C tahmin sayisi: {len(pred_c)}, ortak (label'li) satir: {len(common_idx_c)}")
