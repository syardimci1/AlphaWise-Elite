"""Borsa disi baski (dark pool print) hacminin konsolide hacme orani.

MEVCUT IKI VERI KUMESINE DE DOKUNULMAZ. Bu, onlarin yanina eklenen
UCUNCU olcumdur:

  haftalik ATS  (finra.py)  -> hangi ATS ne kadar isledi, 21-27 gun gecikmeli
  gunluk RegSHO (regsho.py) -> borsa disi hacmin ne kadari "short" isaretli
  BU MODUL                  -> borsa disi hacim, TOPLAM piyasa hacminin
                               yuzde kaci? (gunluk)

NEDEN AYRI BIR OLCUM
====================
regsho.py "short / borsa disi toplam" oranini verir; paydasi borsa disi
hacmin KENDISIDIR. Dolayisiyla borsa disi islem hacmi iki katina ciksa
bile o oran degismeyebilir. "Karanlik havuz aktivitesi arti mi" sorusu
bu oranla yanitlanamaz; payda konsolide hacim olmalidir.

PAYDA NEREDEN GELIYOR (ve neden sorun)
======================================
CNMSshvol dosyasindaki TotalVolume KONSOLIDE PIYASA HACMI DEGILDIR;
yalnizca FINRA'ya bildirilen (borsa disi) hacimdir. Bu, regsho.py
basliginda 24.08.2026'da olculerek belgelenmistir. Bu yuzden payda
DISARIDAN gelir: market-data-service'in gunluk barlarindaki hacim.

Iki kaynak farkli sistemlerden geldigi icin GUN GUN ESLESMEYEBILIR.
Olculdu (10.09.2026): FINRA gunluk dosyasi 2026-09-09'a kadar
yayimlanmisti, konsolide hacim deposu ise 2026-09-03'te bitiyordu -
bes is gunluk bosluk. Eslesmeyen gunler SESSIZCE ATILMAZ; "olculemedi"
olarak, gerekcesiyle birlikte raporlanir. Atilsalardi ortalama, yalnizca
iki kaynagin ortustugu gunlerden hesaplanmis olur ama okuyucu bunu
bilemezdi.

%100'DEN BUYUK ORAN BIR OLCUM DEGILDIR
======================================
Borsa disi hacim, tanimi geregi konsolide hacmin bir PARCASIDIR; oran
1'i asamaz. Astiginda bu, piyasanin bir davranisi degil, iki kaynagin
ayni seyi olcmedigi anlamina gelir (farkli tarih, farkli duzeltme
carpani, farkli sembol). Boyle bir deger kirpilmaz ve ortalamaya
katilmaz - VERI TUTARSIZLIGI olarak isaretlenir.

Olculen taban (2026-09-03, 10 buyuk sembol): pay %25,3 - %55,0,
ortalama %42,3, 100%'u asan yok.
"""
from __future__ import annotations

import os
from datetime import date, timedelta

import httpx

from .regsho import _gun_dosyasi

MARKET_DATA_URL = os.getenv("MARKET_DATA_URL", "http://alphawise-market-data:8000")
HTTP_TIMEOUT = float(os.getenv("BASKI_TIMEOUT", "30"))

OLCULDU = "olculdu"
OLCULEMEDI = "olculemedi"
TUTARSIZ = "tutarsiz"


async def _konsolide_hacimler(ticker: str) -> tuple[dict, str]:
    """market-data-service'ten {tarih: hacim} dondurur.

    Basarisizlikta BOS SOZLUK DEGIL, (bos, gerekce) doner ki cagiran
    "hacim yok" ile "ogrenemedik" arasindaki farki gorebilsin.
    """
    url = f"{MARKET_DATA_URL}/price/{ticker.upper()}"
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as c:
            r = await c.get(url)
    except Exception as e:
        return {}, f"market-data-service'e ulasilamadi: {type(e).__name__}"
    if r.status_code != 200:
        return {}, f"market-data-service HTTP {r.status_code}"
    try:
        govde = r.json()
    except Exception:
        return {}, "market-data-service JSON dondurmedi"
    if isinstance(govde, dict) and govde.get("error"):
        return {}, f"market-data-service hata bildirdi: {govde['error']}"
    barlar = (govde or {}).get("data") or []
    out = {}
    for b in barlar:
        t, h = b.get("date"), b.get("volume")
        if not t or h is None:
            continue
        try:
            h = float(h)
        except (TypeError, ValueError):
            continue
        if h > 0:
            out[t] = h
    if not out:
        return {}, "market-data-service hacim icermeyen yanit dondu"
    return out, ""


