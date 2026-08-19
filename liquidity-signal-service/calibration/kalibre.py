"""
Likidite sinyali kalibrasyonu — YENIDEN URETILEBILIR.

=======================================================================
BU DOSYA NEDEN VAR
=======================================================================
Onceki surumde servis "9 spesifikasyonun hicbiri baz orani geceMEDI"
iddiasini tasiyordu ama bu iddiayi ureten betik SERVISTE YOKTU
(yalnizca gecici bir calisma dizinindeydi). Yani servis, kimsenin
yeniden uretemedigi bir sayiyi gercek gibi tasiyordu. Bu dosya o
bosluğu kapatir: kalibrasyon artik depoda, veri anlik goruntusuyle
birlikte, tek komutla yeniden calistirilabilir.

    python3 calibration/kalibre.py

=======================================================================
BULUNAN HATA: "isabet - baz" KARSILASTIRMASI GECERSIZDI
=======================================================================
Eski betik su iki sayiyi karsilastiriyordu:

  hit_rate  = (YUKARI sinyallerinin dogrusu + ASAGI sinyallerinin
               dogrusu) / toplam sinyal          <- KARISIK metrik
  base_rate = P(fiyat yukari), tum gunler        <- TEK YONLU referans

Bu gecersizdir, cunku iki sinyal turunun sans karsiligi FARKLIDIR:

  YUKARI sinyali "dogru" ise fiyat yukari cikmistir -> sans = P(yukari)
  ASAGI  sinyali "dogru" ise fiyat asagi inmistir   -> sans = 1-P(yukari)

Yukselen bir piyasada (P(yukari)=%68.9) ASAGI sinyali en iyi ihtimalle
%31.1 isabet edebilir. Bunu %68.9'luk referansla kiyaslamak, sinyal ne
kadar iyi olursa olsun devasa negatif fark uretir.

Gercek olcum (NASDAQ h20, test penceresi):
  ASAGI sinyali 322 kez atesledi, isabet %28.9, sans karsiligi %31.1
    -> gercek fark: -2.2 puan
  Eski formul ayni hucreyi %68.9 ile kiyasladi
    -> raporlanan fark: -40 puan

Dokuz spesifikasyonda eski metrik basarisizligi ORTALAMA 17.1 PUAN
abartti. En kotu hucre -34.38 puandan -0.30 puana geldi.

DOGRU METRIK (bu dosyada uygulanan):
  beklenen_dogru = n_yukari * baz + n_asagi * (1 - baz)
  beceri_puan    = (gerceklesen_dogru - beklenen_dogru) / n * 100
Yani her sinyal turu KENDI sans referansiyla kiyaslanir.

=======================================================================
HATA DUZELTILDI — SONUC DEGISMEDI
=======================================================================
Metrik duzeltilince rakamlar cok daha az felaket gorunuyor, ANCAK
kenar yine de yok:

  duzeltilmis beceri araligi : -3.93 ile +1.63 puan
  gecme esigi (>= +5 puan)   : 0/9
  istatistiksel anlamli      : 0/9 (en dusuk p = 0.077)

Ek elemeler:
  - Esik taramasi: egitimde secilen en iyi esik (+3.8..+23.4 puan)
    testte cokuyor (-6.9..+6.7). Klasik asiri uyum. Esik sorunu DEGIL.
  - Isaret kararsizligi: sinyal EGITIMDE 9/9 pozitif, TESTTE 7/9
    negatif. Ters cevrilmis bir sinyal olsa iki pencerede de ayni
    yonde olurdu. Bu, gercek kenar yoklugunun imzasidir.
  - Guc: n~400-450 ile +5 puanlik kenari yakalama gucu ~%55
    (%80 guc icin n=785 gerekir). Ornek ideal degil; ancak olculen
    etki +1.6..-3.9 araliginda, yani 5 puana yakin bile degil.

KARAR: buzusme_lambda 0.0'da KALIR. Metrik hatasi duzeltildi ama
sonucu degistirmedi. Sahte bir kalibrasyon uretilmedi.
"""
import json
import math
import os
import statistics

VERI_YOLU = os.path.join(os.path.dirname(__file__), "fred_data.json")

EGITIM = ("2021-01-01", "2023-12-31")
TEST = ("2024-01-01", "2026-08-18")
UFUKLAR = (5, 10, 20)
VARLIK_ADLARI = ("NASDAQ", "SP500", "BTC")

