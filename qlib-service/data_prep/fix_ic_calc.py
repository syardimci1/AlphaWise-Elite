"""
ALPHAWISE - IC hesaplamasini NaN-guvenli hale getirir (15.08.2026).
Onceki calistirmada IC=nan cikti - muhtemel neden: test donemi son
gunlerinde ileri-donuk etiketin (2 gun sonraki getiri) hesaplanamamasi.
Cozum: corrcoef'ten ONCE NaN iceren satirlari at.
"""
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

print(f"HAM: tahmin={len(pred)}, NaN tahmin={pred.isna().sum()}, etiket={len(label)}, NaN etiket={label.isna().sum()}", flush=True)

common_idx = pred.index.intersection(label.index)
p = pred.loc[common_idx]
l = label.loc[common_idx]

# NaN olan satirlari FILTRELE (kritik duzeltme)
valid_mask = p.notna() & l.notna()
p_clean = p[valid_mask]
l_clean = l[valid_mask]

print(f"TEMIZLENDI: {valid_mask.sum()}/{len(common_idx)} gecerli satir kaldi", flush=True)

if len(p_clean) > 10:
    ic = np.corrcoef(p_clean, l_clean)[0, 1]
    print(f"", flush=True)
    print("=" * 50, flush=True)
    print(f"DUZELTILMIS SONUC - ABD Alpha158 IC: {ic:.5f}", flush=True)
    print(f"Gecerli ornek sayisi: {len(p_clean)}", flush=True)
    print("=" * 50, flush=True)
else:
    print("HATA: temizleme sonrasi yeterli veri kalmadi", flush=True)
