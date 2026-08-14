"""
ALPHAWISE - Qlib LightGBM Model Egitimi
Alpha158 faktor seti (RSI, momentum, hacim vb. 158 ozellik) + LightGBM.
Egitilen model diske kaydedilir - "egitim yavas/arka planda, tahmin hizli/anlik"
mimarisinin geregi (kullanici sorgusunda YENIDEN egitim yapilmaz).
"""
import qlib
from qlib.constant import REG_US
from qlib.contrib.model.gbdt import LGBModel
from qlib.contrib.data.handler import Alpha158
from qlib.data.dataset import DatasetH
import pickle
import os

qlib.init(provider_uri='/app/qlib_bin_data/us_data', region=REG_US)

# Guncel veri araligina gore tarihler (elimizdeki veri 2020'den bugune)
data_handler_config = {
    "start_time": "2020-01-01",
    "end_time": "2026-08-10",
    "fit_start_time": "2020-01-01",
    "fit_end_time": "2025-06-30",
    "instruments": "all",
}

print("Alpha158 faktor seti hesaplaniyor...")
handler = Alpha158(**data_handler_config)

dataset = DatasetH(handler, segments={
    "train": ("2020-01-01", "2025-06-30"),
    "valid": ("2025-07-01", "2025-12-31"),
    "test": ("2026-01-01", "2026-08-10"),
})

print("LightGBM modeli egitiliyor...")
model = LGBModel(
    loss="mse",
    num_leaves=64,
    learning_rate=0.05,
    n_estimators=200,
)
model.fit(dataset)

os.makedirs("/app/models", exist_ok=True)
with open("/app/models/lightgbm_v1.pkl", "wb") as f:
    pickle.dump(model, f)

print("Model kaydedildi: /app/models/lightgbm_v1.pkl")

# Test setinde hizli bir dogruluk kontrolu
pred = model.predict(dataset, segment="test")
print(f"Test tahmin sayisi: {len(pred)}")
print(f"Ornek tahminler:\n{pred.head(10)}")
