"""DBnomics — FRED icin ANAHTARSIZ yedek kaynak (yalnizca DOGRULANMIS seriler).

NEDEN
=====
fred_client.py FRED_API_KEY olmadan calismaz. DBnomics ayni verinin bir
kismini anahtarsiz sunuyor ve olculdu: Fed bilanco toplaminda degerler
BIREBIR ayni, ustelik daha taze.

DOGRULANMAYAN SERI EKLENMEZ
===========================
Bu modulun tek kurali sudur: bir eslesme, DEGERLERI karsilastirilarak
dogrulanmadan tabloya girmez. "Ayni seri adi" ile "ayni deger" ayni sey
DEGILDIR ve bu somut olarak olculdu (10.09.2026):

  WALCL -> FED/H41/RESPPA_N.WW
      6 ortak tarihte fark 0 (birebir)  ->  DOGRULANDI
      DBnomics ayrica DAHA TAZE: 2026-09-02 vs FRED onbellek 2026-08-12
  M2SL  -> FED/H6_H6_M2/M2.M
      ayni aylarda fark -21,4 / -35,7 / -43,2  ->  DOGRULANMADI (surum farki)
  WTREGEN (TGA), RRPONTSYD (RRP)
      FED/H41'in turev olmayan 258 serisi DEGER uzerinden tarandi,
      eslesen bulunamadi  ->  KAYNAKTA YOK

Bu yuzden tablo tek bir seri tasiyor. Az ama kanitli; tahmine dayali bir
eslesme, sessizce yanlis makro veri beslerdi.
"""
from __future__ import annotations

import os

import httpx

TABAN = os.getenv("DBNOMICS_BASE", "https://api.db.nomics.world/v22")
HTTP_TIMEOUT = float(os.getenv("DBNOMICS_TIMEOUT", "45"))

# FRED seri kodu -> (DBnomics yolu, dogrulama kaniti)
# Kanit alani ZORUNLUDUR; dogrulanmamis eslesme buraya YAZILAMAZ.
DOGRULANMIS_ESLESME = {
    "WALCL": {
        "yol": "FED/H41/RESPPA_N.WW",
        "aciklama": "Fed toplam varliklari (H.4.1, haftalik Carsamba)",
        "dogrulama": {
            "tarih": "2026-09-10",
            "ortak_gozlem": 6,
            "azami_fark_yuzde": 0.0,
            "yontem": ("FRED onbellek verisiyle (calibration/fred_data.json) "
                       "ortak tarihlerde birebir karsilastirildi"),
        },
    },
}


class DBnomicsHatasi(Exception):
    """Kaynaga ulasilamadi ya da beklenen sema gelmedi."""


async def seri_getir(fred_kodu: str, gozlem: int = 0) -> list:
    """Dogrulanmis bir FRED serisini DBnomics'ten anahtarsiz ceker.

    Doner: [(tarih, deger), ...] — eskiden yeniye.
    Dogrulanmamis kod istendiginde TAHMIN EDILMEZ, hata firlatilir.
    """
    esl = DOGRULANMIS_ESLESME.get((fred_kodu or "").upper())
    if esl is None:
        raise DBnomicsHatasi(
            f"'{fred_kodu}' icin DOGRULANMIS bir DBnomics eslesmesi yok. "
            f"Tahmini bir eslesme kullanmak sessizce yanlis makro veri "
            f"beslerdi. Dogrulanmis kodlar: {sorted(DOGRULANMIS_ESLESME)}")
    url = f"{TABAN}/series/{esl['yol']}?observations=1"
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as c:
            r = await c.get(url)
    except Exception as e:
        raise DBnomicsHatasi(f"DBnomics'e ulasilamadi: {type(e).__name__}") from e
    if r.status_code != 200:
        raise DBnomicsHatasi(f"DBnomics HTTP {r.status_code}")
    try:
        govde = r.json()
    except Exception as e:
        raise DBnomicsHatasi("DBnomics JSON dondurmedi") from e
    return _gozlemleri_ayikla(govde, esl["yol"])


def _gozlemleri_ayikla(govde: dict, yol: str) -> list:
    docs = ((govde or {}).get("series") or {}).get("docs") or []
    if not docs:
        raise DBnomicsHatasi(f"{yol}: DBnomics bos sonuc dondu")
    d = docs[0]
    donemler = d.get("period") or []
    degerler = d.get("value") or []
    if not donemler or len(donemler) != len(degerler):
        raise DBnomicsHatasi(
            f"{yol}: period/value uzunluklari uyusmuyor "
            f"({len(donemler)}/{len(degerler)}) — sema degismis olabilir")
    # DBnomics eksik gozlemi None olarak verir; bunlari SIFIR yapmak
    # zaman serisini sessizce bozardi, atlanir.
    return [(p, float(v)) for p, v in zip(donemler, degerler) if v is not None]


def eslesme_durumu() -> dict:
    """Hangi FRED serileri anahtarsiz alinabiliyor (ve kaniti nedir)."""
    return {
        "kaynak": "DBnomics (api.db.nomics.world) — API ANAHTARI GEREKTIRMEZ",
        "dogrulanmis_seri_sayisi": len(DOGRULANMIS_ESLESME),
        "eslesmeler": {k: {"yol": v["yol"], "aciklama": v["aciklama"],
                           "dogrulama": v["dogrulama"]}
                       for k, v in DOGRULANMIS_ESLESME.items()},
        "not": ("Yalnizca DEGERLERI karsilastirilarak dogrulanmis seriler "
                "listelenir. 'Ayni seri adi' ile 'ayni deger' ayni sey "
                "DEGILDIR; M2 bu farkin somut ornegidir (bkz. modul basligi)."),
    }
