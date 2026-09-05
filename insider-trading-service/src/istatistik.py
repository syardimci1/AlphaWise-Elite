"""
Iceriden islem yon ayrimi icin ISTATISTIKSEL YETERLILIK katmani (Madde 25).

NEDEN GEREKLI
=============
Servis alim/satim ayrimini zaten yapiyor (acik_piyasa_yonu) ve ozetinde
"herhangi bir yon cikarimi yapilamaz" diyor. Ama bunu OLCMUYOR: cumle bir
YARGI, sayi degil. Az sayida islemde 3 alim / 1 satis gormek ile 300 alim /
100 satis gormek ayni oran olmasina ragmen bambaska seylerdir. Bu modul,
gozlenen yon farkinin sansla ayirt edilip edilemedigini HESAPLAR.

YONTEM VE GEREKCESI
===================
1) TABAN ORAN VARSAYILMAZ. "Alim ve satim esit olasilikli" (p=0.5) demek bu
   evrende YANLIS olurdu: servisin kendi olcumu acik piyasa aliminin cok
   nadir oldugunu soyluyor (3,57 yilda 32 kayit). Bunun yerine pencere,
   SIRKETIN KENDI GECMISININ GERI KALANIYLA karsilastirilir — yani "son 90
   gun, bu sirketin normalinden farkli mi?" sorusu sorulur.

2) FISHER KESIN TESTI kullanilir, ki-kare degil. Ki-kare yaklasimi kucuk
   sayilarda (beklenen hucre < 5) guvenilmezdir ve burada sayilar tam olarak
   o bolgededir. Fisher kesindir ve ek bagimlilik gerektirmez (math.comb).

3) KISI DUZEYINDE toplama birincildir. Ayni yoneticinin ayni gun yaptigi bes
   alim BES BAGIMSIZ ISARET DEGILDIR; islem sayisiyla test etmek sahte
   coklama (pseudo-replication) olur ve p degerini yapay olarak kucultur.
   Islem duzeyi ikincil olarak ayrica bildirilir.

4) SONUC "yon kodu" DEGILDIR. Bu modul yalnizca "gozlenen fark sansla
   aciklanabilir mi" sorusunu yanitlar; karar kodu uretmez.
"""
from __future__ import annotations
from math import comb, sqrt
from typing import Optional

# Bu esigin altinda test bile calistirilmaz: 2x2 tablonun bir kenari cok
# kucukse Fisher matematiksel olarak calisir ama sonuc yorumlanamaz.
ASGARI_PENCERE_OLAY = 5
ANLAMLILIK_ESIGI = 0.05


def hipergeometrik(a: int, b: int, c: int, d: int, k: int) -> float:
    """Kenar toplamlari sabitken sol-ust hucrenin k olma olasiligi."""
    n = a + b + c + d
    ust, alt = a + b, c + d
    sol = a + c
    if k < max(0, sol - alt) or k > min(ust, sol):
        return 0.0
    return comb(ust, k) * comb(alt, sol - k) / comb(n, sol)


def fisher_kesin_p(a: int, b: int, c: int, d: int) -> float:
    """Iki yonlu Fisher kesin testi p degeri.

    Tablo:
              alim   satis
      pencere   a      b
      gecmis    c      d

    Iki yonlu p: gozlenen tablodan DAHA OLASI OLMAYAN tum tablolarin
    olasiliklarinin toplami (Fisher'in kendi tanimi).
    """
    for x in (a, b, c, d):
        if x < 0:
            raise ValueError("negatif hucre olamaz")
    n = a + b + c + d
    if n == 0:
        raise ValueError("bos tablo")
    ust, alt, sol = a + b, c + d, a + c
    # NOT: burada bir "bos kenar -> p=1" ozel durumu vardi. OLCULDU ve OLU
    # KOD oldugu gorildu: 0-5 arasi tum 1.295 tablo tarandiginda, ozel durum
    # ile onsuz sonuclar arasinda TEK BIR FARK bile yok (bos kenarda toplama
    # zaten tek bir tabloyu iceriyor ve 1.0 veriyor). Bir seyi koruduguna
    # inanilan ama korumayan kod, gelecekte yanlis guven verir; kaldirildi.
    gozlenen = hipergeometrik(a, b, c, d, a)
    # Kayan nokta esitligini kaybetmemek icin kucuk bir pay birakilir.
    tolerans = gozlenen * 1e-7
    toplam = 0.0
    for k in range(max(0, sol - alt), min(ust, sol) + 1):
        p = hipergeometrik(a, b, c, d, k)
        if p <= gozlenen + tolerans:
            toplam += p
    return min(1.0, toplam)


