"""
ALPHAWISE - Model B HIZLI KONTROL TESTI (14.08.2026)
Bellek sinirlamasi nedeniyle SADECE ILK 1000 hisseyle calisir.
Amac: boru hattinin saglikli calistigini hizlica dogrulamak,
tam-kapsam egitim gece cron ile yapilacak.
"""
import qlib
from qlib.constant import REG_US
from qlib.contrib.model.gbdt import LGBModel
from qlib.contrib.data.handler import Alpha360
from qlib.data.dataset import DatasetH
import pickle
import os

qlib.init(provider_uri='/app/qlib_bin_data/us_data', region=REG_US, kernels=2)

from qlib.data import D
all_instruments = D.instruments(market='all')
all_tickers = D.list_instruments(instruments=all_instruments, as_list=True)
subset_tickers = sorted(all_tickers)[:1000]
print(f"Toplam hisse: {len(all_tickers)}, test icin kullanilacak: {len(subset_tickers)}")

data_handler_config = {
    "start_time": "2020-01-01",
    "end_time": "2026-08-13",
    "fit_start_time": "2020-01-01",
    "fit_end_time": "2025-12-31",
    "instruments": subset_tickers,
}

print("Alpha360 faktor seti hesaplaniyor (1000 hisse - hizli test)...")
handler = Alpha360(**data_handler_config)

dataset = DatasetH(handler, segments={
    "train": ("2020-01-01", "2025-12-31"),
    "valid": ("2026-01-01", "2026-04-30"),
    "test": ("2026-05-01", "2026-08-13"),
})

print("LightGBM modeli egitiliyor...")
model = LGBModel(loss="mse", num_leaves=64, learning_rate=0.05, n_estimators=200)
model.fit(dataset)

os.makedirs("/app/models", exist_ok=True)
with open("/app/models/lightgbm_quicktest.pkl", "wb") as f:
    pickle.dump(model, f)

pred = model.predict(dataset, segment="test")
print(f"HIZLI TEST TAMAMLANDI. Test tahmin sayisi: {len(pred)}")
print(pred.describe())
