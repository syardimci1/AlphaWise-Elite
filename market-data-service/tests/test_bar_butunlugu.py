"""IZOLE BIRIM TESTI - /price ucunun bar butunlugu suzgeci.

NEDEN BU TEST VAR (04.09.2026, look-ahead bias denetimi)
  qlib-service/csv_data_persistent/us_data'da (bu servisin de okudugu ayni
  merkezi depo) 4.649 imkansiz bar bulundu: high < max(open,close) veya
  low > min(open,close). Kaynak dosyalar data-fetcher/scripts/
  incremental_update.py duzeltmesiyle onarildi, ama:
    - bazi barlar saglayicinin KENDI bozuk verisi oldugu icin kaldi,
    - TAA'nin protected taa/src/main.py dosyasina kontrol EKLENEMEZ.
  Bu yuzden ayni kural /price'in OKUMA yolunda (read_central_csv) tekrarlanir.
  TAA'nin formasyon modulu "ust_golge = High - max(Open,Close)" gibi
  hesaplar yapiyor; imkansiz bir bar bu degeri NEGATIF yapar ve ATR'yi
  bozar - imkansiz bar, eksik bardan daha kotudur (projenin "olculemedi"
  ilkesi: eksik veri durustur, uydurulmus/bozuk veri degildir).

  gecerli() KURALI, incremental_update.py'deki bar_butunlugu_gecerli() ile
  BIREBIR AYNIDIR - iki kod tabaninda ayni bar ayni sekilde degerlendirilsin.
"""
import csv
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import main as market_data  # noqa: E402


GECERLI = {"date": "2026-08-27", "open": "41.31", "high": "41.42",
           "low": "40.66", "close": "41.03", "volume": "1000", "factor": "1.0"}
IMKANSIZ_HIGH = {"date": "2026-08-27", "open": "37.0", "high": "36.74",
                 "low": "36.33", "close": "36.52", "volume": "500", "factor": "1.0"}
IMKANSIZ_LOW = {"date": "2026-08-27", "open": "0.048", "high": "0.0317",
                "low": "0.0255", "close": "0.0317", "volume": "620", "factor": "1.0"}
EKSIK_ALAN = {"date": "2026-08-27", "open": "10.0", "high": "11.0", "low": "9.0"}
BOZUK_SAYI = {"date": "2026-08-27", "open": "abc", "high": "11.0",
              "low": "9.0", "close": "10.0", "volume": "1", "factor": "1.0"}


def test_bar_butunlugu_gecerli():
    print("\n===== bar_butunlugu_gecerli() birim testi =====")
    vakalar = [
        ("gecerli bar (GFL 08-27, canli veriyle dogrulandi)", GECERLI, True),
        ("imkansiz - high acilis/kapanisin altinda (RDN 08-27 deseni)", IMKANSIZ_HIGH, False),
        ("imkansiz - low acilis/kapanisin ustunde (ACONW 08-27 deseni)", IMKANSIZ_LOW, False),
        ("eksik alan (close yok)", EKSIK_ALAN, False),
        ("sayisal olmayan alan", BOZUK_SAYI, False),
    ]
    tum_ok = True
    for etiket, row, beklenen in vakalar:
        sonuc = market_data.bar_butunlugu_gecerli(row)
        ok = sonuc == beklenen
        tum_ok &= ok
        print(f"  [{'OK' if ok else 'FAIL'}] {etiket}: gecerli={sonuc} (beklenen: {beklenen})")
    return tum_ok


def test_read_central_csv_imkansiz_bari_filtreler():
    print("\n===== read_central_csv() - imkansiz bar SIZDIRMIYOR mu =====")
    with tempfile.TemporaryDirectory() as d:
        market_data.CENTRAL_DATA_DIR = d
        path = os.path.join(d, "TEST.csv")
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["date", "open", "high", "low", "close", "volume", "factor"])
            w.writeheader()
            w.writerow(GECERLI)
            w.writerow(IMKANSIZ_HIGH)
            w.writerow(GECERLI | {"date": "2026-08-28"})

        rows = market_data.read_central_csv("TEST", limit=60)
        tarihler = [r["date"] for r in rows]
        imkansiz_disarida = "2026-08-27" not in [r["date"] for r in rows if r == IMKANSIZ_HIGH]
        n_ok = len(rows) == 2
        print(f"  donen bar sayisi: {len(rows)} (beklenen: 2, kaynakta 3 satir vardi)")
        print(f"  tarihler: {tarihler}")
        print(f"  imkansiz bar disarida mi: {imkansiz_disarida} (beklenen: True)")
        return n_ok and imkansiz_disarida


def test_read_central_csv_hepsi_imkansizsa_bos_doner():
    print("\n===== read_central_csv() - TUMU imkansizsa None doner =====")
    with tempfile.TemporaryDirectory() as d:
        market_data.CENTRAL_DATA_DIR = d
        path = os.path.join(d, "TEST2.csv")
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["date", "open", "high", "low", "close", "volume", "factor"])
            w.writeheader()
            w.writerow(IMKANSIZ_HIGH)
            w.writerow(IMKANSIZ_LOW)
        sonuc = market_data.read_central_csv("TEST2", limit=60)
        ok = sonuc is None
        print(f"  sonuc: {sonuc} (beklenen: None)")
        return ok


sonuclar = [
    test_bar_butunlugu_gecerli(),
    test_read_central_csv_imkansiz_bari_filtreler(),
    test_read_central_csv_hepsi_imkansizsa_bos_doner(),
]
print("\nTEST: " + ("PASS" if all(sonuclar) else "FAIL"))
raise SystemExit(0 if all(sonuclar) else 1)
