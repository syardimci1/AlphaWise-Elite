"""
RISK METRIKLERI - cerceve bagimliligi OLMAYAN saf hesaplamalar.

=======================================================================
NEDEN AYRI BIR MODUL
=======================================================================
Bu hesaplar daha once main.py'nin `analyze()` govdesine GOMULUYDU. Gomulu
oldugu icin de bagimsiz test EDILEMIYORDU: dogrulamak icin FastAPI, redis,
psycopg2 ve yfinance'in tamamini ayaga kaldirmak gerekiyordu.

10.09.2026'da bulunan Sortino hatasi tam olarak bu yuzden hayatta kaldi -
formulun iki yarisinin farkli esik kullandigini gosterecek dort satirlik
bir test yazmak, o kod orada durdugu surece mumkun degildi. Matematik
buraya tasindi ki bir daha sessizce bozulamasin.

main.py'nin davranisi DEGISMEDI: ayni girdiye ayni cikti (duzeltilen hata
disinda).
"""
from __future__ import annotations

import numpy as np

ISLEM_GUNU = 252
VARSAYILAN_RISKSIZ_ORAN = 0.04


def asagi_yonlu_sapma(getiriler, risksiz_oran: float = VARSAYILAN_RISKSIZ_ORAN,
                      periyot: int = ISLEM_GUNU) -> float:
    """Yillik asagi yonlu sapma (downside deviation).

    TANIM: esigin (MAR) ALTINA dususlerin karesel ortalamasinin karekoku,
    TUM gozlemler uzerinden. Esigin ustundeki gunler diziden ATILMAZ, sifir
    olarak KALIR - cunku "o gun asagi yonlu risk uretmedi" demek, "o gun
    hic olmadi" demek degildir.

    ONCEKI YANLIS UYGULAMA (main.py, 10.09.2026'da duzeltildi):
        np.std(getiriler[getiriler < 0]) * sqrt(252)
    Iki ayri hata tasiyordu:
      1. `np.std(negatifler)` negatif getirilerin KENDI ORTALAMALARI
         etrafindaki dagilimini olcer - oysa gereken, esikten sapmadir.
         Bir seri "her gun tam -%2" olsa asagi yonlu risk BUYUKTUR ama
         bu formul 0 verir.
      2. Bolme yalnizca NEGATIF gun sayisina yapiliyordu; oysa ortalama
         TUM gozlemler uzerinden alinmalidir.
    Ikisi de paydayi kucultur, dolayisiyla Sortino'yu OLDUGUNDAN BUYUK
    gosterir. Gercek veride olculen abartma: %1,5 ile %12,5 arasi.
    """
    r = np.asarray(getiriler, dtype=float)
    if r.size == 0:
        return 0.0
    esik_gunluk = risksiz_oran / periyot
    eksik = np.minimum(r - esik_gunluk, 0.0)
    return float(np.sqrt(np.mean(eksik ** 2)) * np.sqrt(periyot))


def sortino_orani(getiriler, risksiz_oran: float = VARSAYILAN_RISKSIZ_ORAN,
                  periyot: int = ISLEM_GUNU) -> float | None:
    """Sortino orani - pay ve payda AYNI MAR ile.

    Pay   : yillik ortalama getiri - risksiz oran
    Payda : ayni risksiz orana gore asagi yonlu sapma

    Iki yarinin AYNI esigi kullanmasi tesadufi bir ayrinti degil, oranin
    tanimidir. Farkli esikler kullanildiginda cikan sayi bir Sortino orani
    degil, iki farkli olcegin bolumudur ve yorumlanamaz.

    Payda sifirsa (hicbir gun esigin altina dusmemisse) oran TANIMSIZDIR
    ve None doner - buyuk bir sayi UYDURULMAZ.
    """
    r = np.asarray(getiriler, dtype=float)
    if r.size == 0:
        return None
    yillik_ortalama = float(np.mean(r) * periyot)
    payda = asagi_yonlu_sapma(r, risksiz_oran, periyot)
    if payda <= 0:
        return None
    return (yillik_ortalama - risksiz_oran) / payda
