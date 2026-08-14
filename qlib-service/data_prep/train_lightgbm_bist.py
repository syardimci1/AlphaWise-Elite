"""
ALPHAWISE - BIST Model: LightGBM + Alpha360
ABD'deki Model B'nin (Alpha360) birebir ayni deseni, BIST verisiyle.
Ayri qlib_dir (bist_data) kullanir, ABD modeliyle karismaz.
"""
import qlib
from qlib.constant import REG_US
from qlib.contrib.model.gbdt import LGBModel
from qlib.contrib.data.handler import Alpha360
from qlib.data.dataset import DatasetH
import pickle
import os

qlib.init(provider_uri='/app/qlib_bin_data/bist_data', region=REG_US)

# BIST verisi 2020-01-01'den bugune (13 Agustos 2026)
data_handler_config = {
    "start_time": "2020-01-01",
    "end_time": "2026-08-13",
    "fit_start_time": "2020-01-01",
    "fit_end_time": "2025-12-31",
    "instruments": "all",
}

print("BIST Alpha360 faktor seti hesaplaniyor...")
handler = Alpha360(**data_handler_config)

dataset = DatasetH(handler, segments={
    "train": ("2020-01-01", "2025-12-31"),
    "valid": ("2026-01-01", "2026-04-30"),
    "test": ("2026-05-01", "2026-08-13"),
})

print("LightGBM (BIST) modeli egitiliyor...")
model = LGBModel(loss="mse", num_leaves=64, learning_rate=0.05, n_estimators=200)
model.fit(dataset)

os.makedirs("/app/models", exist_ok=True)
with open("/app/models/lightgbm_bist.pkl", "wb") as f:
    pickle.dump(model, f)

pred = model.predict(dataset, segment="test")
print(f"BIST MODEL TAMAMLANDI. Test tahmin sayisi: {len(pred)}")
print(pred.describe())