# Gecme esigi: sinyalin baz orandan en az bu kadar iyi olmasi beklenir.
GECME_ESIGI_PUAN = 5.0
ALFA = 0.05


# ---------------------------------------------------------------- veri

def _sozluk(ciftler):
    return {d: v for d, v in ciftler}


def ffill(gunler, seri):
    """Her gun icin en son bilinen degeri dondurur (ileriye tasima)."""
    anahtarlar = sorted(seri.keys())
    ki, son, cikti = 0, None, []
    for g in gunler:
        while ki < len(anahtarlar) and anahtarlar[ki] <= g:
            son = seri[anahtarlar[ki]]
            ki += 1
        cikti.append(son)
    return cikti


def veri_yukle(yol=VERI_YOLU):
    D = json.load(open(yol))
    gunler = sorted(_sozluk(D["SP500"]).keys())
    walcl = ffill(gunler, _sozluk(D["WALCL"]))
    tga = ffill(gunler, _sozluk(D["TGA"]))
    # RRP FRED'de MILYAR USD; WALCL/TGA MILYON USD -> birim hizalanir
    rrp = [v * 1000 if v is not None else None
           for v in ffill(gunler, _sozluk(D["RRP"]))]
    net_likidite = [(w - t - r) if (w and t and r is not None) else None
                    for w, t, r in zip(walcl, tga, rrp)]
    varliklar = {a: ffill(gunler, _sozluk(D[a])) for a in VARLIK_ADLARI}
    return gunler, net_likidite, varliklar


# ---------------------------------------------------------------- faktorler

def zskor(seri, pencere=60):
    cikti = []
    for i, v in enumerate(seri):
        vals = [x for x in seri[max(0, i - pencere + 1):i + 1] if x is not None]
        if len(vals) < 5 or v is None:
            cikti.append(None)
            continue
        m = sum(vals) / len(vals)
        sd = math.sqrt(sum((x - m) ** 2 for x in vals) / (len(vals) - 1))
        cikti.append((v - m) / sd if sd > 0 else None)
    return cikti


def yoy(seri, donem=252):
    return [None if (i < donem or v is None or seri[i - donem] in (None, 0))
            else (v / seri[i - donem] - 1) * 100
            for i, v in enumerate(seri)]


def momentum(seri, pencere=20):
    return [None if (i < pencere or v is None or seri[i - pencere] in (None, 0))
            else (v / seri[i - pencere] - 1) * 100
            for i, v in enumerate(seri)]


def rejim(i, net_lik, mom):
    if i < 60 or net_lik[i] is None:
        return "tanimsiz"
    kisa = statistics.mean([x for x in net_lik[max(0, i - 19):i + 1] if x is not None] or [0])
    uzun = statistics.mean([x for x in net_lik[max(0, i - 59):i + 1] if x is not None] or [0])
    if mom[i] is None or i < 21 or mom[i - 1] is None:
        return "tanimsiz"
    delta = mom[i] - mom[i - 1]
    if kisa - uzun > 0:
        return "genisleme_hizlaniyor" if delta > 0 else "genisleme_yavasliyor"
    return "daralma_hizlaniyor" if delta < 0 else "daralma_yavasliyor"


def kompozit_skor(rej, makas_z, sapma, lik_mom, fiyat_mom):
    """M2Quant kompoziti: rejim %50 + esik %30 + momentum %20."""
    if rej == "genisleme_hizlaniyor":
        r = 2 if (makas_z is not None and makas_z >= 2.0) else \
            (0 if (makas_z is not None and makas_z <= -2.0) else 1)
    elif rej == "genisleme_yavasliyor":
        r = 0 if (makas_z is not None and makas_z >= 2.0) else -1
    elif rej == "daralma_hizlaniyor":
        r = 0 if (makas_z is not None and makas_z >= 2.0) else \
            (-2 if (makas_z is not None and makas_z <= -2.0) else -1)
    elif rej == "daralma_yavasliyor":
        r = 1 if (makas_z is not None and makas_z >= 2.0) else 0
    else:
        r = 0

    if sapma is None:
        t = 0
    elif sapma <= -2.0:
        t = 2
    elif sapma <= -1.5:
        t = 1
    elif sapma >= 2.0:
        t = -2
    elif sapma >= 1.5:
        t = -1
    else:
        t = 0

    if lik_mom is None or fiyat_mom is None:
        m = 0
    elif lik_mom > 0 and lik_mom > fiyat_mom:
        m = 1
    elif lik_mom < 0 and lik_mom < fiyat_mom:
        m = -1
    else:
        m = 0

    return 0.5 * r + 0.3 * t + 0.2 * m


