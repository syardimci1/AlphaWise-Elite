"""
ALPHAWISE - Finnhub istemcisi (resmi finnhub-python kutuphanesi).

ANAHTAR HAVUZU: FINNHUB_API_KEY_1..4 — saa/src/main.py'deki mevcut
round-robin desenin aynisi. Bir anahtar 429 alirsa digerine gecilir.
Mevcut servislere DOKUNULMADI; desen yalnizca tekrar edildi.

UCRETSIZ KATMANDA NE CALISIR — 23.08.2026'da CANLI OLCULDU:
    /quote             HTTP 200  (94 B)
    /company-news      HTTP 200  (59 KB)
    /calendar/earnings HTTP 200  (4,8 KB)
    /stock/metric      HTTP 200  (242 KB)
    /news?category=... HTTP 200  — ama 'general' kategorisi BOS dizi
                       dondurdu, 'forex' 1,1 KB gercek veri dondurdu.
    /calendar/economic HTTP 403  {"error":"You don't have access..."}
    /forex/rates       HTTP 403  (ayni)
    /crypto/candle     HTTP 403  (ayni)

Yani ekonomik takvim ve doviz/kripto UCRETSIZ KATMANDA YOK. Bu servis
403 donen uclara HIC dokunmaz — bosuna kota yakmamak icin.
"""
import logging
import os
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import finnhub

from .kota import DakikaSayaci, KotaDoldu

logger = logging.getLogger("finnhub-signal.client")

# Kutuphane ic loglarinda jeton gorunmesin.
logging.getLogger("finnhub").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

HABER_GUN = 7
BILANCO_ILERI_GUN = 120


def _anahtarlar() -> list:
    ks = []
    for i in range(1, 5):
        k = os.getenv(f"FINNHUB_API_KEY_{i}")
        if k:
            ks.append(k)
    return ks


_ANAHTARLAR = _anahtarlar()

# ROTASYON NEDEN 0'DAN DEGIL 1'DEN BASLIYOR (olculdu):
# news-monitor 7/24 calisan bir dongude 11 hisselik listesini her 60
# saniyede tariyor ve rotasyon YAPMIYOR — her cagriyi ANAHTAR #1 ile
# yapiyor, ustelik ayni anahtarla surekli acik bir WebSocket tutuyor.
# Canli olcumumuz bunu dogruladi: anahtar #1'in "remaining" degeri biz
# arada tek istek yaparken 59'dan 48'e dustu.
# Bu yuzden bu servis rotasyona #2'den baslar; #1 ancak digerleri 429
# verirse, yani en son sirada kullanilir. Boylece surekli yuk altindaki
# anahtara gereksiz baski yapilmaz.
_sira = 1 if len(_ANAHTARLAR) > 1 else 0

_SAYAC = DakikaSayaci()


def anahtar_durumu() -> dict:
    """Anahtarlarin varligini bildirir — DEGERLERI ASLA sizdirmadan."""
    return {
        "havuz_boyutu": len(_ANAHTARLAR),
        "uzunluklar": [len(k) for k in _ANAHTARLAR],
    }


def sayac() -> DakikaSayaci:
    return _SAYAC


def _sonraki_anahtar() -> Optional[str]:
    global _sira
    if not _ANAHTARLAR:
        return None
    k = _ANAHTARLAR[_sira % len(_ANAHTARLAR)]
    _sira += 1
    return k


