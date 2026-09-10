"""Takilabilir olcut katmani — Backtrader'in "analyzer" fikri, kendi kodumuzla.

ALINAN MIMARI FIKIR
===================
Backtrader'da olcutler motorun icine gomulu degildir: her biri bagimsiz bir
"analyzer"dir, kosuya TAKILIR, kendi sonucunu uretir. Alinan fikir budur —
kod degil. Backtrader kurulmadi, bagimlilik eklenmedi; cunku bu depoda
backtest motoru zaten vectorbt ve onu degistirmenin bir gerekcesi yok.
Kazanc, olcutlerin motordan AYRILMASINDA.

NEDEN BURADA DEGERLI
====================
walkforward.olcumler tek bir fonksiyonda yedi olcutu birden hesapliyordu.
Yeni bir olcut eklemek o fonksiyonu duzenlemeyi gerektiriyordu ve her
duzenleme, mevcut yedi degeri dogrulayan testlerin altini oyma riski
tasiyordu. Ayri kayitli analizcilerle yeni olcut eklemek mevcut hicbir
olcutun koduna dokunmaz.

ASIL KAZANC: HER OLCUT "OLCULEMEDI" DIYEBILIYOR
==============================================
Tek fonksiyonlu bicimde her olcut bir sayi dondurmek ZORUNDAYDI. Bunun
somut bedeli olculdu: gunluk getirilerin standart sapmasi 0 ise (strateji
hic islem acmadiysa ya da tek gunluk veri varsa) Sharpe TANIMSIZDIR, ama
kod 0.0 yaziyordu. Kullanici ekranda "Sharpe 0.000" goruyor ve bunu
"olculdu, vasat" diye okuyor — oysa hicbir sey olculmemis.

Bu, bu depoda 232d1a0 ile kapatilan hatanin ta kendisidir. Burada her
analizci uc durumlu doner: OLCULDU / OLCULEMEDI, ve OLCULEMEDI durumunda
deger None'dir — asla 0, asla sonsuz.

Ayni sinif iki yeni olcutte de kendini gosteriyor:
  - Sortino: hic kayip gunu yoksa asagi yonlu sapma 0'dir; bolme sonsuz
    verirdi. "Sonsuz Sortino" bir olcum degil, bir bolme kazasidir.
  - Calmar: maksimum dusus 0 ise ayni sey.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import pandas as pd

OLCULDU = "olculdu"
OLCULEMEDI = "olculemedi"

ISLEM_GUNU = 252


@dataclass(frozen=True)
class Olcut:
    deger: Optional[float]
    durum: str
    gerekce: str = ""
    birim: str = ""

    def __post_init__(self):
        if self.durum not in (OLCULDU, OLCULEMEDI):
            raise ValueError(f"gecersiz durum: {self.durum}")
        if self.durum == OLCULDU and self.deger is None:
            raise ValueError("OLCULDU durumunda deger None olamaz")
        if self.durum == OLCULEMEDI and self.deger is not None:
            raise ValueError(
                "OLCULEMEDI durumunda deger None OLMALI "
                "(0 yazmak 'olculdu' anlamina gelir)")
        if self.durum == OLCULDU and not np.isfinite(self.deger):
            raise ValueError(
                f"OLCULDU durumunda deger sonlu olmali, {self.deger} verildi "
                "(sonsuz bir olcum degil, bir bolme kazasidir)")


ANALIZCILER: dict = {}


def analizci(ad: str, birim: str = "", basamak: int = 3) -> Callable:
    """Bir olcutu kayda ekler. Mevcut olcutlerin koduna dokunmadan eklenir."""
    def sarmala(fn):
        if ad in ANALIZCILER:
            raise ValueError(f"'{ad}' zaten kayitli")
        fn._birim, fn._basamak = birim, basamak
        ANALIZCILER[ad] = fn
        return fn
    return sarmala


def _olculdu(deger, birim, basamak) -> Olcut:
    return Olcut(round(float(deger), basamak), OLCULDU, birim=birim)


def _seri(baglam) -> Optional[pd.Series]:
    g = baglam.get("getiriler")
    if g is None or len(g) == 0:
        return None
    return pd.Series(g).astype(float).fillna(0.0)


def _birikimli(g: pd.Series) -> pd.Series:
    return (1.0 + g).cumprod()


# ------------------------------------------------------------- analizciler
@analizci("toplam_getiri_yuzde", "%", 2)
def _toplam_getiri(baglam):
    g = _seri(baglam)
    if g is None:
        return Olcut(None, OLCULEMEDI, "getiri serisi bos")
    return _olculdu((_birikimli(g).iloc[-1] - 1) * 100, "%", 2)


@analizci("son_deger", "USD", 2)
def _son_deger(baglam):
    g = _seri(baglam)
    if g is None:
        return Olcut(None, OLCULEMEDI, "getiri serisi bos")
    nakit = baglam.get("baslangic_nakit")
    if nakit is None:
        return Olcut(None, OLCULEMEDI, "baslangic nakti bilinmiyor",
                     birim="USD")
    return _olculdu(float(nakit) * float(_birikimli(g).iloc[-1]), "USD", 2)


@analizci("sharpe", "", 3)
def _sharpe(baglam):
    """DUZELTME: tanimsiz Sharpe artik 0.0 degil, OLCULEMEDI.

    Standart sapma 0 ise (hic islem yok, ya da tek gunluk veri) oran
    tanimsizdir. Onceki davranis 0.0 yaziyordu ve bu ekranda "olculdu,
    vasat" diye okunuyordu.
    """
    g = _seri(baglam)
    if g is None:
        return Olcut(None, OLCULEMEDI, "getiri serisi bos")
    if len(g) < 2:
        return Olcut(None, OLCULEMEDI,
                     f"Sharpe icin en az 2 gun gerekli, {len(g)} gun var")
    std = float(g.std())
    if not np.isfinite(std) or std <= 0:
        return Olcut(None, OLCULEMEDI,
                     "gunluk getirilerin degiskenligi sifir; oran TANIMSIZ "
                     "(strateji hic islem acmamis olabilir). Sifir yazmak "
                     "'olculdu ve vasat' anlamina gelirdi.")
    return _olculdu(np.sqrt(ISLEM_GUNU) * float(g.mean()) / std, "", 3)


@analizci("sortino", "", 3)
def _sortino(baglam):
    """Yalnizca ASAGI yonlu sapmayi cezalandiran oran.

    Sharpe yukari yondeki oynakligi da ceza sayar; Sortino saymaz. Kayip
    gunu hic yoksa payda 0'dir ve oran sonsuz cikar — bu bir olcum degil,
    bolme kazasidir; OLCULEMEDI donulur.
    """
    g = _seri(baglam)
    if g is None:
        return Olcut(None, OLCULEMEDI, "getiri serisi bos")
    if len(g) < 2:
        return Olcut(None, OLCULEMEDI,
                     f"Sortino icin en az 2 gun gerekli, {len(g)} gun var")
    negatif = g[g < 0]
    if len(negatif) == 0:
        return Olcut(None, OLCULEMEDI,
                     "hic kayip gunu yok; asagi yonlu sapma sifir ve oran "
                     "TANIMSIZ. Sonsuz bir Sortino olcum degildir.")
    asagi = float(np.sqrt((negatif ** 2).mean()))
    if not np.isfinite(asagi) or asagi <= 0:
        return Olcut(None, OLCULEMEDI, "asagi yonlu sapma hesaplanamadi")
    return _olculdu(np.sqrt(ISLEM_GUNU) * float(g.mean()) / asagi, "", 3)


@analizci("maks_dusus_yuzde", "%", 2)
def _maks_dusus(baglam):
    g = _seri(baglam)
    if g is None:
        return Olcut(None, OLCULEMEDI, "getiri serisi bos", birim="%")
    b = _birikimli(g)
    return _olculdu(((b / b.cummax()) - 1).min() * 100, "%", 2)


@analizci("calmar", "", 3)
def _calmar(baglam):
    """Yillik getiri / maksimum dusus.

    Dusus 0 ise (hic geri cekilme yok) oran tanimsizdir — genellikle
    strateji hic islem acmadigi icin. Sonsuz donmek yerine OLCULEMEDI.
    """
    g = _seri(baglam)
    if g is None:
        return Olcut(None, OLCULEMEDI, "getiri serisi bos")
    b = _birikimli(g)
    dusus = float(((b / b.cummax()) - 1).min())
    if dusus >= 0 or not np.isfinite(dusus):
        return Olcut(None, OLCULEMEDI,
                     "maksimum dusus sifir; oran TANIMSIZ (strateji hic "
                     "geri cekilme yasamamis ya da hic islem acmamis)")
    yil = len(g) / ISLEM_GUNU
    if yil <= 0:
        return Olcut(None, OLCULEMEDI, "gun sayisi sifir")
    son = float(b.iloc[-1])
    if son <= 0:
        return Olcut(None, OLCULEMEDI,
                     "birikimli deger sifir ya da negatif; yillik getiri "
                     "tanimsiz")
    yillik = son ** (1.0 / yil) - 1.0
    return _olculdu(yillik / abs(dusus), "", 3)


@analizci("en_uzun_dusus_gun", "gun", 0)
def _en_uzun_dusus(baglam):
    """Zirveden zirveye en uzun toparlanma suresi.

    Maksimum dusus "ne kadar kaybettin" der; bu olcut "ne kadar sure
    kayipta kaldin" der. Ikisi cok farkli stratejileri ayirir.
    """
    g = _seri(baglam)
    if g is None:
        return Olcut(None, OLCULEMEDI, "getiri serisi bos", birim="gun")
    b = _birikimli(g)
    zirve = b.cummax()
    sualti = (b < zirve).to_numpy()
    en_uzun = suren = 0
    for altta in sualti:
        suren = suren + 1 if altta else 0
        en_uzun = max(en_uzun, suren)
    return _olculdu(en_uzun, "gun", 0)


@analizci("en_uzun_kayip_serisi", "gun", 0)
def _en_uzun_kayip(baglam):
    g = _seri(baglam)
    if g is None:
        return Olcut(None, OLCULEMEDI, "getiri serisi bos", birim="gun")
    en_uzun = suren = 0
    for x in g.to_numpy():
        suren = suren + 1 if x < 0 else 0
        en_uzun = max(en_uzun, suren)
    return _olculdu(en_uzun, "gun", 0)


@analizci("gun_sayisi", "gun", 0)
def _gun_sayisi(baglam):
    g = _seri(baglam)
    if g is None:
        return Olcut(None, OLCULEMEDI, "getiri serisi bos", birim="gun")
    return _olculdu(len(g), "gun", 0)


@analizci("islem_sayisi", "islem", 0)
def _islem_sayisi(baglam):
    n = baglam.get("islem_sayisi")
    if n is None:
        return Olcut(None, OLCULEMEDI, "islem sayisi bildirilmedi",
                     birim="islem")
    return _olculdu(n, "islem", 0)


@analizci("kazanma_orani_yuzde", "%", 2)
def _kazanma_orani(baglam):
    o = baglam.get("kazanan_oran")
    if o is None:
        return Olcut(None, OLCULEMEDI,
                     "kapali islem yok; kazanma orani TANIMSIZ", birim="%")
    return _olculdu(o, "%", 2)


# ------------------------------------------------------------------ kosucu
def calistir(baglam: dict, secim=None) -> dict:
    """Kayitli analizcileri calistirir. Biri patlarsa digerleri etkilenmez."""
    adlar = list(ANALIZCILER) if secim is None else list(secim)
    sonuc = {}
    for ad in adlar:
        fn = ANALIZCILER.get(ad)
        if fn is None:
            sonuc[ad] = Olcut(None, OLCULEMEDI, f"'{ad}' adli analizci kayitli degil")
            continue
        try:
            sonuc[ad] = fn(baglam)
        except Exception as e:
            # Bir analizcinin hatasi digerlerini goturmez — takilabilir
            # katmanin butun anlami bu.
            sonuc[ad] = Olcut(None, OLCULEMEDI,
                              f"analizci hata verdi: {type(e).__name__}: {str(e)[:120]}")
    return sonuc


def duz_sozluk(sonuclar: dict) -> dict:
    """Analizci sonuclarini {ad: deger} bicimine indirger (None = olculemedi)."""
    return {ad: o.deger for ad, o in sonuclar.items()}


def gerekceler(sonuclar: dict) -> dict:
    """Olculemeyen olcutlerin NEDEN olculemedigini dondurur."""
    return {ad: o.gerekce for ad, o in sonuclar.items()
            if o.durum == OLCULEMEDI and o.gerekce}