def skor_serisi(net_likidite, fiyatlar):
    lik_z = zskor(net_likidite, 60)
    lik_yoy = yoy(net_likidite, 252)
    lik_mom = momentum(net_likidite, 20)
    f_z = zskor(fiyatlar, 60)
    f_yoy = yoy(fiyatlar, 252)
    f_mom = momentum(fiyatlar, 20)
    makas = [(a - b) if (a is not None and b is not None) else None
             for a, b in zip(lik_yoy, f_yoy)]
    sapma = [(a - b) if (a is not None and b is not None) else None
             for a, b in zip(f_z, lik_z)]
    makas_z = zskor(makas, 60)
    return [kompozit_skor(rejim(i, net_likidite, lik_mom),
                          makas_z[i], sapma[i], lik_mom[i], f_mom[i])
            for i in range(len(fiyatlar))]


# ---------------------------------------------------------------- metrikler

def beceri(gunler, skorlar, fiyatlar, ufuk, d0, d1,
           esik_poz=0.5, esik_neg=-0.5):
    """
    DOGRU metrik: her sinyal turu KENDI sans referansiyla kiyaslanir.

      YUKARI sinyali -> sans karsiligi = baz       (P(yukari))
      ASAGI  sinyali -> sans karsiligi = 1 - baz   (P(asagi))

    Eski (hatali) metrik ikisinin karisimini yalnizca baz ile
    kiyasliyordu; bkz. modul basligi.
    """
    n_yuk = i_yuk = n_asg = i_asg = 0
    yukselen = toplam_gun = 0
    for i, g in enumerate(gunler):
        if g < d0 or g > d1 or i + ufuk >= len(fiyatlar):
            continue
        p0, p1 = fiyatlar[i], fiyatlar[i + ufuk]
        if p0 is None or p1 is None:
            continue
        yukari = p1 > p0
        toplam_gun += 1
        yukselen += 1 if yukari else 0
        s = skorlar[i]
        if s is None:
            continue
        if s >= esik_poz:
            n_yuk += 1
            i_yuk += 1 if yukari else 0
        elif s <= esik_neg:
            n_asg += 1
            i_asg += 1 if not yukari else 0

    n = n_yuk + n_asg
    if toplam_gun == 0 or n == 0:
        return None
    baz = yukselen / toplam_gun
    dogru = i_yuk + i_asg
    beklenen = n_yuk * baz + n_asg * (1 - baz)
    varyans = n_yuk * baz * (1 - baz) + n_asg * baz * (1 - baz)
    se = math.sqrt(varyans)
    z = (dogru - beklenen) / se if se > 0 else 0.0
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return {
        "n": n, "n_yukari": n_yuk, "n_asagi": n_asg,
        "isabet_yukari": i_yuk / n_yuk if n_yuk else None,
        "isabet_asagi": i_asg / n_asg if n_asg else None,
        "baz_oran": baz,
        "gerceklesen_dogru": dogru,
        "beklenen_dogru": beklenen,
        "beceri_puan": (dogru - beklenen) / n * 100,
        "z": z, "p": p,
        "toplam_gun": toplam_gun,
    }


def eski_hatali_metrik(gunler, skorlar, fiyatlar, ufuk, d0, d1,
                       esik_poz=0.5, esik_neg=-0.5):
    """
    Eski metrigin BIREBIR kopyasi — yalnizca hatanin buyuklugunu
    gosterebilmek icin tutuluyor. Karar almakta KULLANILMAZ.
    """
    dogru = toplam_sinyal = yukselen = toplam_gun = 0
    for i, g in enumerate(gunler):
        if g < d0 or g > d1 or i + ufuk >= len(fiyatlar):
            continue
        p0, p1 = fiyatlar[i], fiyatlar[i + ufuk]
        if p0 is None or p1 is None:
            continue
        yukari = p1 > p0
        toplam_gun += 1
        yukselen += 1 if yukari else 0
        s = skorlar[i]
        if s is None:
            continue
        if s >= esik_poz:
            toplam_sinyal += 1
            dogru += 1 if yukari else 0
        elif s <= esik_neg:
            toplam_sinyal += 1
            dogru += 1 if not yukari else 0
    if toplam_gun == 0 or toplam_sinyal == 0:
        return None
    baz = yukselen / toplam_gun
    isabet = dogru / toplam_sinyal
    return {"isabet": isabet, "baz_oran": baz,
            "fark_puan": (isabet - baz) * 100}


