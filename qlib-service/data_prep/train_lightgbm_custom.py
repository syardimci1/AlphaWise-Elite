"""
ALPHAWISE - Model C: LightGBM + Alpha158 + Ozel TAA Faktorleri
NestedDataLoader ile (Qlib'in resmi belgelenmis yontemi) Alpha158'in
faktorlerini ozel MACD/ATR/fiyat-pozisyon faktorleriyle birlestirir.
"""
import qlib
from qlib.constant import REG_US
from qlib.contrib.model.gbdt import LGBModel
from qlib.data.dataset.loader import NestedDataLoader
from qlib.data.dataset.handler import DataHandlerLP
from qlib.data.dataset import DatasetH
import pickle
import os

qlib.init(provider_uri='/app/qlib_bin_data/us_data', region=REG_US, kernels=1)

custom_fields = [
    "(EMA($close, 12) - EMA($close, 26))",
    "EMA((EMA($close, 12) - EMA($close, 26)), 9)",
    "Mean(Abs($high - $low), 14)",
    "($close - Min($low, 20)) / (Max($high, 20) - Min($low, 20) + 1e-12)",
]
custom_names = ["CUSTOM_MACD", "CUSTOM_MACD_SIGNAL", "CUSTOM_ATR", "CUSTOM_PRICE_POSITION"]

print("NestedDataLoader: Alpha158 + ozel faktorler birlestiriliyor...")
nd = NestedDataLoader(
    dataloader_l=[
        {"class": "qlib.contrib.data.loader.Alpha158DL"},
        {
            "class": "qlib.data.dataset.loader.QlibDataLoader",
            "kwargs": {
                "config": {
                    "feature": (custom_fields, custom_names),
                    "label": (["Ref($close, -2)/Ref($close, -1) - 1"], ["LABEL0"]),
                }
            },
        },
    ]
)

handler = DataHandlerLP(
    instruments="all",
    start_time="2020-01-01",
    end_time="2026-08-10",
    data_loader=nd,
    infer_processors=[
        {"class": "RobustZScoreNorm", "kwargs": {"fields_group": "feature", "clip_outlier": True, "fit_start_time": "2020-01-01", "fit_end_time": "2025-06-30"}},
        {"class": "Fillna", "kwargs": {"fields_group": "feature"}},
    ],
    learn_processors=[{"class": "DropnaLabel"}, {"class": "CSZScoreNorm", "kwargs": {"fields_group": "label"}}],
)

dataset = DatasetH(handler, segments={
    "train": ("2020-01-01", "2025-06-30"),
    "valid": ("2025-07-01", "2025-12-31"),
    "test": ("2026-01-01", "2026-08-10"),
})

print("LightGBM (Alpha158+Ozel) modeli egitiliyor...")
model = LGBModel(loss="mse", num_leaves=64, learning_rate=0.05, n_estimators=200)
model.fit(dataset)

os.makedirs("/app/models", exist_ok=True)
with open("/app/models/lightgbm_custom.pkl", "wb") as f:
    pickle.dump(model, f)

pred = model.predict(dataset, segment="test")
print(f"MODEL C TAMAMLANDI. Test tahmin sayisi: {len(pred)}")
print(pred.describe())
