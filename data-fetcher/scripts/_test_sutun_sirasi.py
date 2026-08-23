"""IZOLE BIRIM TESTI — sutun sirasi duzeltmesi.
Ag/veri erisimi YOK: defeatbeta yerine sahte bir 'yeni' DataFrame kullanilir.
ESKI kod (sabit A duzeni) ile YENI kod (hedefin kendi basligi) yan yana kosulur.
"""
import os
import tempfile

import pandas as pd
import polars as pl

A = ["date", "open", "high", "low", "close", "volume", "factor"]
B = ["date", "open", "close", "high", "low", "volume", "factor"]

# Kaynaktan gelen yeni bar: o=100, h=110, l=90, c=105  (gecerli bar)
YENI_BAR = {"date": pd.Timestamp("2026-08-24"), "open": 100.0, "high": 110.0,
            "low": 90.0, "close": 105.0, "volume": 1000, "factor": 1.0}


def dosya_kur(sutunlar, yol):
    """Verilen baslik duzeninde tek satirlik gecerli bir CSV yaz."""
    ilk = {"date": "2026-08-21", "open": 100.0, "high": 110.0,
           "low": 90.0, "close": 105.0, "volume": 900, "factor": 1.0}
    pd.DataFrame([ilk])[sutunlar].to_csv(yol, index=False)


def ekle_ESKI(csv_path, mevcut, yeni):
    return yeni[A]


def ekle_YENI(csv_path, mevcut, yeni):
    hedef = list(mevcut.columns)
    eksik = [s for s in hedef if s not in yeni.columns]
    if eksik:
        raise ValueError(f"kaynakta eksik sutun {eksik}")
    return yeni[hedef]


def kos(etiket, ekleyici):
    print(f"\n===== {etiket} =====")
    tum_ok = True
    for ad, sutunlar in (("A duzeni", A), ("B duzeni", B)):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "T.csv")
            dosya_kur(sutunlar, p)
            mevcut = pl.read_csv(p)
            yeni = pd.DataFrame([YENI_BAR])
            cikti = ekleyici(p, mevcut, yeni)
            cikti.to_csv(p, mode="a", header=False, index=False)

            # geri oku ve son satirin bar butunlugunu dogrula
            geri = pd.read_csv(p)
            son = geri.iloc[-1]
            o, h, l, c = son["open"], son["high"], son["low"], son["close"]
            gecerli = (h >= max(o, c) - 1e-9) and (l <= min(o, c) + 1e-9)
            dogru_deger = (o == 100.0 and h == 110.0 and l == 90.0 and c == 105.0)
            durum = "OK" if (gecerli and dogru_deger) else "BOZUK"
            if durum == "BOZUK":
                tum_ok = False
            print(f"  {ad}: yazilan son satir o={o} h={h} l={l} c={c} "
                  f"| bar_gecerli={gecerli} deger_dogru={dogru_deger} -> {durum}")
    return tum_ok


eski_ok = kos("ESKI KOD (sabit A duzeni)", ekle_ESKI)
yeni_ok = kos("YENI KOD (hedefin kendi basligi)", ekle_YENI)

print("\n===== SONUC =====")
print(f"  ESKI kod her iki duzende de dogru mu : {eski_ok}   (beklenen: False — hata burada)")
print(f"  YENI kod her iki duzende de dogru mu : {yeni_ok}   (beklenen: True)")
print("\nTEST:", "PASS" if (not eski_ok and yeni_ok) else "FAIL")
