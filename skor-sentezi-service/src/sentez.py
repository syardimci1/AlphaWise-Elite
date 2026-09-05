"""
Bes eksenli temel skor sentezi.

EKSENLER (her biri 0-100, ya da olculemedi/uygulanamaz)
=======================================================
  1. finansal_saglik   <- Altman Z-Score (1968)
  2. kazanc_kalitesi   <- Beneish M-Score (1999), ters cevrilmis
  3. temel_guc         <- Piotroski F-Score (2000)
  4. degerleme         <- Iki asamali DCF guvenlik payi
  5. temettu           <- AlphaWise temettu dayaniklilik bilesimi

Ilk dordu YAYIMLANMIS akademik olcutlerdir ve kendi kodumuzla, kendi
verimizle bagimsiz hesaplanir. Besincisi kendi bilesimimizdir ve ciktida
boyle etiketlenir.

GENEL PUAN KURALI — Anayasa Madde 2.1 ile ayni ilke
===================================================
Anayasa "gecerli karar icin minimum 3 veri katmani zorunludur" der ve kod
bunu maa/src/main.py:586'da uygular (layers_available < 3 -> BEKLE,
total_score None). Ayni ilke burada da gecerlidir: UCTEN AZ eksen
olculebildiyse genel puan URETILMEZ (None), sifir yazilmaz. Boylece "veri
yok" ile "olculdu ve zayif" hicbir yerde birbirine karismaz.

Genel puan, olculebilen eksenlerin DUZ ORTALAMASIDIR. Agirliklandirma
bilincli olarak YAPILMADI: depoda kalibre edilmis bir agirlik seti yok ve
uydurulmus agirliklar sonuca sahte bir kesinlik katardi.
"""
from __future__ import annotations
from typing import Optional
from . import skorlar, normalizasyon
from .olcum import Olcum, OLCULDU, OLCULEMEDI, UYGULANAMAZ

ASGARI_EKSEN = 3

EKSEN_TANIMLARI = [
    {"anahtar": "finansal_saglik", "ad": "Finansal Sağlık",
     "kaynak": "Altman Z-Score (1968)", "yayimlanmis": True,
     "aciklama": "İflas riski göstergesi; işletme sermayesi, birikmiş kâr, "
                 "faaliyet kârı, piyasa değeri ve satışların aktife oranı."},
    {"anahtar": "kazanc_kalitesi", "ad": "Kazanç Kalitesi",
     "kaynak": "Beneish M-Score (1999), ters çevrilmiş", "yayimlanmis": True,
     "aciklama": "Muhasebe kalemlerinde olağandışı yönelim olup olmadığını "
                 "sekiz endeksle ölçer. Yüksek puan = daha temiz kalem yapısı."},
    {"anahtar": "temel_guc", "ad": "Temel Güç",
     "kaynak": "Piotroski F-Score (2000)", "yayimlanmis": True,
     "aciklama": "Kârlılık, kaldıraç/likidite ve verimlilikte dokuz ikili ölçüt."},
    {"anahtar": "degerleme", "ad": "Değerleme",
     "kaynak": "İki aşamalı indirgenmiş nakit akışı", "yayimlanmis": True,
     "aciklama": "Serbest nakit akışından türetilen içsel değerin fiyata "
                 "oranı. 1,0 = fiyat içsel değere eşit. Beş eksen içinde "
                 "varsayıma EN DUYARLI olanıdır; büyüme varsayımı ±5 puan "
                 "oynatıldığında içsel değerin nereye gittiği ayrıntıda "
                 "'duyarlilik' alanında bildirilir."},
    {"anahtar": "temettu", "ad": "Temettü Dayanıklılığı",
     "kaynak": "AlphaWise bileşimi (yayımlanmış bir ölçüt değildir)",
     "yayimlanmis": False,
     "aciklama": "Ödeme oranı, serbest nakit akışı kapsamı ve ödeme sürekliliği."},
]


def _eksen(olcum: Olcum, puanla) -> dict:
    if olcum.durum == OLCULDU:
        return {"puan": round(puanla(olcum.deger), 1), "ham": olcum.deger,
                "durum": OLCULDU, "gerekce": "", "eksik": [],
                "ayrinti": olcum.ayrinti}
    return {"puan": None, "ham": None, "durum": olcum.durum,
            "gerekce": olcum.gerekce, "eksik": list(olcum.eksik),
            "ayrinti": olcum.ayrinti}


def sentezle(sirket: skorlar.Sirket, risksiz_faiz: Optional[float] = None) -> dict:
    ham = {
        "finansal_saglik": (skorlar.altman_z(sirket), normalizasyon.altman_puan),
        "kazanc_kalitesi": (skorlar.beneish_m(sirket), normalizasyon.beneish_puan),
        "temel_guc": (skorlar.piotroski_f(sirket), normalizasyon.piotroski_puan),
        "degerleme": (skorlar.dcf_icsel_fiyat_orani(sirket, risksiz_faiz),
                      normalizasyon.dcf_puan),
        "temettu": (skorlar.temettu_dayanikligi(sirket), normalizasyon.temettu_puan),
    }
    eksenler = []
    for tanim in EKSEN_TANIMLARI:
        olcum, puanla = ham[tanim["anahtar"]]
        eksenler.append({**tanim, **_eksen(olcum, puanla)})

    olculen = [e for e in eksenler if e["durum"] == OLCULDU]
    if len(olculen) < ASGARI_EKSEN:
        genel = None
        genel_gerekce = (
            f"Genel puan üretilmedi: {len(olculen)} eksen ölçülebildi, "
            f"en az {ASGARI_EKSEN} gerekiyor. "
            "Eksik ölçüm sıfır olarak sayılmaz.")
    else:
        genel = round(sum(e["puan"] for e in olculen) / len(olculen), 1)
        genel_gerekce = (f"{len(olculen)} ölçülebilen eksenin düz ortalaması. "
                         "Ağırlıklandırma yapılmadı: kalibre edilmiş bir ağırlık "
                         "seti bulunmadığı için uydurulmuş ağırlık sahte kesinlik "
                         "yaratırdı.")
    return {
        "ticker": sirket.ticker,
        "eksenler": eksenler,
        "genel_puan": genel,
        "genel_gerekce": genel_gerekce,
        "olculebilen_eksen": len(olculen),
        "toplam_eksen": len(eksenler),
        "asgari_eksen": ASGARI_EKSEN,
    }
