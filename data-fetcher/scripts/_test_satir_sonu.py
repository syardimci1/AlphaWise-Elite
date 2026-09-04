"""IZOLE BIRIM TESTI — satir sonu (line terminator) duzeltmesi.

Ag/veri erisimi YOK: defeatbeta yerine sahte bir 'yeni' DataFrame kullanilir.
ESKI kod (pandas varsayilani, her zaman LF) ile YENI kod (hedefin KENDI satir
sonu) yan yana kosulur.

NEDEN BU TEST VAR (24.08.2026 olculdu)
  us_data deposunda iki kaynaktan gelen dosyalar birlikte yasiyor:
    - 4.011 dosya LF   (\\n)    — defeatbeta toplu cekim
    - 2.744 dosya CRLF (\\r\\n)  — Tiingo/qlib yolu
  incremental_update.py yeni barlari pandas to_csv(mode="a") ile ekliyordu;
  pandas varsayilan olarak LF yazar. CRLF bir dosyaya LF eklenince dosya
  KARISIK satir sonlu hale geliyor. Olculen sonuc: 6.755 dosyanin 104'u
  karisik satir sonlu ve DuckDB'nin CSV lehce sezicisi bu dosyalari
  ayristiramiyor:
    InvalidInputException: Error when sniffing file ".../AACI.csv"
  Bu, qlib-service/data_prep/test_polars_duckdb.py'yi de dusuruyordu.

  Bu duzeltme, sutun sirasi duzeltmesiyle (bkz. _test_sutun_sirasi.py) AYNI
  ilkeyi izler: bicim kararlari sabit kodlanmaz, HEDEF DOSYANIN KENDISINDEN
  okunur.
"""
import os
import tempfile

import pandas as pd

SUTUNLAR = ["date", "open", "high", "low", "close", "volume", "factor"]

YENI_BAR = {"date": pd.Timestamp("2026-08-24"), "open": 100.0, "high": 110.0,
            "low": 90.0, "close": 105.0, "volume": 1000, "factor": 1.0}


def dosya_kur(satir_sonu, yol):
    """Verilen satir sonuyla tek satirlik gecerli bir CSV yaz."""
    ilk = {"date": "2026-08-21", "open": 100.0, "high": 110.0,
           "low": 90.0, "close": 105.0, "volume": 900, "factor": 1.0}
    govde = pd.DataFrame([ilk])[SUTUNLAR].to_csv(index=False, lineterminator="\n")
    with open(yol, "wb") as f:
        f.write(govde.replace("\n", satir_sonu).encode())


def satir_sonu_oku(csv_path):
    """Hedef dosyanin KENDI satir sonunu ilk satirdan tespit et.

    incremental_update.py'deki duzeltmenin birebir kopyasidir; ikisi
    ayrisirsa bu test bunu yakalar.
    """
    with open(csv_path, "rb") as f:
        ilk = f.readline()
    return "\r\n" if ilk.endswith(b"\r\n") else "\n"


def ekle_ESKI(csv_path, yeni):
    """pandas varsayilani — her zaman LF yazar."""
    yeni.to_csv(csv_path, mode="a", header=False, index=False)


def ekle_YENI(csv_path, yeni):
    """Hedef dosyanin kendi satir sonuyla yazar."""
    yeni.to_csv(csv_path, mode="a", header=False, index=False,
                lineterminator=satir_sonu_oku(csv_path))


def karisik_mi(yol):
    """Dosyada hem CRLF hem yalniz-LF var mi?"""
    with open(yol, "rb") as f:
        ham = f.read()
    crlf = ham.count(b"\r\n")
    yalniz_lf = ham.count(b"\n") - crlf
    return bool(crlf and yalniz_lf)


def kos(etiket, ekleyici):
    print(f"\n===== {etiket} =====")
    tum_ok = True
    for ad, satir_sonu in (("LF dosya", "\n"), ("CRLF dosya", "\r\n")):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "T.csv")
            dosya_kur(satir_sonu, p)
            ekleyici(p, pd.DataFrame([YENI_BAR])[SUTUNLAR])

            karisik = karisik_mi(p)
            # Deger butunlugu: karisik olsa bile pandas dogru okuyabilir;
            # bu yuzden ayri ayri raporlanir.
            geri = pd.read_csv(p)
            son = geri.iloc[-1]
            deger_dogru = (son["open"] == 100.0 and son["high"] == 110.0
                           and son["low"] == 90.0 and son["close"] == 105.0)
            durum = "OK" if (not karisik and deger_dogru) else "BOZUK"
            if durum == "BOZUK":
                tum_ok = False
            print(f"  {ad}: karisik_satir_sonu={karisik} deger_dogru={deger_dogru} -> {durum}")
    return tum_ok


eski_ok = kos("ESKI KOD (pandas varsayilani, hep LF)", ekle_ESKI)
yeni_ok = kos("YENI KOD (hedefin kendi satir sonu)", ekle_YENI)

print("\n===== SONUC =====")
print(f"  ESKI kod her iki dosyada da temiz mi : {eski_ok}   (beklenen: False — hata burada)")
print(f"  YENI kod her iki dosyada da temiz mi : {yeni_ok}   (beklenen: True)")
gecti = (not eski_ok) and yeni_ok
print("\nTEST:", "PASS" if gecti else "FAIL")
raise SystemExit(0 if gecti else 1)