def wilson_araligi(basari: int, toplam: int, z: float = 1.96) -> Optional[tuple]:
    """Oran icin Wilson %95 guven araligi.

    Normal yaklasim (p +- z*sqrt(p(1-p)/n)) kucuk n'de ve orana 0/1'e
    yaklastiginda aralik sinirlarini [0,1] disina tasirir; Wilson tasirmaz.
    """
    if toplam <= 0:
        return None
    p = basari / toplam
    payda = 1 + z * z / toplam
    merkez = (p + z * z / (2 * toplam)) / payda
    yayilim = z * sqrt(p * (1 - p) / toplam + z * z / (4 * toplam * toplam)) / payda
    return (max(0.0, merkez - yayilim), min(1.0, merkez + yayilim))


def yeterlilik(pencere_alim: int, pencere_satis: int,
               gecmis_alim: int, gecmis_satis: int,
               asgari: int = ASGARI_PENCERE_OLAY,
               esik: float = ANLAMLILIK_ESIGI) -> dict:
    """Gozlenen yon farki sansla aciklanabilir mi?

    Doner: durum = "yetersiz_veri" | "ayirt_edilemiyor" | "ayirt_ediliyor"
    """
    pencere_toplam = pencere_alim + pencere_satis
    gecmis_toplam = gecmis_alim + gecmis_satis
    ortak = {
        "pencere_alim": pencere_alim, "pencere_satis": pencere_satis,
        "gecmis_alim": gecmis_alim, "gecmis_satis": gecmis_satis,
        "pencere_toplam": pencere_toplam, "gecmis_toplam": gecmis_toplam,
        "pencere_alim_orani": (pencere_alim / pencere_toplam
                               if pencere_toplam else None),
        "gecmis_alim_orani": (gecmis_alim / gecmis_toplam
                              if gecmis_toplam else None),
        "guven_araligi_95": wilson_araligi(pencere_alim, pencere_toplam),
        "asgari_olay": asgari,
    }
    if gecmis_toplam == 0:
        # AYRI BIR DURUM: gecmis "az" degil, HIC YOK. Bu neredeyse her zaman
        # pencerenin mevcut tum veriyi yutmasindan kaynaklanir; "az islem var"
        # demek kullaniciyi yanlis yere bakmaya iter.
        return {**ortak, "durum": "temel_yok", "p_degeri": None,
                "gerekce": ("Karşılaştırma temeli oluşmadı: pencere, elde olan "
                            "tüm kayıtları kapsıyor ve geriye kıyaslanacak "
                            "dönem kalmıyor. Daha kısa bir pencere deneyin.")}
    if pencere_toplam < asgari or gecmis_toplam < asgari:
        return {**ortak, "durum": "yetersiz_veri", "p_degeri": None,
                "gerekce": (f"Yeterli açık piyasa işlemi yok "
                            f"(pencere: {pencere_toplam}, geçmiş: {gecmis_toplam}; "
                            f"her biri için en az {asgari} gerekiyor). "
                            f"Bu bir ölçüm eksikliğidir, yön yokluğu değildir.")}
    p = fisher_kesin_p(pencere_alim, pencere_satis, gecmis_alim, gecmis_satis)
    if p > esik:
        return {**ortak, "durum": "ayirt_edilemiyor", "p_degeri": round(p, 4),
                "gerekce": (f"Gözlenen fark şansla açıklanabilir "
                            f"(Fisher kesin testi p = {p:.3f} > {esik}). "
                            f"Yön çıkarımı yapılamaz.")}
    return {**ortak, "durum": "ayirt_ediliyor", "p_degeri": round(p, 4),
            "gerekce": (f"Pencere, şirketin kendi geçmişinden istatistiksel "
                        f"olarak ayrışıyor (Fisher kesin testi p = {p:.3f} "
                        f"≤ {esik}). Bu, yönün gelecekte süreceği anlamına "
                        f"GELMEZ; yalnızca farkın şansla açıklanamadığını söyler.")}
