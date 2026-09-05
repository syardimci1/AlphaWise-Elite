"""
Monte Carlo deger dususu dagilimi (Madde 26).

NEDEN BLOK BOOTSTRAP — VE BIR VARSAYIMIN OLCUMLE CURUTULMESI
============================================================
Bagimsiz (i.i.d.) ornekleme gunluk getirileri tek tek ceker ve serideki TUM
sirali yapiyi yok eder. Blok bootstrap ardisik BLOKLAR cekerek kisa vadeli
bagimliligi korur. Blok uzunlugu 1 secilirse yontem matematiksel olarak
i.i.d.'ye cokerr — bu, kodun bir tutarlilik kontroludur.

BU MODULUN ILK SURUMU SU IDDIAYI TASIYORDU: "i.i.d. ornekleme dususu
SISTEMATIK OLARAK kucuk gosterir, cunku oynaklik kumelenmesini yok eder."
IDDIA OLCULDU VE CURUTULDU. MSFT'nin gercek 2020-2026 serisinde (1.676
gunluk getiri, 2.000 yol, 252 gun ufuk, ayni tohum):

    blok        medyan      p95       p99
       1        0.2254    0.4104    0.4903     <- i.i.d. ile birebir ayni
      10        0.2075    0.3748    0.4670
      20        0.2075    0.3808    0.4731
      60        0.2198    0.3576    0.4162
    i.i.d.      0.2254    0.4104    0.4903

Yani bu seride blok bootstrap dususu DAHA SIG gosteriyor, daha derin degil.
Nedeni sunulabilir: gercek veride sert dusus gunlerini cogu zaman sert
toparlanma gunleri izliyor; blok ornekleme bu ESLESMEYI koruyor ve dususu
kesiyor, i.i.d. ise esleşmeyi bozup dusus serilerini kurtaracak toparlanmayi
yok ediyor.

Ilk iddiayi destekleyen sentetik ornek (uzun sakin donem + kumelenmis kotu
donem) hala testlerde duruyor, ama artik dogru adiyla: o ornek YONUN VERIYE
BAGLI oldugunu gosterir, genel bir kural OLDUGUNU degil.

SONUC: yontem secimi tek basina "dogru sayi" uretmez. Bu yuzden cikti IKI
YONTEMI DE bildirir; kullanici tek bir sayiya degil, yonteme duyarliliga
bakar.

TEKRARLANABILIRLIK
==================
Her simulasyon bir TOHUM alir ve ayni tohumla ayni sonucu verir. Tohumsuz
bir stres testi, iki calistirmada iki farkli sayi vererek hangisinin dogru
oldugu sorusunu cevapsiz birakirdi.

BU BIR TAHMIN DEGILDIR
======================
Simulasyon "gelecek gecmise benzerse" varsayimi altinda calisir. Gecmiste
gorulmemis bir rejim degisikligini uretemez; ciktida bu acikca yazilir.
"""
from __future__ import annotations
import random
from typing import Optional

VARSAYILAN_YOL = 2000
VARSAYILAN_UFUK = 252      # yaklasik bir islem yili
VARSAYILAN_BLOK = 20       # yaklasik bir islem ayi
ASGARI_GETIRI = 60         # bu kadar gunluk gecmis olmadan simulasyon yapilmaz


def gunluk_getiriler(fiyatlar: list) -> list:
    temiz = [float(f) for f in fiyatlar
             if f is not None and float(f) == float(f) and float(f) > 0]
    return [temiz[i] / temiz[i - 1] - 1.0 for i in range(1, len(temiz))]


def _yol_dususu(getiriler: list) -> float:
    """Bir getiri yolunun ureteceigi en derin dusus."""
    deger, zirve, en_derin = 1.0, 1.0, 0.0
    for g in getiriler:
        deger *= (1.0 + g)
        if deger > zirve:
            zirve = deger
        dusus = (zirve - deger) / zirve
        if dusus > en_derin:
            en_derin = dusus
    return en_derin


def iid_yol(getiriler: list, ufuk: int, rng: random.Random) -> list:
    """Bagimsiz ornekleme — KARSILASTIRMA icin vardir, varsayilan DEGILDIR."""
    return [rng.choice(getiriler) for _ in range(ufuk)]


def blok_yol(getiriler: list, ufuk: int, blok: int, rng: random.Random) -> list:
    """Ardisik bloklar halinde ornekleme (dairesel/stationary blok bootstrap).

    Seri dairesel kabul edilir; boylece son gunler de blok baslangici
    olabilir ve serinin sonu sistematik olarak eksik temsil edilmez.
    """
    n = len(getiriler)
    yol = []
    while len(yol) < ufuk:
        bas = rng.randrange(n)
        for i in range(blok):
            yol.append(getiriler[(bas + i) % n])
            if len(yol) >= ufuk:
                break
    return yol[:ufuk]


def yuzdelik(sirali: list, q: float) -> float:
    """Dogrusal ara degerli yuzdelik (q: 0-1). Liste SIRALI olmali."""
    if not sirali:
        raise ValueError("bos dagilim")
    if len(sirali) == 1:
        return float(sirali[0])
    konum = q * (len(sirali) - 1)
    alt = int(konum)
    ust = min(alt + 1, len(sirali) - 1)
    pay = konum - alt
    return float(sirali[alt] * (1 - pay) + sirali[ust] * pay)


def dusus_dagilimi(getiriler: list, yol_sayisi: int = VARSAYILAN_YOL,
                   ufuk: int = VARSAYILAN_UFUK, blok: int = VARSAYILAN_BLOK,
                   tohum: int = 20260906, yontem: str = "blok",
                   asgari: int = ASGARI_GETIRI) -> dict:
    if len(getiriler) < asgari:
        return {"durum": "olculemedi", "gerekce":
                (f"Simülasyon için yeterli geçmiş yok: {len(getiriler)} günlük "
                 f"getiri var, en az {asgari} gerekiyor."),
                "yuzdelikler": None}
    rng = random.Random(tohum)
    uretici = (blok_yol if yontem == "blok" else iid_yol)
    dususler = []
    for _ in range(yol_sayisi):
        yol = (uretici(getiriler, ufuk, blok, rng) if yontem == "blok"
               else uretici(getiriler, ufuk, rng))
        dususler.append(_yol_dususu(yol))
    dususler.sort()
    return {
        "durum": "olculdu",
        "yontem": yontem,
        "yol_sayisi": yol_sayisi, "ufuk_gun": ufuk,
        "blok_gun": blok if yontem == "blok" else None,
        "tohum": tohum,
        "gecmis_gun": len(getiriler),
        "yuzdelikler": {
            "medyan": yuzdelik(dususler, 0.50),
            "p75": yuzdelik(dususler, 0.75),
            "p95": yuzdelik(dususler, 0.95),
            "p99": yuzdelik(dususler, 0.99),
            "en_kotu": dususler[-1],
        },
        "uyari": ("Bu bir tahmin değildir. Simülasyon 'gelecek geçmişe benzerse' "
                  "varsayımı altında çalışır ve geçmişte görülmemiş bir rejim "
                  "değişikliğini üretemez."),
    }
