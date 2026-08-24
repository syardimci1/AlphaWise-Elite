"""
ALPHAWISE - FRED Makro Servisi / veri istemcisi.

=======================================================================
NEDEN AYRI BIR SERVIS — CAKISMA ANALIZI (23.08.2026'da OLCULDU)
=======================================================================
FRED_API_KEY sistemde zaten IKI yerde kullaniliyor. Yeni bir tuketici
eklemeden once ikisinin de NE cektigi tek tek okundu:

  1) liquidity-signal-service/src/fred_client.py -> FRED_SERIES:
     WALCL, WTREGEN, RRPONTSYD, M2SL, NASDAQCOM, SP500, CBBTCUSD
     Yani: Fed BILANCO/LIKIDITE tesisati. Ayrica o servis kalibrasyonu
     BASARISIZ oldugu icin lambda=0'da duruyor ve yon iddiasi tasiyan
     kod uretmiyor. BU SERVIS ONA HIC DOKUNMAZ.

  2) maa/src/main.py -> FRED_SERIES (KORUNAN DOSYA, yalnizca okundu):
     FEDFUNDS, DGS10, CPIAUCSL, UNRATE
     Yani: LLM kaskadina beslenen makro baglam. Dashboard'da kart olarak
     GORUNMUYOR.

Bu servisin serilerinin ikisiyle de KESISIMI SIFIRDIR:
     T10Y2Y, PCEPILFE, PAYEMS, ICSA, UMCSENT, DTWEXBGS
Secim bilincli: MAA zaten "bariz dortlu"yu (politika faizi, 10Y, TUFE,
issizlik) aldigi icin burada onlar TEKRAR EDILMEDI; onun yerine sistemde
hic olmayan getiri egrisi farki, Fed'in gercek hedef olcusu cekirdek PCE,
tarim disi istihdam, haftalik issizlik basvurulari, tuketici guveni ve
genis dolar endeksi alindi.

=======================================================================
TAKVIM: fredapi BUNU SARMALAMIYOR (olculdu)
=======================================================================
fredapi 0.5.2'nin TUM metotlari canli introspection ile listelendi:
  get_series, get_series_all_releases, get_series_as_of_date,
  get_series_first_release, get_series_info, get_series_latest_release,
  get_series_vintage_dates, search, search_by_category, search_by_release
Yani ILERI TARIHLI yayin takvimi icin bir metot YOK. Gostergeler
fredapi ile cekilir (gorevin istedigi gibi); resmi takvim icin FRED'in
kendi /fred/releases/dates ucu httpx ile okunur. Bu uc ayni anahtarla
calisiyor (dogrulandi: 45 gunluk pencerede 1311 kayit dondu).

ONBELLEK: onek 'fms:' — liquidity-signal 'lss:' kullaniyor, cakismaz.
"""
import json
import logging
import os
import socket
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import httpx
import redis
from fredapi import Fred

# ---------------------------------------------------------------------------
# fredapi'NIN ZAMAN ASIMI YOK — SURECI KORUYAN TEK ONLEM BU SATIR
# ---------------------------------------------------------------------------
# fredapi 0.5.2 tum ag cagrisini tek bir yerde, stdlib urlopen ile yapar:
#     response = urlopen(url)          # fred.py, __fetch_data
# Bu cagriya timeout GECILMIYOR. Python'un varsayilani None'dir, yani
# FRED yavaslar ya da asilirsa cagri SURESIZ bekler. Bu servisin uclari
# senkron 'def' oldugu icin Starlette onlari thread havuzunda calistirir;
# asili kalan her istek havuzdan bir thread'i kalici olarak yer ve yeterli
# sayida istek birikirse SERVIS TAMAMEN CEVAP VEREMEZ HALE GELIR.
#
# Kutuphaneye parametre gecirmenin yolu olmadigi icin surec genelinde
# varsayilan soket zaman asimi kuruluyor; urlopen bu degeri devralir.
# (httpx ile yapilan takvim cagrisi zaten kendi timeout'unu tasiyor.)
socket.setdefaulttimeout(float(os.getenv("FRED_TIMEOUT", "30")))

logger = logging.getLogger("fred-macro.client")
# GUVENLIK: httpx INFO seviyesinde tam URL loglar ve api_key query
# parametresinde gorunur. liquidity-signal'de de ayni onlem alinmisti.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

