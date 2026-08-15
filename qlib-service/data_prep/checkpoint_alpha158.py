"""
ALPHAWISE - Bellek-verimli kontrol noktasi testi (15.08.2026)
Alpha360 (2814 hisse) 24GB sunucuda 7 kez OOM ile olduruldu (dmesg kaniti:
18.5GB / 20.7GB / 22.4GB). Alpha158, faktor sayisinin %44'u kadar bellek
kullanir -> ~10GB, mevcut kaynaklara sigar.
Egitim + IC hesaplamasi TEK dosyada, hata durumunda ACIKCA raporlar.
"""
import sys
import traceback

try:
    import qlib
    from qlib.constant import REG_US
    from qlib.contrib.model.gbdt import LGBModel
    from qlib.contrib.data.handler import Alpha158
    from qlib.data.dataset import DatasetH
    import numpy as np
    import pickle
    import os

    print("[ADIM 1/4] Qlib baslatiliyor...", flush=True)
    qlib.init(provider_uri='/app/qlib_bin_data/us_data', region=REG_US, kernels=2)

    print("[ADIM 2/4] Alpha158 faktor seti hesaplaniyor (bellek-verimli)...", flush=True)
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

    print("[ADIM 3/4] LightGBM egitiliyor...", flush=True)
    model = LGBModel(loss="mse", num_leaves=64, learning_rate=0.05, n_estimators=200)
    model.fit(dataset)

    os.makedirs("/app/models", exist_ok=True)
    with open("/app/models/lightgbm_alpha158_us.pkl", "wb") as f:
        pickle.dump(model, f)

    print("[ADIM 4/4] IC hesaplaniyor...", flush=True)
    pred = model.predict(dataset, segment="test")
    label = dataset.prepare("test", col_set="label")["LABEL0"]
    common = pred.index.intersection(label.index)
    ic = np.corrcoef(pred.loc[common], label.loc[common])[0, 1]

    print("", flush=True)
    print("=" * 50, flush=True)
    print(f"SONUC - ABD Alpha158 IC: {ic:.5f}", flush=True)
    print(f"Test tahmin sayisi: {len(pred)}, ortak satir: {len(common)}", flush=True)
    print(f"KARSILASTIRMA -> Onceki ABD Alpha360 IC: 0.01292 | BIST IC: 0.07356-0.09036", flush=True)
    print("=" * 50, flush=True)

except Exception:
    print("", flush=True)
    print("!!! HATA OLUSTU - tam detay asagida !!!", flush=True)
    traceback.print_exc()
    sys.exit(1)