def _gun_kaydi(tarih: date, borsa_disi, konsolide, konsolide_gerekce):
    """Tek gunun kaydini uc durumlu kurar."""
    t = tarih.isoformat()
    if konsolide is None:
        return {"tarih": t, "borsa_disi_hacim": borsa_disi,
                "konsolide_hacim": None, "pay_yuzde": None,
                "durum": OLCULEMEDI,
                "gerekce": (konsolide_gerekce
                            or f"{t} icin konsolide hacim bulunamadi")}
    if konsolide <= 0:
        return {"tarih": t, "borsa_disi_hacim": borsa_disi,
                "konsolide_hacim": konsolide, "pay_yuzde": None,
                "durum": OLCULEMEDI,
                "gerekce": "konsolide hacim sifir ya da negatif; oran TANIMSIZ"}
    pay = borsa_disi / konsolide * 100.0
    if pay > 100.0:
        return {"tarih": t, "borsa_disi_hacim": borsa_disi,
                "konsolide_hacim": konsolide, "pay_yuzde": round(pay, 2),
                "durum": TUTARSIZ,
                "gerekce": ("borsa disi hacim konsolide hacmi asiyor; bu bir "
                            "piyasa davranisi degil, iki kaynagin ayni seyi "
                            "olcmedigini gosterir. Ortalamaya KATILMADI.")}
    return {"tarih": t, "borsa_disi_hacim": borsa_disi,
            "konsolide_hacim": konsolide, "pay_yuzde": round(pay, 2),
            "durum": OLCULDU, "gerekce": ""}


async def borsa_disi_pay(ticker: str, gun: int = 10,
                         geriye_bak: int = 20) -> dict:
    """Son `gun` yayimlanmis is gunu icin borsa disi hacim payi."""
    ticker = ticker.upper()
    konsolide, kons_gerekce = await _konsolide_hacimler(ticker)

    gunler = []
    bakilan = 0
    g = date.today()
    while len(gunler) < gun and bakilan < geriye_bak:
        bakilan += 1
        g -= timedelta(days=1)
        if g.weekday() >= 5:
            continue
        veri = await _gun_dosyasi(g)
        if not veri:
            continue                      # dosya yayimlanmamis: gun HIC yok
        k = veri.get(ticker)
        if not k:
            continue                      # sembol o gun dosyada yok
        gunler.append(_gun_kaydi(g, k[2], konsolide.get(g.isoformat()),
                                 kons_gerekce))

    olculen = [x["pay_yuzde"] for x in gunler if x["durum"] == OLCULDU]
    ortalama = round(sum(olculen) / len(olculen), 2) if olculen else None
    en_yeni_olculen = next((x for x in gunler if x["durum"] == OLCULDU), None)
    return {
        "ticker": ticker,
        "kaynak": ("FINRA Reg SHO gunluk (borsa disi hacim) / "
                   "market-data-service gunluk bar (konsolide hacim)"),
        "gun_sayisi": len(gunler),
        "olculen_gun": len(olculen),
        "olculemeyen_gun": sum(1 for x in gunler if x["durum"] == OLCULEMEDI),
        "tutarsiz_gun": sum(1 for x in gunler if x["durum"] == TUTARSIZ),
        "en_yeni_olculen_gun": en_yeni_olculen["tarih"] if en_yeni_olculen else None,
        "en_yeni_pay_yuzde": en_yeni_olculen["pay_yuzde"] if en_yeni_olculen else None,
        "ortalama_pay_yuzde": ortalama,
        "gunler": gunler,
        "kalibrasyon_gecerli": False,
        "not": ("Borsa disi hacmin toplam piyasa hacmine orani. YON IDDIASI "
                "TASIMAZ ve bu sistemde kalibre EDILMEMISTIR. Ortalama "
                "YALNIZCA iki kaynagin ortustugu gunlerden hesaplanir; "
                "ortusmeyen gunler ayrica sayilir, sessizce atilmaz."),
    }