FRED_REST = "https://api.stlouisfed.org/fred"
ZAMAN_ASIMI = float(os.getenv("FRED_TIMEOUT", "30"))
ONEK = "fms:"

# Gosterge -> (FRED seri kimligi, insan okunur ad, birim)
GOSTERGELER = {
    "getiri_egrisi": ("T10Y2Y", "10Y-2Y getiri farki", "yuzde puan"),
    "cekirdek_pce": ("PCEPILFE", "Cekirdek PCE fiyat endeksi", "endeks (2017=100)"),
    "tarim_disi_istihdam": ("PAYEMS", "Tarim disi toplam istihdam", "bin kisi"),
    "issizlik_basvurulari": ("ICSA", "Haftalik ilk issizlik basvurulari", "kisi"),
    "tuketici_guveni": ("UMCSENT", "Michigan tuketici guveni", "endeks"),
    "dolar_endeksi": ("DTWEXBGS", "Genis dolar endeksi", "endeks (2006=100)"),
}

# Takvimde izlenen FRED yayinlari. Kimlikler canli /fred/releases
# sorgusuyla dogrulandi (23.08.2026).
TAKVIM_YAYINLARI = {
    10: "Tuketici Fiyat Endeksi (TUFE)",
    50: "Istihdam Durumu Raporu",
    54: "Kisisel Gelir ve Harcamalar (PCE)",
    53: "Gayri Safi Yurt Ici Hasila (GSYH)",
    46: "Uretici Fiyat Endeksi (UFE)",
    20: "H.4.1 Fed Bilancosu",
    192: "Acik Pozisyon ve Isgucu Devri (JOLTS)",
    9: "Perakende Satislar (on veri)",
}

_redis_istemci = None
_fred = None


def _get_redis():
    global _redis_istemci
    if _redis_istemci is None:
        _redis_istemci = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD") or None,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
    return _redis_istemci


def _onbellek_al(anahtar: str):
    try:
        v = _get_redis().get(ONEK + anahtar)
        return json.loads(v) if v else None
    except Exception:
        return None


def _onbellek_yaz(anahtar: str, deger, saniye: int):
    try:
        _get_redis().setex(ONEK + anahtar, saniye, json.dumps(deger))
    except Exception:
        pass


def redis_durumu() -> dict:
    try:
        _get_redis().ping()
        return {"bagli": True}
    except Exception as e:
        return {"bagli": False, "detay": str(e)[:200]}


def _anahtar() -> Optional[str]:
    return os.getenv("FRED_API_KEY")


def anahtar_durumu() -> dict:
    """Anahtarin varligini bildirir — DEGERINI sizdirmadan."""
    k = _anahtar()
    if not k:
        return {"tanimli": False, "uzunluk": 0}
    return {"tanimli": True, "uzunluk": len(k), "beklenen_format": len(k) == 32}


def _fred_istemci() -> Fred:
    global _fred
    if _fred is None:
        k = _anahtar()
        if not k:
            raise RuntimeError("FRED_API_KEY tanimli degil")
        _fred = Fred(api_key=k)
    return _fred


def _sayisal(x):
    """pandas/numpy degerini duz Python sayisina cevirir; NaN -> None."""
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


