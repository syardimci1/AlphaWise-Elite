"""
ALPHAWISE - ABD hisseleri icin FMP (Financial Modeling Prep) ile veri toplama (16.08.2026)
Tiingo'nun aylik yeni-sembol kotasi doldu. FMP'nin YENI 'stable' API yapisi
kullanilir (eski /api/v3/ Agustos 2025'te kaldirildi).
Sadece progress.json'daki HALA basarisiz olan hisseleri dener.
"""
import requests
import json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fmp_kota import KotaSayaci  # noqa: E402

PROGRESS_FILE = "/app/csv_data/progress.json"
DATA_DIR = "/app/csv_data/us_data"
API_KEY = os.getenv("FMP_API_KEY")

if not API_KEY:
    print("HATA: FMP_API_KEY ortam degiskeni bulunamadi", flush=True)
    exit(1)

with open(PROGRESS_FILE) as f:
    progress = json.load(f)

to_retry = progress["failed"]
print(f"FMP ile denenecek: {len(to_retry)} hisse", flush=True)

# KOTA BEKCISI: bu script congress-trading-service ile AYNI FMP anahtarini
# paylasiyor (dogrulandi). Burasi arka plan isi, o ise kullanici isteginden
# tetikleniyor. Bekci, gunluk kotanin bir kismini kullanici-yuzu servise
# rezerve eder ve toplu cekme o siniri asamaz — boylece dashboard karti
# toplu is yuzunden bos kalmaz.
kota = KotaSayaci("bulk_fetch_fmp_us")
print(
    f"FMP gunluk kota: tavan {kota.tavan}, arka plan butcesi "
    f"{kota.arka_plan_butcesi()}, kullanici rezervi {kota.rezerv}, "
    f"bugun kullanilan {kota.kullanilan()}",
    flush=True,
)

completed_now = []
still_failed = []
kota_yuzunden_atlanan = []

for i, ticker in enumerate(to_retry):
    if not kota.izin_var():
        # Kalanlari BASARISIZ saymiyoruz: denenmediler. Bir sonraki
        # calistirmada (yarin, kota sifirlaninca) yeniden denenecekler.
        kota_yuzunden_atlanan = to_retry[i:]
        break
    try:
        url = f"https://financialmodelingprep.com/stable/historical-price-eod/full?symbol={ticker}&from=2020-01-01&apikey={API_KEY}"
        resp = requests.get(url, timeout=15)
        kota.harca()          # istek FIILEN yapildi, sayaci artir
        data = resp.json()

        if not isinstance(data, list) or len(data) == 0:
            still_failed.append(ticker)
            continue

        with open(f"{DATA_DIR}/{ticker}.csv", "w") as f:
            f.write("date,open,high,low,close,volume,factor\n")
            for row in reversed(data):  # FMP yeniden eskiye veriyor, ters cevir
                f.write(f"{row['date']},{row['open']},{row['high']},{row['low']},{row['close']},{row['volume']},1.0\n")

        completed_now.append(ticker)

    except Exception:
        still_failed.append(ticker)

    time.sleep(0.15)  # FMP rate-limit'e saygili (dakikada ~400 cagri)

    if (i + 1) % 50 == 0:
        progress["completed"] = list(set(progress["completed"]) | set(completed_now))
        progress["failed"] = still_failed + to_retry[i+1:]
        with open(PROGRESS_FILE, "w") as f:
            json.dump(progress, f)
        print(f"  {i+1}/{len(to_retry)} islendi (basarili: {len(completed_now)})", flush=True)

progress["completed"] = list(set(progress["completed"]) | set(completed_now))
# Kota yuzunden hic DENENMEMIS olanlar "basarisiz" degildir; listede
# kalirlar ki bir sonraki calistirmada yeniden denensinler.
progress["failed"] = still_failed + kota_yuzunden_atlanan
with open(PROGRESS_FILE, "w") as f:
    json.dump(progress, f)

print(f"\nTAMAMLANDI. FMP ile ek basarili: {len(completed_now)}", flush=True)
print(f"Toplam tamamlanan: {len(progress['completed'])}", flush=True)
print(f"Hala basarisiz: {len(still_failed)}", flush=True)
if kota_yuzunden_atlanan:
    print(
        f"KOTA NEDENIYLE DENENMEDI: {len(kota_yuzunden_atlanan)} hisse — "
        f"kullanici-yuzu servisin payi korundu, bunlar bir sonraki "
        f"calistirmada denenecek.",
        flush=True,
    )
print(kota.ozet(), flush=True)
