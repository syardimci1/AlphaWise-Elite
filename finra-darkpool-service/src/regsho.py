"""
FINRA GUNLUK Reg SHO kisa-satis hacmi (23.08.2026) — Faz 2 / C1.

MEVCUT HAFTALIK ATS (DPKE) MODULUNE DOKUNULMAZ. Bu, onun YANINA eklenen
AYRI bir veri kumesidir:

  mevcut: otcMarket/weeklySummary  -> HAFTALIK, 21-27 gun gecikmeli
  yeni  : equity/regsho/daily      -> GUNLUK, T+1 (olculdu: 21 Agustos
          dosyasi 23 Agustos'ta indi)

Kaynak: https://cdn.finra.org/equity/regsho/daily/CNMSshvol{YYYYMMDD}.txt
Ucretsiz, API anahtari GEREKTIRMEZ, boru-ayrilmis metin:
    Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market

DURUSTLUK NOTU — bu ne DEGILDIR:
  * "Kisa hacim orani" ACIK KISA POZISYON (short interest) DEGILDIR.
    Gunluk konsolide hacmin ne kadarinin "short" isaretlendigini olcer;
    icinde piyasa yapicilarin korunma (hedge) islemleri de vardir ve bu
    pay buyuk hisselerde yapisal olarak %40-55 bandindadir.
  * Yon iddiasi tasimaz; bu sistemde KALIBRE EDILMEMISTIR.
"""
import io
import os
from datetime import date, timedelta

import httpx

from .finra import _cache_get, _cache_set  # ayni onbellek disiplini

TABAN = "https://cdn.finra.org/equity/regsho/daily"
HTTP_TIMEOUT = float(os.getenv("REGSHO_TIMEOUT", "45"))
# Yayimlanan gunluk dosya DEGISMEZ -> uzun TTL guvenli.
TTL_GUN_DOSYASI = int(os.getenv("REGSHO_TTL", str(7 * 24 * 3600)))
KALIBRASYON_GECERLI = False


def _url(g: date) -> str:
    return f"{TABAN}/CNMSshvol{g.strftime('%Y%m%d')}.txt"


async def _gun_dosyasi(g: date) -> dict | None:
    """Bir gunun tum sembollerini {sembol: (short, exempt, toplam)} dondurur.

    Dosya yoksa (hafta sonu/tatil/henuz yayimlanmadi) None doner.
    """
    anahtar = f"regsho:{g.isoformat()}"
    onbellek = _cache_get(anahtar)
    if onbellek is not None:
        return onbellek or None

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.get(_url(g))
    if r.status_code != 200 or len(r.content) < 200:
        _cache_set(anahtar, {}, 3600)          # yok: kisa TTL (yayimlanabilir)
        return None

    kayitlar = {}
    for satir in io.StringIO(r.text):
        p = satir.rstrip("\n").split("|")
        if len(p) < 5 or p[0] == "Date":
            continue
        try:
            kayitlar[p[1].upper()] = (float(p[2]), float(p[3]), float(p[4]))
        except ValueError:
            continue
    if kayitlar:
        _cache_set(anahtar, kayitlar, TTL_GUN_DOSYASI)
    return kayitlar or None


def _oran(short: float, toplam: float):
    return round(short / toplam * 100, 2) if toplam else None


async def son_gunler(ticker: str, gun: int = 10, geriye_bak: int = 20) -> dict:
    """Son `gun` yayimlanmis is gunu icin kisa hacim orani."""
    ticker = ticker.upper()
    bugun = date.today()
    satirlar = []
    bakilan = 0
    g = bugun
    while len(satirlar) < gun and bakilan < geriye_bak:
        bakilan += 1
        g -= timedelta(days=1)
        if g.weekday() >= 5:                    # hafta sonu
            continue
        veri = await _gun_dosyasi(g)
        if not veri:
            continue
        k = veri.get(ticker)
        if not k:
            continue
        short, exempt, toplam = k
        satirlar.append({
            "tarih": g.isoformat(),
            "kisa_hacim": short,
            "kisa_muaf_hacim": exempt,
            "toplam_hacim": toplam,
            "kisa_hacim_orani_yuzde": _oran(short, toplam),
        })

    oranlar = [s["kisa_hacim_orani_yuzde"] for s in satirlar
               if s["kisa_hacim_orani_yuzde"] is not None]
    ortalama = round(sum(oranlar) / len(oranlar), 2) if oranlar else None
    return {
        "ticker": ticker,
        "kaynak": "FINRA Reg SHO gunluk (CNMS konsolide) — ucretsiz, anahtarsiz",
        "gun_sayisi": len(satirlar),
        "en_yeni_gun": satirlar[0]["tarih"] if satirlar else None,
        "en_yeni_kisa_hacim_orani_yuzde": (satirlar[0]["kisa_hacim_orani_yuzde"]
                                           if satirlar else None),
        "ortalama_kisa_hacim_orani_yuzde": ortalama,
        "gunler": satirlar,
        "kalibrasyon_gecerli": KALIBRASYON_GECERLI,
        "not": ("Bu oran ACIK KISA POZISYON (short interest) DEGILDIR; gunluk "
                "konsolide hacmin short isaretlenen payidir ve piyasa yapici "
                "korunma islemlerini de icerir. Buyuk hisselerde yapisal olarak "
                "%40-55 bandinda seyreder. Yon iddiasi tasimaz."),
    }


async def kaynak_durumu() -> dict:
    """En yeni kac gunun dosyasinin yayimlandigini olcer (teshis)."""
    bugun = date.today()
    bulunan = []
    g = bugun
    for _ in range(10):
        g -= timedelta(days=1)
        if g.weekday() >= 5:
            continue
        if await _gun_dosyasi(g):
            bulunan.append(g.isoformat())
        if len(bulunan) >= 3:
            break
    return {
        "yayimlanmis_son_gunler": bulunan,
        "gecikme_notu": ("Gunluk dosya T+1 yayimlanir; haftalik ATS verisi ise "
                         "21-27 gun gecikmelidir."),
        "api_anahtari_gerekli": False,
    }
