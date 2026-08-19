"""
Kalibrasyon meta-verisi.

=======================================================================
YENIDEN URETILEBILIRLIK
=======================================================================
Asagidaki her sayi su komutla yeniden uretilebilir:

    python3 calibration/kalibre.py

Onceki surumde bu dosya, ureten betigi depoda BULUNMAYAN sayilar
tasiyordu. Artik betik de veri anlik goruntusu de depoda.

=======================================================================
DUZELTILEN HATA: "isabet - baz" KARSILASTIRMASI GECERSIZDI
=======================================================================
Eski kalibrasyon, YUKARI ve ASAGI sinyallerinin KARISIK isabet oranini
yalnizca P(yukari) referansiyla kiyasliyordu. Oysa iki sinyal turunun
sans karsiligi farklidir:

    YUKARI sinyali icin sans = P(yukari)
    ASAGI  sinyali icin sans = 1 - P(yukari)

Yukselen bir piyasada ASAGI sinyali en iyi ihtimalle P(asagi) kadar
isabet edebilir; bunu P(yukari) ile kiyaslamak yapay bir felaket
uretir. Olculen abarti: ORTALAMA 17.11 puan (en kotu hucre -34.38
puandan -0.30 puana geldi).

SONUC DEGISMEDI: metrik duzeltildikten sonra da hicbir spesifikasyon
gecme esigini asmiyor. Sahte kalibrasyon uretilmedi.

=======================================================================
NEDEN HALA lambda = 0.0
=======================================================================
Duzeltilmis metrikle:
  - beceri araligi          : -3.93 .. +1.63 puan   (esik: +5.0)
  - gecen spesifikasyon     : 0/9
  - istatistiksel anlamli   : 0/9  (en dusuk p = 0.077)

Elenen alternatif aciklamalar:
  - ESIK SORUNU DEGIL: egitimde secilen en iyi esikler (+3.8..+23.4
    puan) testte cokuyor (-6.9..+6.7). Asiri uyum izi.
  - TERS SINYAL DEGIL: sinyal EGITIMDE 9/9 pozitif, TESTTE 7/9 negatif.
    Gercekten ters olsaydi iki pencerede de ayni yonde olurdu. Bu
    isaret kararsizligi, kenar yoklugunun imzasidir.
  - ORNEKLEM TEK BASINA ACIKLAMIYOR: n~400-450 ile +5 puanlik kenari
    yakalama gucu ~%55 (%80 icin n=785 gerekir). Ornek ideal degil,
    ama olculen etki +1.6..-3.9 araliginda — 5 puana yakin bile degil.

=======================================================================
SERVISIN DURUMU: DENEYSEL
=======================================================================
Bu servis izleme/baglam verisi uretir. Yon iddiasi tasiyan kodlar
(EKLE, DIKKAT ET) URETILMEZ; yalnizca TUT/BEKLE dondurulur. Cagiran
taraf (God Mode) bu durumu /health ve /methodology uzerinden gorur ve
servisi bilerek dusuk guvenilirlikli olarak kullanir.
"""

DURUM_DENEYSEL = "deneysel"

KALIBRASYON = {
    "gecerli": False,
    "durum": DURUM_DENEYSEL,
    "buzusme_lambda": 0.0,
    "yon_kodu_uretir": False,
    "gerekce": (
        "Duzeltilmis beceri metrigiyle 9 spesifikasyonun (NASDAQ/SP500/BTC "
        "× 5g/10g/20g) hicbiri +5.0 puanlik gecme esigini asmadi ve hicbiri "
        "istatistiksel olarak anlamli degil (en dusuk p=0.077). Beceri "
        "araligi -3.93 ile +1.63 puan. Esik ayari ve isaret cevirme "
        "alternatifleri de elendi. lambda=0'da tutuluyor."
    ),
    "metrik": {
        "ad": "beceri_puan",
        "tanim": ("(gerceklesen_dogru - beklenen_dogru) / n * 100; "
                  "beklenen_dogru = n_yukari*baz + n_asagi*(1-baz)"),
        "duzeltilen_hata": (
            "Onceki metrik YUKARI+ASAGI karisik isabetini yalnizca P(yukari) "
            "ile kiyasliyordu. Iki sinyal turunun sans karsiligi farklidir; "
            "bu, basarisizligi ORTALAMA 17.11 puan abartiyordu."
        ),
        "abarti_ortalama_puan": 17.11,
        "eski_en_kotu_puan": -34.38,
        "duzeltilmis_en_kotu_puan": -0.30,
    },
    "test_penceresi": "2024-01-01 -> 2026-08-18",
    "egitim_penceresi": "2021-01-01 -> 2023-12-31",
    "denenen_spesifikasyon": 9,
    "basarili_spesifikasyon": 0,
    "anlamli_spesifikasyon": 0,
    "gecme_esigi_puan": 5.0,
    "alfa": 0.05,
    "en_iyi_beceri_puan": 1.63,
    "en_kotu_beceri_puan": -3.93,
    "en_dusuk_p": 0.077,
    "elenen_alternatifler": {
        "esik_ayari": ("Egitimde secilen en iyi esikler testte cokuyor "
                       "(+3.8..+23.4 -> -6.9..+6.7). Asiri uyum."),
        "isaret_cevirme": ("Sinyal egitimde 9/9 pozitif, testte 7/9 negatif. "
                           "Ters sinyal degil, isaret kararsizligi."),
        "orneklem": ("n~400-450, +5 puan icin guc ~%55 (%80 icin n=785). "
                     "Ornek ideal degil ama olculen etki 5 puana yakin bile degil."),
    },
    "istatistiksel_guc": {
        "mevcut_n_araligi": "401-450",
        "guc_5_puan_kenar": 0.55,
        "gereken_n_5_puan_%80_guc": 785,
    },
    "veri_kaynaklari": ["FRED WALCL", "FRED WTREGEN", "FRED RRPONTSYD",
                        "FRED NASDAQCOM", "FRED SP500", "FRED CBBTCUSD"],
    "yeniden_uret": "python3 calibration/kalibre.py",
    "sonraki_gozden_gecirme": (
        "n>=785 saglandiginda (yaklasik 2027 ortasi) veya metodoloji "
        "degistiginde tekrar calistir."
    ),
}
