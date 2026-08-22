"""
ALPHAWISE - Gunluk Skor Onbellegi Ureticisi (16.08.2026)
/predict endpoint'i CANLI hesaplama yapmiyor artik - bu script GUNDE
BIR KEZ (cron) TUM evrenin skorlarini hesaplayip diske yazar.
Endpoint sadece bu dosyayi okur (milisaniyeler).
"""
import qlib
from qlib.constant import REG_US
from qlib.contrib.data.handler import Alpha158
from qlib.data import D
import pickle, json, os

qlib.init(provider_uri="/app/qlib_bin_data/us_data", region=REG_US, kernels=2)

with open("/app/models/lightgbm_batched_us.pkl", "rb") as f:
    model = pickle.load(f)

# 22.08.2026 DUZELTME - SESSIZ DONMA HATASI:
# Bu iki tarih ONCEDEN SABIT KODLUYDU (start "2026-06-01", end "2026-08-16").
# Sonuc: haftalik yeniden egitim veriyi 19 Agustos'a kadar tazelese bile
# skorlar 14 Agustos'ta DONUP KALIYORDU ve /predict endpoint'i gunlerce
# eski skor servis ediyordu — hicbir hata vermeden. Artik gercek takvimden
# okunuyor, boylece veri ilerledikce skorlar da ilerler.
takvim = D.calendar(start_time="2020-01-01")
son_tarih = str(takvim[-1].date())
# Alpha158'in en uzun penceresi 60 gun; 150 islem gunu fazlasiyla yeterli
# ve pencereyi sabit tutar (sabit baslangic tarihi zamanla buyuyup
# hesaplamayi gereksiz yavaslatirdi).
baslangic = str(takvim[max(0, len(takvim) - 150)].date())
print(f"Takvimden okunan aralik: {baslangic} -> {son_tarih}", flush=True)

print("Alpha158 ozellikleri hesaplaniyor (TUM evren, gunde 1 kez)...", flush=True)
handler = Alpha158(
    start_time=baslangic, end_time=son_tarih,
    fit_start_time="2020-01-01", fit_end_time="2025-12-31",
    instruments="all",
)
df = handler.fetch(col_set="feature")
latest_date = df.index.get_level_values(0).max()
latest = df.xs(latest_date, level=0)

print(f"Tahminler hesaplaniyor ({len(latest)} hisse)...", flush=True)
preds = model.predict(latest)

scores = {ticker: round(float(p), 6) for ticker, p in zip(latest.index, preds)}
output = {"as_of_date": str(latest_date), "scores": scores}

with open("/app/models/daily_scores_cache.json", "w") as f:
    json.dump(output, f)

print(f"TAMAMLANDI: {len(scores)} hisse icin skor onbellege yazildi ({latest_date})", flush=True)
