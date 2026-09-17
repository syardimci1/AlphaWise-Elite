"""Opsiyon zincirinin BETIMLEYICI istatistikleri (24.08.2026).

NE ISE YARAR
  Zincirin ham sayimlarini raporlar: put/call hacim orani, put/call acik
  pozisyon orani ve hacim/acik pozisyon orani. Bunlar OLGUDUR — zincirde
  ne oldugunu sayarlar, ne olacagini soylemezler.

NEDEN AYRI BIR MODUL
  dex_vanna.py'ye DOKUNULMADI. O modulun `atlanma_nedeni` sozlugu disari
  `atlanan_kontrat` olarak donuyor ve test_dex_vanna.py bu sayilara birebir
  assertion yaziyor (== 5 / == 1). Yeni sayaclari oraya eklemek o testleri
  kesin olarak patlatirdi. Bu yuzden istatistikler tamamen ayri tutuldu.

NEDEN "MARKET TIDE" BENZERI BIR AKIS SKORU URETMIYORUZ
  Unusual Whales tarzi net-prim (net premium) hesaplari, her islemin ALIS
  mi SATIS tarafinda gerceklestigini bilmeyi gerektirir (Lee-Ready tipi
  kotasyon esleme). Ucretsiz zincir anlik goruntusunde islem seviyesinde
  tape YOKTUR — yalnizca gun sonu toplamlari vardir. Dolayisiyla bu modul
  yon tasiyan bir "akis" skoru URETMEZ; yalnizca yon iddiasi tasimayan
  sayimlar dondurur. Bu, DPKE modulundeki ayni kisitin opsiyon karsiligidir.

KASITLI TASARIM KARARLARI
  1. FILTRESIZ hesaplanir. /dex-vanna ucundaki `min_acik_pozisyon`
     parametresi bu istatistikleri YAPISAL OLARAK bozar: acik pozisyonu 0
     olup hacmi olan kontratlar "yeni pozisyon aciliyor" vekilinin EN
     GUCLU halidir ve OI filtresi tam olarak onlari eler. Bu yuzden
     istatistikler zincirin ham haline uygulanir.
  2. Sifir paydali oranlar None doner — 0 veya sonsuz UYDURULMAZ.
  3. Tek gunluk bir anlik goruntudur; tarihce olmadan yuzdelik dilim veya
     z-skoru URETILMEZ (mutlak esik de yoktur). Tek basina yorumlanamaz.
"""

# Bu modul KALIBRE EDILMEMISTIR: hicbir karar koduna (EKLE/TUT/BEKLE/
# DIKKAT ET) baglanmaz ve lambda katkisi yoktur.
KALIBRASYON_GECERLI = False


def _sayi(deger):
    """Guvenli sayiya cevrim. NaN ve cevrilemeyen degerler None doner.

    NaN ozellikle elenir: IEEE-754 geregi NaN ile yapilan her karsilastirma
    False dondurur, bu yuzden `deger > 0` gibi bir kontrol NaN'i sessizce
    gecirir ve tum toplami NaN'a cevirir (dex_vanna.py'de olculmus bir
    tuzaktir, bkz. oradaki 23.08.2026 duzeltmesi).
    """
    if deger is None:
        return None
    try:
        d = float(deger)
    except (TypeError, ValueError):
        return None
    return None if d != d else d


def _oran(pay, payda):
    """Payda 0 veya yoksa None — sifir/sonsuz UYDURULMAZ."""
    if not payda:
        return None
    return round(pay / payda, 4)


def zincir_istatistikleri(kontratlar) -> dict:
    """Ham opsiyon zincirinden betimleyici sayimlar uretir.

    `kontratlar`: her biri option_type, volume, open_interest tasiyabilen
    sozlukler. Eksik/bozuk alanlar sessizce atlanmaz — ayri sayilir.
    """
    sayim = {
        "call": {"kontrat": 0, "hacim": 0.0, "acik_pozisyon": 0.0},
        "put": {"kontrat": 0, "hacim": 0.0, "acik_pozisyon": 0.0},
    }
    gecersiz_tip = 0
    hacim_alani_yok = 0
    acik_pozisyon_alani_yok = 0
    # OI = 0 ve hacim > 0 olan kontratlar: "yeni pozisyon aciliyor" vekilinin
    # en guclu hali. Ayrica sayilir cunku OI filtresi bunlari elemektedir.
    yeni_pozisyon_adayi = 0

    for k in kontratlar:
        tip = str(k.get("option_type", "")).lower()
        if tip not in ("call", "put"):
            gecersiz_tip += 1
            continue

        hacim = _sayi(k.get("volume"))
        oi = _sayi(k.get("open_interest"))
        if hacim is None:
            hacim_alani_yok += 1
            hacim = 0.0
        if oi is None:
            acik_pozisyon_alani_yok += 1
            oi = 0.0

        sayim[tip]["kontrat"] += 1
        sayim[tip]["hacim"] += hacim
        sayim[tip]["acik_pozisyon"] += oi
        if oi == 0 and hacim > 0:
            yeni_pozisyon_adayi += 1

    toplam_hacim = sayim["call"]["hacim"] + sayim["put"]["hacim"]
    toplam_oi = sayim["call"]["acik_pozisyon"] + sayim["put"]["acik_pozisyon"]

    return {
        "kapsam": {
            "degerlendirilen_kontrat": sayim["call"]["kontrat"] + sayim["put"]["kontrat"],
            "gecersiz_tip": gecersiz_tip,
            "hacim_alani_eksik": hacim_alani_yok,
            "acik_pozisyon_alani_eksik": acik_pozisyon_alani_yok,
            "filtresiz": True,
        },
        "call": {k: round(v, 2) for k, v in sayim["call"].items()},
        "put": {k: round(v, 2) for k, v in sayim["put"].items()},
        "toplam_hacim": round(toplam_hacim, 2),
        "toplam_acik_pozisyon": round(toplam_oi, 2),
        "put_call_hacim_orani": _oran(sayim["put"]["hacim"], sayim["call"]["hacim"]),
        "put_call_acik_pozisyon_orani": _oran(sayim["put"]["acik_pozisyon"],
                                              sayim["call"]["acik_pozisyon"]),
        # Hacim/OI > 1: o gun el degistiren kontrat sayisi, acik duran
        # pozisyondan fazla. Gun ici/kisa vadeli yogunluga isaret eden bir
        # OLCUMDUR; yon iddiasi TASIMAZ.
        "hacim_acik_pozisyon_orani": _oran(toplam_hacim, toplam_oi),
        "acik_pozisyonsuz_hacimli_kontrat": yeni_pozisyon_adayi,
        "kalibrasyon_gecerli": KALIBRASYON_GECERLI,
        "not": (
            "Bu alanlar OLGUSAL SAYIMDIR, tahmin degildir; yon iddiasi "
            "tasimaz ve hicbir karar koduna baglanmaz (lambda = 0). Tek "
            "gunluk anlik goruntudur: tarihce tutulmadigi icin yuzdelik "
            "dilim/z-skoru URETILMEZ ve mutlak bir 'yuksek/dusuk' esigi "
            "YOKTUR — tek basina yorumlanamaz. Ucretsiz zincirde islem "
            "seviyesi tape bulunmadigi icin alis/satis yonu atanamaz, bu "
            "nedenle net-prim tarzi bir akis skoru hesaplanmamistir. "
            "Sayimlar zincirin FILTRESIZ halinden uretilir; min_acik_pozisyon "
            "filtresi acik pozisyonu 0 olan hacimli kontratlari elerdi."
        ),
    }
