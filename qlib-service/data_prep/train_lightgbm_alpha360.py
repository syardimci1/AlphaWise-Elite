"""
ALPHAWISE - Model B: LightGBM + Alpha360 (360 faktor)
"""
import qlib
from qlib.constant import REG_US
from qlib.contrib.model.gbdt import LGBModel
from qlib.contrib.data.handler import Alpha360
from qlib.data.dataset import DatasetH
import pickle
import os

# kernels=1: bellek yetersizligi (OOM) nedeniyle paralel isci sayisi sinirlandi (14.08.2026)
qlib.init(provider_uri='/app/qlib_bin_data/us_data', region=REG_US, kernels=1)

data_handler_config = {
    "start_time": "2020-01-01",
    "end_time": "2026-08-10",
    "fit_start_time": "2020-01-01",
    "fit_end_time": "2025-06-30",
    "instruments": "all",
}

print("Alpha360 faktor seti hesaplaniyor (360 faktor, biraz daha uzun surer)...")
handler = Alpha360(**data_handler_config)

dataset = DatasetH(handler, segments={
    "train": ("2020-01-01", "2025-06-30"),
    "valid": ("2025-07-01", "2025-12-31"),
    "test": ("2026-01-01", "2026-08-10"),
})

print("LightGBM (Alpha360) modeli egitiliyor...")
model = LGBModel(loss="mse", num_leaves=64, learning_rate=0.05, n_estimators=200)
model.fit(dataset)

os.makedirs("/app/models", exist_ok=True)
with open("/app/models/lightgbm_alpha360.pkl", "wb") as f:
    pickle.dump(model, f)

pred = model.predict(dataset, segment="test")
print(f"MODEL B TAMAMLANDI. Test tahmin sayisi: {len(pred)}")
print(pred.describe())
