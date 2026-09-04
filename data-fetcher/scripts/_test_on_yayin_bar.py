"""IZOLE BIRIM TESTI — on-yayin (preliminary) bar duzeltmesi.

Ag/veri erisimi YOK: defeatbeta yerine sahte bir 'saglayici' DataFrame
kullanilir. ESKI mantik (salt-ekleme, ust tarih siniri yok, dogrulama yok)
ile YENI mantik (revizyon penceresi + bitmemis seans korumasi + bar
butunlugu dogrulamasi) yan yana kosulur.

NEDEN BU TEST VAR (04.09.2026 olculdu)
  us_data'daki 6.742 dosyanin 6.529'unun son bari 2026-08-27 idi ve o gunun
  barlari saglayicidan cekildigi anda NIHAI DEGILDI. 30 likit sembolluk
  olcumde:
      son bar (g-0)      : 20/30 saglayicinin nihai degerinden FARKLI (%66,7)
      onceki barlar g-1..g-10 : 0/30 farkli (%0,0)
  Farkin yonu tek tarafli: bizim [low, high] araligimiz nihai araligin ALT
  KUMESI. Olculen gercek ornekler (bizim -> saglayicinin nihai degeri):
      RDN  2026-08-27  high 36,74   -> 37,00
      SE   2026-08-27  high 118,875 -> 118,99
      FLUT 2026-08-27  high 98,98   -> 99,13
      GFL  2026-08-27  high 41,42   -> 41,47
  Bu bir LOOK-AHEAD BIAS DEGILDIR: elimizdeki bar gercekten olandan DAHA AZ
  bilgi tasiyor (gelecegi degil, gecmisin eksik halini iceriyor).

  Ayrica olculdu: 4.649 butunluk ihlalinin 40'lik orneginde 30'u
  SAGLAYICININ KENDI bozuk verisiydi (warrant/unit, 1990'lar tarihi).
  Bunlar TAA'nin formasyon modulunde golge uzunlugunu negatif yapar.

Bu duzeltme, onceki iki duzeltmeyle (bkz. _test_sutun_sirasi.py ve
_test_satir_sonu.py) AYNI ilkeyi izler: bicim/kapsam kararlari sabit
kodlanmaz, hedef dosyanin KENDISINDEN okunur.
"""
import os
import tempfile
from datetime import date, datetime, timedelta

import pandas as pd

SUTUNLAR = ["date", "open", "high", "low", "close", "volume", "factor"]
REVIZYON_PENCERESI_GUN = 5

BUGUN = date(2026, 9, 4)
REVIZYON_SINIRI = BUGUN - timedelta(days=REVIZYON_PENCERESI_GUN)  # 2026-08-30


def bar_butunlugu_gecerli(o, h, l, c):
    """incremental_update.py'deki dogrulamanin AYNISI."""
    try:
        o, h, l, c = float(o), float(h), float(l), float(c)
    except (TypeError, ValueError):
        return False
    if any(x != x for x in (o, h, l, c)):
        return False
    return h >= max(o, c) and l <= min(o, c) and h >= l


# --- SENARYO ---------------------------------------------------------------
# Dosyada 09-01 tarihli bar ON-YAYIN halde duruyor (high dar: 41.42).
# Saglayici ayni bari NIHAI haliyle veriyor (high 41.47) ve ustune
# 09-02 (gecerli), 09-03 (IMKANSIZ bar) ve 09-04 (BUGUN, seans surerken)
# barlarini donuyor.
MEVCUT_DOSYA = [
    {"date": "2026-08-28", "open": 40.0, "high": 41.0, "low": 39.5, "close": 40.5,
     "volume": 1000, "factor": 1.0},
    {"date": "2026-09-01", "open": 40.6, "high": 41.42, "low": 40.66, "close": 41.0,
     "volume": 1100, "factor": 1.0},   # <- ON-YAYIN: low 40.66 > open 40.6 (IHLAL)
]

SAGLAYICI = [
    {"date": "2026-08-28", "open": 40.0, "high": 41.0, "low": 39.5, "close": 40.5,
     "volume": 1000, "factor": 1.0},
    {"date": "2026-09-01", "open": 40.6, "high": 41.47, "low": 40.60, "close": 41.0,
     "volume": 1150, "factor": 1.0},   # <- NIHAI hali (duzelmis)
    {"date": "2026-09-02", "open": 41.0, "high": 42.0, "low": 40.8, "close": 41.8,
     "volume": 1200, "factor": 1.0},   # <- yeni, gecerli
    {"date": "2026-09-03", "open": 0.75, "high": 0.0085, "low": 0.005, "close": 0.0085,
     "volume": 900, "factor": 1.0},    # <- IMKANSIZ (gercek ARQQW 2026-08-21 deseni)
    {"date": "2026-09-04", "open": 41.8, "high": 41.9, "low": 41.7, "close": 41.85,
     "volume": 300, "factor": 1.0},    # <- BUGUN, seans SURUYOR
]


def dosya_kur(yol):
    pd.DataFrame(MEVCUT_DOSYA)[SUTUNLAR].to_csv(yol, index=False)