# ---------------------------------------------------------------- calistir

def calistir(yazdir=True):
    gunler, net_lik, varliklar = veri_yukle()
    sonuc = {"spesifikasyonlar": [], "ozet": {}}

    if yazdir:
        print("=" * 104)
        print("LIKIDITE SINYALI KALIBRASYONU — duzeltilmis metrik")
        print(f"egitim: {EGITIM[0]} -> {EGITIM[1]}   test: {TEST[0]} -> {TEST[1]}")
        print("=" * 104)
        print(f"{'spek':13s} {'ESKI(hatali)':>13s} {'DUZELTILMIS':>12s} {'abarti':>8s} "
              f"{'n':>5s} {'p':>7s} {'>=+5?':>6s}")
        print("-" * 104)

    for ad in VARLIK_ADLARI:
        fiyat = varliklar[ad]
        skor = skor_serisi(net_lik, fiyat)
        for h in UFUKLAR:
            te = beceri(gunler, skor, fiyat, h, *TEST)
            eg = beceri(gunler, skor, fiyat, h, *EGITIM)
            eski = eski_hatali_metrik(gunler, skor, fiyat, h, *TEST)
            gecti = te["beceri_puan"] >= GECME_ESIGI_PUAN
            kayit = {
                "varlik": ad, "ufuk": h,
                "egitim_beceri_puan": eg["beceri_puan"],
                "test_beceri_puan": te["beceri_puan"],
                "test_n": te["n"], "test_p": te["p"],
                "test_baz_oran": te["baz_oran"],
                "test_n_yukari": te["n_yukari"], "test_n_asagi": te["n_asagi"],
                "test_isabet_yukari": te["isabet_yukari"],
                "test_isabet_asagi": te["isabet_asagi"],
                "eski_hatali_fark_puan": eski["fark_puan"],
                "abarti_puan": te["beceri_puan"] - eski["fark_puan"],
                "gecti": gecti,
                "anlamli": te["p"] < ALFA,
            }
            sonuc["spesifikasyonlar"].append(kayit)
            if yazdir:
                print(f"{ad+' h'+str(h):13s} {eski['fark_puan']:>+13.2f} "
                      f"{te['beceri_puan']:>+12.2f} {kayit['abarti_puan']:>+8.2f} "
                      f"{te['n']:>5d} {te['p']:>7.3f} {'EVET' if gecti else 'hayir':>6s}")

    S = sonuc["spesifikasyonlar"]
    gecen = sum(1 for s in S if s["gecti"])
    anlamli = sum(1 for s in S if s["anlamli"])
    sonuc["ozet"] = {
        "toplam_spesifikasyon": len(S),
        "gecen_spesifikasyon": gecen,
        "anlamli_spesifikasyon": anlamli,
        "gecme_esigi_puan": GECME_ESIGI_PUAN,
        "alfa": ALFA,
        "en_iyi_beceri_puan": max(s["test_beceri_puan"] for s in S),
        "en_kotu_beceri_puan": min(s["test_beceri_puan"] for s in S),
        "en_dusuk_p": min(s["test_p"] for s in S),
        "ortalama_abarti_puan": sum(s["abarti_puan"] for s in S) / len(S),
        "buzusme_lambda": 0.0 if gecen < 3 else None,
        "karar": ("lambda=0.0 — kenar yok" if gecen < 3
                  else "INCELE: gecen spesifikasyon var"),
    }

    if yazdir:
        o = sonuc["ozet"]
        print()
        print("=" * 104)
        print(f"  gecen (>= +{GECME_ESIGI_PUAN} puan) : {gecen}/{len(S)}")
        print(f"  anlamli (p < {ALFA})        : {anlamli}/{len(S)}")
        print(f"  en iyi / en kotu beceri    : {o['en_iyi_beceri_puan']:+.2f} / "
              f"{o['en_kotu_beceri_puan']:+.2f} puan")
        print(f"  en dusuk p                 : {o['en_dusuk_p']:.3f}")
        print(f"  eski metrigin ORTALAMA abartisi: {o['ortalama_abarti_puan']:+.2f} puan")
        print(f"  KARAR                      : {o['karar']}")
        print("=" * 104)

    return sonuc


if __name__ == "__main__":
    s = calistir()
    yol = os.path.join(os.path.dirname(__file__), "kalibrasyon_sonuc.json")
    json.dump(s, open(yol, "w"), indent=1, ensure_ascii=False)
    print(f"\nKaydedildi: {yol}")