def _cagir(metot_adi: str, *args, **kwargs):
    """
    Kota bekcisinden gecerek Finnhub cagrisi yapar.

    Butce dolmussa AG CAGRISI YAPILMADAN KotaDoldu yukseltilir — boylece
    reddedilen istek havuzdan jeton yakmaz.

    429'da siradaki anahtara gecilir; her anahtar en fazla bir kez denenir.
    Anahtar degistirmek YENI bir Finnhub cagrisi demektir, bu yuzden her
    deneme ayri ayri sayaca islenir.
    """
    if not _ANAHTARLAR:
        raise RuntimeError("FINNHUB_API_KEY_1..4 tanimli degil")

    son_hata = None
    for _ in range(len(_ANAHTARLAR)):
        if not _SAYAC.izin_var():
            raise KotaDoldu(
                f"Bu servisin dakikalik Finnhub payi doldu "
                f"({_SAYAC.kullanilan()}/{_SAYAC.butce}); cagri yapilmadi."
            )
        key = _sonraki_anahtar()
        istemci = finnhub.Client(api_key=key)
        try:
            _SAYAC.harca()
            return getattr(istemci, metot_adi)(*args, **kwargs)
        except finnhub.FinnhubAPIException as e:
            son_hata = e
            if getattr(e, "status_code", None) == 429:
                logger.warning("Finnhub 429 — siradaki anahtara geciliyor")
                continue
            raise
        finally:
            # Kutuphane requests.Session aciyor; sizinti olmasin.
            try:
                istemci.close()
            except Exception:
                pass
    raise RuntimeError(f"Tum anahtarlar hiz limitine takildi: {son_hata}")


def anlik_fiyat(ticker: str) -> dict:
    """/quote — anlik fiyat anlik gorunumu."""
    d = _cagir("quote", ticker)
    if not d or d.get("c") in (None, 0):
        return {"veri_var": False}
    return {
        "veri_var": True,
        "son": d.get("c"),
        "degisim": d.get("d"),
        "degisim_yuzde": d.get("dp"),
        "gun_yuksek": d.get("h"),
        "gun_dusuk": d.get("l"),
        "acilis": d.get("o"),
        "onceki_kapanis": d.get("pc"),
    }


def haberler(ticker: str, azami: int = 3) -> dict:
    """/company-news — son HABER_GUN gunun basliklari."""
    bugun = datetime.now(timezone.utc).date()
    bas = bugun - timedelta(days=HABER_GUN)
    liste = _cagir("company_news", ticker, _from=str(bas), to=str(bugun)) or []
    secili = []
    for h in liste[:azami]:
        ts = h.get("datetime")
        secili.append({
            "baslik": h.get("headline"),
            "kaynak": h.get("source"),
            "url": h.get("url"),
            "zaman_utc": (datetime.fromtimestamp(ts, timezone.utc).isoformat()
                          if isinstance(ts, (int, float)) and ts else None),
        })
    return {
        "pencere_gun": HABER_GUN,
        "toplam_adet": len(liste),
        "secili_basliklar": secili,
    }


def bilanco_takvimi(ticker: str) -> dict:
    """/calendar/earnings — bir sonraki bilanco tarihi (varsa)."""
    bugun = datetime.now(timezone.utc).date()
    ileri = bugun + timedelta(days=BILANCO_ILERI_GUN)
    d = _cagir("earnings_calendar", _from=str(bugun), to=str(ileri),
               symbol=ticker, international=False) or {}
    kayitlar = d.get("earningsCalendar") or []
    kayitlar = [k for k in kayitlar if k.get("date")]
    kayitlar.sort(key=lambda k: k["date"])
    if not kayitlar:
        return {"yaklasan_var": False, "pencere_gun": BILANCO_ILERI_GUN}
    ilk = kayitlar[0]
    try:
        kalan = (date.fromisoformat(ilk["date"]) - bugun).days
    except (ValueError, TypeError):
        kalan = None
    return {
        "yaklasan_var": True,
        "pencere_gun": BILANCO_ILERI_GUN,
        "tarih": ilk.get("date"),
        "kalan_gun": kalan,
        "seans": ilk.get("hour") or None,
        "ceyrek": ilk.get("quarter"),
        "yil": ilk.get("year"),
        "eps_beklentisi": ilk.get("epsEstimate"),
    }


# /stock/metric yaniti 242 KB; tamami tasinmaz, yalnizca bu alanlar okunur.
ILGILI_METRIKLER = {
    "yil_zirvesi": "52WeekHigh",
    "yil_dibi": "52WeekLow",
    "beta": "beta",
    "fk_orani": "peTTM",
    "yil_getirisi_yuzde": "52WeekPriceReturnDaily",
}


def temel_metrikler(ticker: str) -> dict:
    """/stock/metric — yalnizca secili alanlar."""
    d = _cagir("company_basic_financials", ticker, "all") or {}
    m = d.get("metric") or {}
    return {tr: m.get(en) for tr, en in ILGILI_METRIKLER.items()}