def saglayici_df():
    df = pd.DataFrame(SAGLAYICI)
    df["date"] = pd.to_datetime(df["date"])
    return df


def yaz_ESKI(csv_path):
    """Salt-ekleme, ust tarih siniri yok, dogrulama yok."""
    mevcut = pd.read_csv(csv_path)
    son_tarih = datetime.strptime(str(mevcut["date"].max())[:10], "%Y-%m-%d")
    yeni = saglayici_df()
    yeni = yeni[yeni["date"] > son_tarih][SUTUNLAR]
    if len(yeni):
        yeni.to_csv(csv_path, mode="a", header=False, index=False)


def yaz_YENI(csv_path):
    """Revizyon penceresi + bitmemis seans korumasi + butunluk dogrulamasi."""
    mevcut = pd.read_csv(csv_path)
    son_tarih = datetime.strptime(str(mevcut["date"].max())[:10], "%Y-%m-%d")
    yeni = saglayici_df()

    yeni = yeni[yeni["date"].dt.date < BUGUN]                       # (1)
    # Kesme, DOSYANIN KENDI son tarihine gore (uretimdeki mantigin AYNISI).
    kesme = son_tarih - timedelta(days=REVIZYON_PENCERESI_GUN)      # (2)
    yeni = yeni[yeni["date"] > kesme][SUTUNLAR]
    if len(yeni):
        gecerli = yeni.apply(lambda r: bar_butunlugu_gecerli(
            r["open"], r["high"], r["low"], r["close"]), axis=1)      # (3)
        yeni = yeni[gecerli]
    if len(yeni):
        eski = mevcut.copy()
        eski["date"] = pd.to_datetime(eski["date"])
        korunan = eski[eski["date"] <= kesme]
        birlesik = pd.concat([korunan[SUTUNLAR], yeni], ignore_index=True)
        birlesik = birlesik.sort_values("date")
        birlesik["date"] = pd.to_datetime(birlesik["date"]).dt.strftime("%Y-%m-%d")
        if len(birlesik) < len(eski):   # fail-closed: satir kaybi olacaksa dokunma
            return
        gecici = csv_path + ".tmp"
        birlesik.to_csv(gecici, index=False)
        os.replace(gecici, csv_path)


def denetle(etiket, yazici):
    print(f"\n===== {etiket} =====")
    with tempfile.TemporaryDirectory() as d:
        yol = os.path.join(d, "GFL.csv")
        dosya_kur(yol)
        yazici(yol)
        df = pd.read_csv(yol)

    tarihler = list(df["date"].astype(str))
    ihlal = int(((df["high"] < df[["open", "close"]].max(axis=1)) |
                 (df["low"] > df[["open", "close"]].min(axis=1))).sum())
    r0901 = df[df["date"].astype(str) == "2026-09-01"].iloc[0]
    on_yayin_duzeldi = abs(float(r0901["high"]) - 41.47) < 1e-9
    bugun_yazildi = "2026-09-04" in tarihler
    imkansiz_yazildi = "2026-09-03" in tarihler

    print(f"  tarihler                         : {tarihler}")
    print(f"  09-01 high (nihai 41.47 olmali)  : {r0901['high']}")
    print(f"  on-yayin bar DUZELDI mi          : {on_yayin_duzeldi}")
    print(f"  BUGUNUN yarim bari yazildi mi    : {bugun_yazildi}   (istenmeyen)")
    print(f"  IMKANSIZ bar yazildi mi          : {imkansiz_yazildi}   (istenmeyen)")
    print(f"  dosyadaki butunluk ihlali sayisi : {ihlal}")
    return on_yayin_duzeldi, bugun_yazildi, imkansiz_yazildi, ihlal


e_duz, e_bugun, e_imk, e_ihlal = denetle("ESKI KOD (salt-ekleme)", yaz_ESKI)
y_duz, y_bugun, y_imk, y_ihlal = denetle("YENI KOD (revizyon penceresi)", yaz_YENI)

print("\n===== SONUC =====")
print(f"  ESKI: on-yayin duzeldi={e_duz} bugun_yazildi={e_bugun} "
      f"imkansiz_yazildi={e_imk} ihlal={e_ihlal}")
print(f"  YENI: on-yayin duzeldi={y_duz} bugun_yazildi={y_bugun} "
      f"imkansiz_yazildi={y_imk} ihlal={y_ihlal}")

beklenen_eski = (e_duz, e_bugun, e_imk, e_ihlal) == (False, True, True, 2)
beklenen_yeni = (y_duz, y_bugun, y_imk, y_ihlal) == (True, False, False, 0)
print(f"\n  ESKI kod beklenen sekilde HATALI mi : {beklenen_eski}   (beklenen: True)")
print(f"  YENI kod beklenen sekilde DOGRU mu  : {beklenen_yeni}   (beklenen: True)")
print("\nTEST: " + ("PASS" if (beklenen_eski and beklenen_yeni) else "FAIL"))
raise SystemExit(0 if (beklenen_eski and beklenen_yeni) else 1)