def gosterge_oku(kod: str) -> dict:
    """
    Tek bir gostergeyi fredapi ile ceker.

    Onbellek 6 saat: bu serilerin en sik olani GUNLUK (T10Y2Y, DTWEXBGS),
    en seyregi AYLIK. 6 saat, gun ici gereksiz tekrar cagriyi keser ama
    yeni yayini ayni gun icinde yakalar.
    """
    seri_id, ad, birim = GOSTERGELER[kod]
    onbellekli = _onbellek_al(f"gosterge:{seri_id}")
    if onbellekli is not None:
        onbellekli["onbellekten"] = True
        return onbellekli

    f = _fred_istemci()
    seri = f.get_series(seri_id)          # pandas Series
    bilgi = f.get_series_info(seri_id)    # pandas Series (metadata)

    seri = seri.dropna()
    if len(seri) == 0:
        sonuc = {"kod": kod, "seri_id": seri_id, "ad": ad, "veri_var": False}
        _onbellek_yaz(f"gosterge:{seri_id}", sonuc, 3600)
        return sonuc

    son_deger = _sayisal(seri.iloc[-1])
    onceki = _sayisal(seri.iloc[-2]) if len(seri) > 1 else None
    yil_once = None
    try:
        hedef = seri.index[-1] - timedelta(days=365)
        gecmis = seri[seri.index <= hedef]
        if len(gecmis) > 0:
            yil_once = _sayisal(gecmis.iloc[-1])
    except Exception:
        yil_once = None

    sonuc = {
        "kod": kod,
        "seri_id": seri_id,
        "ad": ad,
        "birim": birim,
        "veri_var": True,
        "son_deger": son_deger,
        "son_tarih": str(seri.index[-1].date()),
        "onceki_deger": onceki,
        "onceki_farki": (round(son_deger - onceki, 4)
                         if son_deger is not None and onceki is not None else None),
        "bir_yil_onceki": yil_once,
        "yillik_degisim_yuzde": (
            round((son_deger - yil_once) / abs(yil_once) * 100, 2)
            if son_deger is not None and yil_once not in (None, 0) else None
        ),
        "gozlem_sayisi": int(len(seri)),
        "kaynak_son_guncelleme": str(bilgi.get("last_updated", ""))[:19],
        "frekans": str(bilgi.get("frequency_short", "")),
        "onbellekten": False,
    }
    _onbellek_yaz(f"gosterge:{seri_id}", sonuc, 6 * 3600)
    return sonuc


def tum_gostergeler() -> list:
    cikti = []
    for kod in GOSTERGELER:
        try:
            cikti.append(gosterge_oku(kod))
        except Exception as e:
            logger.warning("Gosterge %s cekilemedi: %s: %s", kod, type(e).__name__, e)
            cikti.append({"kod": kod, "seri_id": GOSTERGELER[kod][0],
                          "ad": GOSTERGELER[kod][1], "veri_var": False,
                          "hata": type(e).__name__})
    return cikti


def yaklasan_yayinlar(gun: int = 30) -> dict:
    """
    Resmi FRED yayin takvimi — ILERI TARIHLI.

    fredapi bu ucu sarmalamadigi icin (metot listesi modul basliginda)
    dogrudan /fred/releases/dates okunur. Yalnizca TAKVIM_YAYINLARI'ndaki
    kilit yayinlar tutulur: ham uc 45 gunluk pencerede 1311 kayit
    donduruyor ve bunun buyuk cogunlugu dashboard icin gurultu.
    """
    onbellekli = _onbellek_al(f"takvim:{gun}")
    if onbellekli is not None:
        onbellekli["onbellekten"] = True
        return onbellekli

    k = _anahtar()
    if not k:
        raise RuntimeError("FRED_API_KEY tanimli degil")

    bugun = datetime.now(timezone.utc).date()
    bitis = bugun + timedelta(days=gun)
    with httpx.Client(timeout=ZAMAN_ASIMI) as c:
        r = c.get(f"{FRED_REST}/releases/dates", params={
            "api_key": k, "file_type": "json",
            "realtime_start": str(bugun), "realtime_end": str(bitis),
            "include_release_dates_with_no_data": "true",
            "sort_order": "asc", "limit": 1000,
        })
    if r.status_code != 200:
        raise RuntimeError(f"FRED takvim HTTP {r.status_code}")

    kayitlar = []
    for x in r.json().get("release_dates", []):
        rid = x.get("release_id")
        if rid not in TAKVIM_YAYINLARI:
            continue
        try:
            kalan = (date.fromisoformat(x["date"]) - bugun).days
        except (ValueError, KeyError, TypeError):
            kalan = None
        kayitlar.append({
            "tarih": x.get("date"),
            "kalan_gun": kalan,
            "yayin_id": rid,
            "yayin_adi": TAKVIM_YAYINLARI[rid],
        })
    kayitlar.sort(key=lambda z: (z["tarih"] or "", z["yayin_id"]))

    sonuc = {
        "pencere_gun": gun,
        "bugun_utc": str(bugun),
        "izlenen_yayin_sayisi": len(TAKVIM_YAYINLARI),
        "yaklasan": kayitlar,
        "adet": len(kayitlar),
        "onbellekten": False,
    }
    # Takvim gun icinde degismez; 12 saat yeterli.
    _onbellek_yaz(f"takvim:{gun}", sonuc, 12 * 3600)
    return sonuc
