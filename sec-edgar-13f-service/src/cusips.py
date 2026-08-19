"""
Ticker -> CUSIP cozumleme.

=======================================================================
NEDEN ACIK HARITA GEREKLI (SADECE ISIM ESLESTIRME YETMEZ)
=======================================================================
13F bilgi tablolari hisseyi TICKER ile degil CUSIP ile tanimlar.
Ticker'i CUSIP'e cevirmek icin SEC'in company_tickers.json'undaki
sirket adiyla 13F'teki nameOfIssuer'i eslestirmek ilk akla gelen
yoldur — ama gercek veri uzerinde denendiginde KIRILIYOR
(2026-08-19, BlackRock 2026-06-30 dosyasi, 49.968 satir):

  AMZN : SEC adi "AMAZON COM INC". " CO" son eki temizlenince
         "AMAZON M" kaliyor -> eslesme yok.
  XOM  : SEC adi "ExxonMobil Holdings Corp", 13F adi
         "EXXON MOBIL CORP" -> bosluk farki yuzunden eslesmiyor.
  GOOGL: "ALPHABET" uc ayri CUSIP'e cikiyor (02079K107 / 02079K305 /
         02079K907) -> hangi sinif oldugu isimden anlasilmiyor.
  BAC  : 13F adi "BANK OF AMER CORP" (AMERICA degil AMER kisaltmasi).

Bu yuzden CIK'lerde oldugu gibi burada da ACIK, DOGRULANMIS bir harita
tutulur. Asagidaki her CUSIP, BlackRock'un 2026-06-30 donemli gercek
13F bilgi tablosundan (accession 0002012383-26-003238) cikarilmis ve
tek tek dogrulanmistir — elle tahmin edilmemistir.

Harita disindaki ticker'lar icin isim eslestirme YEDEK olarak calisir,
ama sonuc "dogrulanmadi" bayragiyla doner; sessizce kesin gibi
sunulmaz.
"""
import re

# ticker -> (cusip, 13F'teki isim, sinif)
# Kaynak: BlackRock 13F-HR, donem 2026-06-30, accession 0002012383-26-003238
# Cikarim tarihi: 2026-08-19
DOGRULANMIS = {
    "NVDA":  ("67066G104", "NVIDIA CORPORATION", "COM"),
    "AAPL":  ("037833100", "APPLE INC", "COM"),
    "MSFT":  ("594918104", "MICROSOFT CORP", "COM"),
    "AMZN":  ("023135106", "AMAZON COM INC", "COM"),
    "GOOGL": ("02079K305", "ALPHABET INC", "CAP STK CL A"),
    "GOOG":  ("02079K107", "ALPHABET INC", "CAP STK CL C"),
    "META":  ("30303M102", "META PLATFORMS INC", "CL A"),
    "TSLA":  ("88160R101", "TESLA INC", "COM"),
    "AVGO":  ("11135F101", "BROADCOM INC", "COM"),
    "JPM":   ("46625H100", "JPMORGAN CHASE & CO", "COM"),
    "XOM":   ("30231G102", "EXXON MOBIL CORP", "COM"),
    "UNH":   ("91324P102", "UNITEDHEALTH GROUP INC", "COM"),
    "JNJ":   ("478160104", "JOHNSON & JOHNSON", "COM"),
    "WMT":   ("931142103", "WALMART INC", "COM"),
    "PG":    ("742718109", "PROCTER & GAMBLE CO", "COM"),
    "V":     ("92826C839", "VISA INC", "COM CL A"),
    "HD":    ("437076102", "HOME DEPOT INC", "COM"),
    "KO":    ("191216100", "COCA COLA CO", "COM"),
    "CVX":   ("166764100", "CHEVRON CORPORATION", "COM"),
    "MRK":   ("58933Y105", "MERCK & CO INC", "COM"),
    "BAC":   ("060505104", "BANK OF AMER CORP", "COM"),
    "DIS":   ("254687106", "DISNEY WALT CO", "COM"),
    "NFLX":  ("64110L106", "NETFLIX INC.", "COM"),
    "ORCL":  ("68389X105", "ORACLE CORP", "COM"),
    "CAT":   ("149123101", "CATERPILLAR INC", "COM"),
    "BA":    ("097023105", "BOEING CO", "COM"),
}

# Isim eslestirme yedeginde kullanilan sirket-turu son ekleri.
# Kelime SINIRIYLA silinir; "AMAZON COM" -> "AMAZON M" hatasi bu yuzden olusmustu.
_SON_EKLER = [
    "INCORPORATED", "CORPORATION", "HOLDINGS", "COMPANY", "GROUP",
    "CORP", "INC", "PLC", "LTD", "LLC", "LP", "CO", "THE", "NEW",
]


def normalize_ad(s: str) -> str:
    """Sirket adini eslestirme icin sadelestirir (kelime siniriyla)."""
    s = (s or "").upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    kelimeler = [k for k in s.split() if k and k not in _SON_EKLER]
    return " ".join(kelimeler)


def coz(ticker: str) -> dict:
    """
    Ticker -> CUSIP. Dogrulanmis haritada varsa kesin sonuc doner.

    Donen:
      {"bulundu": True, "cusip": ..., "isim": ..., "sinif": ...,
       "kaynak": "dogrulanmis_harita", "dogrulandi": True}
      {"bulundu": False, "isim_anahtari": ..., "dogrulandi": False}
    """
    tk = (ticker or "").upper().strip()
    if tk in DOGRULANMIS:
        cusip, isim, sinif = DOGRULANMIS[tk]
        return {
            "bulundu": True,
            "cusip": cusip,
            "isim": isim,
            "sinif": sinif,
            "kaynak": "dogrulanmis_harita",
            "dogrulandi": True,
            "not": ("CUSIP, gercek bir SEC 13F bilgi tablosundan cikarilip "
                    "dogrulandi (BlackRock 2026-06-30)."),
        }
    return {
        "bulundu": False,
        "dogrulandi": False,
        "isim_anahtari": None,
        "not": (f"{tk} dogrulanmis CUSIP haritasinda yok. Bilgi tablosunda "
                "isim eslestirmesi denenecek; sonuc dogrulanmamis sayilir."),
    }


def isimle_ara(hedef_ad: str, tablo_isimleri: dict) -> dict:
    """
    YEDEK yol: bilgi tablosundaki isimler icinde arar.

    tablo_isimleri: {normalize_ad: {cusip, ...}}
    Sonuc her zaman dogrulandi=False tasir.
    """
    anahtar = normalize_ad(hedef_ad)
    if not anahtar:
        return {"bulundu": False, "dogrulandi": False}
    adaylar = tablo_isimleri.get(anahtar)
    if not adaylar:
        # parcali eslesme
        for k, v in tablo_isimleri.items():
            if anahtar and (anahtar in k or k in anahtar):
                adaylar = v
                anahtar = k
                break
    if not adaylar:
        return {"bulundu": False, "dogrulandi": False, "isim_anahtari": anahtar}
    return {
        "bulundu": True,
        "cusip": sorted(adaylar)[0],
        "tum_adaylar": sorted(adaylar),
        "isim_anahtari": anahtar,
        "kaynak": "isim_eslestirme_yedegi",
        "dogrulandi": False,
        "not": ("Bu CUSIP isim benzerliginden turetildi, dogrulanmis haritada "
                "yok. Birden fazla aday varsa hisse sinifi ayrimi yapilamamis "
                "olabilir."),
    }
