"""
BIST modelinin IC bulgusunu DOGRULAMA: farkli, daha erken bir test
donemiyle ayni deneyi tekrarlar. Eger IC benzer/pozitif cikarsa,
tek donemin sans eseri olmadigina dair daha guclu kanit olur.
"""
import qlib
from qlib.constant import REG_US
from qlib.contrib.model.gbdt import LGBModel
from qlib.contrib.data.handler import Alpha360
from qlib.data.dataset import DatasetH
import numpy as np

qlib.init(provider_uri='/app/qlib_bin_data/bist_data', region=REG_US)

# FARKLI bir bolme: daha erken bir test penceresi (Kasim 2025-Subat 2026)
# boylece egitilen modelin farkli bir donemde de calisip calismadigini goruyoruz
handler = Alpha360(
    start_time="2020-01-01", end_time="2026-08-13",
    fit_start_time="2020-01-01", fit_end_time="2025-10-31",
    instruments="all",
)
dataset = DatasetH(handler, segments={
    "train": ("2020-01-01", "2025-10-31"),
    "valid": ("2025-11-01", "2025-12-31"),
    "test": ("2026-01-01", "2026-04-30"),  # ONCEKI TESTTEN FARKLI DONEM
})

print("Dogrulama modeli egitiliyor (farkli test donemi)...")
model = LGBModel(loss="mse", num_leaves=64, learning_rate=0.05, n_estimators=200)
model.fit(dataset)

pred = model.predict(dataset, segment="test")
label = dataset.prepare("test", col_set="label")["LABEL0"]
common_idx = pred.index.intersection(label.index)
ic = np.corrcoef(pred.loc[common_idx], label.loc[common_idx])[0, 1]

print(f"DOGRULAMA IC (Ocak-Nisan 2026 test donemi): {ic:.5f}")
print(f"Tahmin sayisi: {len(pred)}, ortak satir: {len(common_idx)}")
print(f"KARSILASTIRMA: Ilk test (Mayis-Agustos 2026) IC: 0.09036")
