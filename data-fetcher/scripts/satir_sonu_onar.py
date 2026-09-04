"""
ALPHAWISE - Karisik Satir Sonu Onarim Araci (04.09.2026)

NEDEN BU ARAC VAR
  us_data deposunda iki kaynaktan gelen dosyalar birlikte yasiyor: defeatbeta
  toplu cekimi LF (\\n) yazar, Tiingo/qlib yolu CRLF (\\r\\n) yazar.
  incremental_update.py artik hedef dosyanin KENDI satir sonunu kullanarak
  ekleme yapiyor (bkz. _test_satir_sonu.py), ama bu yalnizca BUNDAN SONRAKI
  yazimlari korur. Onarim penceresinin disinda kalan veya baska bir yoldan
  (orn. toplu cekim script'leri) karisik hale gelmis dosyalar icin GERIYE
  DONUK, tek seferlik bir onarim araci gerekiyordu.

  04.09.2026 look-ahead bias denetiminde 6.742 dosyanin 2.711'i karisik
  satir sonluydu ve bu, DuckDB'nin CSV lehce sezicisini dusuruyordu
  (qlib-service/data_prep/test_polars_duckdb.py):
    InvalidInputException: Error when sniffing file ".../A.csv"
  incremental_update.py duzeltmesi calistirildiktan sonra bile 92 dosya
  karisik kaldi (revizyon penceresinin disindaki, dokunulmayan eski
  satirlar yuzunden); bu arac onlari normalize etti ve kanaryayi FAIL'den
  PASS'e gecirdi.

GUVENLIK ILKESI
  Yalnizca SATIR SONU karakterleri degistirilir. Hicbir ALAN DEGERI, satir
  sayisi veya sutun duzeni degismez. Her dosya icin yazim ONCESI ve SONRASI
  pandas ile ayristirilip BIREBIR ESITLIK dogrulanir; ayristirilamiyorsa
  veya esit degilse dosyaya DOKUNULMAZ (fail-closed) — sessizce yarim
  onarim yapilmaz. Hedef satir sonu, dosyanin KENDI ilk satirindan okunur
  (onceki iki duzeltmeyle - sutun sirasi ve satir sonu - AYNI ilke).

KULLANIM
  python satir_sonu_onar.py [DIZIN]
  DIZIN verilmezse SATIR_SONU_ONARIM_DIZIN ortam degiskeni, o da yoksa
  /app/csv_data/us_data kullanilir.

Kanit: _test_satir_sonu_onar.py
"""
import glob
import io
import os
import sys

import pandas as pd

VARSAYILAN_DIZIN = os.environ.get("SATIR_SONU_ONARIM_DIZIN", "/app/csv_data/us_data")


def karisik_mi(ham: bytes) -> bool:
    """Dosyada hem CRLF hem yalniz-LF satir sonu birlikte var mi?"""
    crlf = ham.count(b"\r\n")
    lf = ham.count(b"\n")
    return bool(crlf and (lf - crlf))


def hedef_satir_sonu(ham: bytes) -> bytes:
    """Dosyanin KENDI ilk satirindan hedef satir sonunu tespit et."""
    ilk_satir = ham.split(b"\n", 1)[0]
    return b"\r\n" if ilk_satir.endswith(b"\r") else b"\n"


def normalize_dosya(yol: str) -> str:
    """Bir dosyayi gerekirse normalize eder; ne oldugunu aciklayan bir
    etiket doner: 'atlandi_karisik_degil', 'atlandi_ayristirilamadi',
    'atlandi_esitlik_dogrulanamadi' veya 'duzeltildi'.
    """
    with open(yol, "rb") as f:
        ham = f.read()
    if not karisik_mi(ham):
        return "atlandi_karisik_degil"

    hedef = hedef_satir_sonu(ham)
    yeni = ham.replace(b"\r\n", b"\n").replace(b"\n", hedef)

    try:
        onceki_df = pd.read_csv(io.BytesIO(ham))
        sonraki_df = pd.read_csv(io.BytesIO(yeni))
    except Exception:
        return "atlandi_ayristirilamadi"

    ayni = (list(onceki_df.columns) == list(sonraki_df.columns)
            and len(onceki_df) == len(sonraki_df)
            and onceki_df.equals(sonraki_df))
    if not ayni:
        return "atlandi_esitlik_dogrulanamadi"

    gecici = yol + ".tmp"
    with open(gecici, "wb") as f:
        f.write(yeni)
    os.replace(gecici, yol)
    return "duzeltildi"


def main():
    dizin = sys.argv[1] if len(sys.argv) > 1 else VARSAYILAN_DIZIN
    sayac = {}
    for yol in sorted(glob.glob(f"{dizin}/*.csv")):
        etiket = normalize_dosya(yol)
        sayac[etiket] = sayac.get(etiket, 0) + 1

    print(f"Taranan dizin: {dizin}")
    for etiket, n in sorted(sayac.items(), key=lambda z: -z[1]):
        print(f"  {etiket:32s}: {n}")
    if not sayac:
        print("  (dizinde .csv dosyasi bulunamadi)")


if __name__ == "__main__":
    main()
