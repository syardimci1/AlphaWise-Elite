"""
Bes eksenli temel skor sentezi — akademik formullerin kendi uygulamamiz.

KAYNAK VE BAGIMSIZLIK
=====================
Formuller yayimlanmis akademik tanimlarindan yazildi; hicbir kutuphaneden
veya depodan kod KOPYALANMADI:
  - Altman, E. (1968) "Financial Ratios, Discriminant Analysis and the
    Prediction of Corporate Bankruptcy"                     -> Z-Score
  - Piotroski, J. (2000) "Value Investing: The Use of Historical Financial
    Statement Information..."                               -> F-Score (0-9)
  - Beneish, M. (1999) "The Detection of Earnings Manipulation" -> M-Score
  - Iki asamali indirgenmis nakit akisi (standart kurumsal finans)  -> DCF

NEDEN financetoolkit KULLANILMADI
=================================
Konteynerde kurulu olmasina ragmen `financetoolkit.models` sinifi OLCULDU:
FinancialModelPrep API ANAHTARI olmadan calismiyor (enforce_source=
"YahooFinance" verilse bile ayni hatayi veriyor). Ucretli bagimlilik butce
kurali geregi onaysiz kurulamaz. yfinance ise ayni ham tablolari ucretsiz
veriyor (MSFT: bilanco 79 kalem x 5 donem), bu yuzden hesap kendi kodumuzda.

EN ONEMLI KURAL
===============
Her olcut, veri eksikse SIFIR degil OLCULEMEDI doner; olcut sirket turune
uymuyorsa UYGULANAMAZ doner (bkz. olcum.py). Sifir, yalnizca gercekten
olculmus bir sifirdir.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .olcum import Olcum, olculdu, olculemedi, uygulanamaz


@dataclass
class Donem:
    """Tek bir mali donemin uc tablosu. Anahtarlar yfinance kalem adlaridir."""
    tarih: str
    bilanco: dict = field(default_factory=dict)
    gelir: dict = field(default_factory=dict)
    nakit: dict = field(default_factory=dict)


@dataclass
class Sirket:
    """donemler EN YENI ONCE siralidir: donemler[0] = t, donemler[1] = t-1 ..."""
    ticker: str
    donemler: list
    piyasa: dict = field(default_factory=dict)


# --------------------------------------------------------------- yardimcilar
def _al(sozluk: dict, *adaylar) -> Optional[float]:
    """Es anlamli kalem adlarindan ILK bulunani dondur. yfinance ayni kalemi
    sirkete gore farkli adlandirabiliyor (ornegin 'Total Liabilities Net
    Minority Interest' vs 'Total Liabilities')."""
    for ad in adaylar:
        if ad in sozluk:
            d = sozluk[ad]
            if d is not None:
                try:
                    f = float(d)
                except (TypeError, ValueError):
                    continue
                if f == f:  # NaN degil
                    return f
    return None


def _oran(pay: Optional[float], payda: Optional[float]) -> Optional[float]:
    if pay is None or payda is None or payda == 0:
        return None
    return pay / payda


def _eksikleri_bul(istekler: dict) -> tuple:
    return tuple(ad for ad, deger in istekler.items() if deger is None)


FINANSAL_SEKTORLER = ("financial services", "financial", "banks", "insurance",
                      "capital markets", "finansal")


def _finansal_kurum_mu(sirket: Sirket) -> bool:
    sektor = str(sirket.piyasa.get("sektor") or "").strip().lower()
    return any(a in sektor for a in FINANSAL_SEKTORLER)


# ------------------------------------------------------------------ ALTMAN Z
def altman_z(sirket: Sirket) -> Olcum:
    """Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5  (Altman 1968, halka acik
    imalat sirketleri icin orijinal katsayilar).

    Bankalara/sigortaya UYGULANAMAZ: siniflandirilmis bilancolari yoktur, bu
    yuzden X1 (isletme sermayesi/aktif) tanimsizdir. Olcumle dogrulandi:
    yfinance JPM icin Current Assets / Current Liabilities / EBIT kalemlerini
    HIC dondurmuyor.
    """
    if _finansal_kurum_mu(sirket):
        return uygulanamaz(
            "Altman Z-Score finansal kurumlara uygulanmaz: bankalarin "
            "siniflandirilmis bilancosu olmadigi icin isletme sermayesi "
            "terimi tanimsizdir.")
    if not sirket.donemler:
        return olculemedi("Mali tablo donemi yok")

    d = sirket.donemler[0]
    ta = _al(d.bilanco, "Total Assets")
    isletme_sermayesi = _al(d.bilanco, "Working Capital")
    if isletme_sermayesi is None:
        ca = _al(d.bilanco, "Current Assets", "Total Current Assets")
        cl = _al(d.bilanco, "Current Liabilities", "Total Current Liabilities")
        isletme_sermayesi = None if (ca is None or cl is None) else ca - cl
    re = _al(d.bilanco, "Retained Earnings")
    ebit = _al(d.gelir, "EBIT", "Operating Income")
    tl = _al(d.bilanco, "Total Liabilities Net Minority Interest", "Total Liabilities")
    satis = _al(d.gelir, "Total Revenue", "Operating Revenue")
    mve = sirket.piyasa.get("piyasa_degeri")

    istekler = {"Total Assets": ta, "Working Capital": isletme_sermayesi,
                "Retained Earnings": re, "EBIT": ebit,
                "Total Liabilities": tl, "Total Revenue": satis,
                "piyasa_degeri": mve}
    eksik = _eksikleri_bul(istekler)
    if eksik:
        return olculemedi("Altman Z icin gerekli kalemler eksik", eksik)

    x1 = _oran(isletme_sermayesi, ta)
    x2 = _oran(re, ta)
    x3 = _oran(ebit, ta)
    x4 = _oran(mve, tl)
    x5 = _oran(satis, ta)
    if None in (x1, x2, x3, x4, x5):
        return olculemedi("Altman Z bileseni sifira bolunuyor",
                          tuple(k for k, v in zip("X1 X2 X3 X4 X5".split(),
                                                  (x1, x2, x3, x4, x5)) if v is None))
    z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5
    return olculdu(z, X1=x1, X2=x2, X3=x3, X4=x4, X5=x5)


# --------------------------------------------------------------- PIOTROSKI F
def piotroski_f(sirket: Sirket) -> Olcum:
    """F-Score: dokuz ikili olcutun toplami (0-9).

    Piotroski donem BASI aktifini kullanir; bu yuzden ROA_t icin TA_{t-1},
    ROA_{t-1} icin TA_{t-2} gerekir -> UC donem sarttir. Uc donem yoksa skor
    kismi uretilmez, OLCULEMEDI donulur: dokuz olcutun bir kismini toplayip
    "F-Score" demek olcutu sessizce degistirmek olurdu.
    """
    if len(sirket.donemler) < 3:
        return olculemedi(
            f"F-Score icin 3 mali donem gerekir (donem basi aktifi kullanilir); "
            f"{len(sirket.donemler)} donem var")

    t, t1, t2 = sirket.donemler[0], sirket.donemler[1], sirket.donemler[2]

    ta_t1 = _al(t1.bilanco, "Total Assets")
    ta_t2 = _al(t2.bilanco, "Total Assets")
    ni_t = _al(t.gelir, "Net Income", "Net Income Common Stockholders")
    ni_t1 = _al(t1.gelir, "Net Income", "Net Income Common Stockholders")
    cfo_t = _al(t.nakit, "Operating Cash Flow", "Total Cash From Operating Activities")
    ltd_t = _al(t.bilanco, "Long Term Debt")
    ltd_t1 = _al(t1.bilanco, "Long Term Debt")
    ta_t = _al(t.bilanco, "Total Assets")
    ca_t = _al(t.bilanco, "Current Assets", "Total Current Assets")
    cl_t = _al(t.bilanco, "Current Liabilities", "Total Current Liabilities")
    ca_t1 = _al(t1.bilanco, "Current Assets", "Total Current Assets")
    cl_t1 = _al(t1.bilanco, "Current Liabilities", "Total Current Liabilities")
    hisse_t = _al(t.bilanco, "Ordinary Shares Number", "Share Issued")
    hisse_t1 = _al(t1.bilanco, "Ordinary Shares Number", "Share Issued")
    bk_t = _al(t.gelir, "Gross Profit")
    bk_t1 = _al(t1.gelir, "Gross Profit")
    sat_t = _al(t.gelir, "Total Revenue", "Operating Revenue")
    sat_t1 = _al(t1.gelir, "Total Revenue", "Operating Revenue")

    istekler = {
        "Total Assets(t)": ta_t, "Total Assets(t-1)": ta_t1, "Total Assets(t-2)": ta_t2,
        "Net Income(t)": ni_t, "Net Income(t-1)": ni_t1,
        "Operating Cash Flow(t)": cfo_t,
        "Long Term Debt(t)": ltd_t, "Long Term Debt(t-1)": ltd_t1,
        "Current Assets(t)": ca_t, "Current Liabilities(t)": cl_t,
        "Current Assets(t-1)": ca_t1, "Current Liabilities(t-1)": cl_t1,
        "Ordinary Shares Number(t)": hisse_t, "Ordinary Shares Number(t-1)": hisse_t1,
        "Gross Profit(t)": bk_t, "Gross Profit(t-1)": bk_t1,
        "Total Revenue(t)": sat_t, "Total Revenue(t-1)": sat_t1,
    }
    eksik = _eksikleri_bul(istekler)
    if eksik:
        return olculemedi("Piotroski F icin gerekli kalemler eksik", eksik)

    roa_t = ni_t / ta_t1
    roa_t1 = ni_t1 / ta_t2
    cfo_olcekli = cfo_t / ta_t1
    cari_t = ca_t / cl_t if cl_t else None
    cari_t1 = ca_t1 / cl_t1 if cl_t1 else None
    if cari_t is None or cari_t1 is None:
        return olculemedi("Cari oran hesaplanamadi (kisa vadeli yukumluluk sifir)")
    kaldirac_t = ltd_t / ta_t
    kaldirac_t1 = ltd_t1 / ta_t1
    marj_t = bk_t / sat_t
    marj_t1 = bk_t1 / sat_t1
    devir_t = sat_t / ta_t1
    devir_t1 = sat_t1 / ta_t2

    olcutler = {
        "roa_pozitif": roa_t > 0,
        "cfo_pozitif": cfo_t > 0,
        "roa_artti": roa_t > roa_t1,
        "tahakkuk_kalitesi": cfo_olcekli > roa_t,
        "kaldirac_azaldi": kaldirac_t < kaldirac_t1,
        "likidite_artti": cari_t > cari_t1,
        "yeni_hisse_ihraci_yok": hisse_t <= hisse_t1,
        "brut_marj_artti": marj_t > marj_t1,
        "varlik_devri_artti": devir_t > devir_t1,
    }
    return olculdu(float(sum(1 for v in olcutler.values() if v)), **olcutler)


# ---------------------------------------------------------------- BENEISH M
def beneish_m(sirket: Sirket) -> Olcum:
    """M = -4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI
            + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI

    M > -1.78 kazanc yonetimi olasiligina isaret eder. Iki donem gerekir.
    """
    if len(sirket.donemler) < 2:
        return olculemedi(f"M-Score icin 2 mali donem gerekir; "
                          f"{len(sirket.donemler)} donem var")
    t, t1 = sirket.donemler[0], sirket.donemler[1]

    def kalemler(d):
        return {
            "alacak": _al(d.bilanco, "Receivables", "Accounts Receivable",
                          "Net Receivables"),
            "satis": _al(d.gelir, "Total Revenue", "Operating Revenue"),
            "smm": _al(d.gelir, "Cost Of Revenue", "Cost Of Goods Sold"),
            "ca": _al(d.bilanco, "Current Assets", "Total Current Assets"),
            "ppe": _al(d.bilanco, "Net PPE", "Net Property Plant And Equipment"),
            "ta": _al(d.bilanco, "Total Assets"),
            "amortisman": _al(d.nakit, "Depreciation And Amortization",
                              "Depreciation Amortization Depletion",
                              "Reconciled Depreciation") or
                          _al(d.gelir, "Reconciled Depreciation"),
            "sga": _al(d.gelir, "Selling General And Administration",
                       "Selling General And Administrative"),
            "ni": _al(d.gelir, "Net Income", "Net Income Common Stockholders"),
            "cfo": _al(d.nakit, "Operating Cash Flow",
                       "Total Cash From Operating Activities"),
            "cl": _al(d.bilanco, "Current Liabilities", "Total Current Liabilities"),
            "ltd": _al(d.bilanco, "Long Term Debt"),
        }

    a, b = kalemler(t), kalemler(t1)
    eksik = tuple(f"{k}({'t' if s == 0 else 't-1'})"
                  for s, sz in enumerate((a, b)) for k, v in sz.items() if v is None)
    if eksik:
        return olculemedi("Beneish M icin gerekli kalemler eksik", eksik)

    def bol(p, q):
        return None if (q is None or q == 0) else p / q

    dsri = bol(bol(a["alacak"], a["satis"]), bol(b["alacak"], b["satis"]))
    bm_t = bol(a["satis"] - a["smm"], a["satis"])
    bm_t1 = bol(b["satis"] - b["smm"], b["satis"])
    gmi = bol(bm_t1, bm_t)
    aq_t = bol(a["ta"] - a["ca"] - a["ppe"], a["ta"])
    aq_t1 = bol(b["ta"] - b["ca"] - b["ppe"], b["ta"])
    aqi = bol(aq_t, aq_t1)
    sgi = bol(a["satis"], b["satis"])
    amo_t = bol(a["amortisman"], a["amortisman"] + a["ppe"])
    amo_t1 = bol(b["amortisman"], b["amortisman"] + b["ppe"])
    depi = bol(amo_t1, amo_t)
    sga_t = bol(a["sga"], a["satis"])
    sga_t1 = bol(b["sga"], b["satis"])
    sgai = bol(sga_t, sga_t1)
    tata = bol(a["ni"] - a["cfo"], a["ta"])
    kal_t = bol(a["cl"] + a["ltd"], a["ta"])
    kal_t1 = bol(b["cl"] + b["ltd"], b["ta"])
    lvgi = bol(kal_t, kal_t1)

    endeksler = {"DSRI": dsri, "GMI": gmi, "AQI": aqi, "SGI": sgi,
                 "DEPI": depi, "SGAI": sgai, "TATA": tata, "LVGI": lvgi}
    bozuk = tuple(k for k, v in endeksler.items() if v is None)
    if bozuk:
        return olculemedi("Beneish endeksi hesaplanamadi (sifira bolme)", bozuk)

    m = (-4.84 + 0.920 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi
         + 0.115 * depi - 0.172 * sgai + 4.679 * tata - 0.327 * lvgi)
    return olculdu(m, **endeksler)


# ---------------------------------------------------------------------- DCF
def dcf_icsel_fiyat_orani(sirket: Sirket, risksiz_faiz: Optional[float] = None,
                      hisse_risk_primi: float = 0.05,
                      surekli_buyume: float = 0.025,
                      tahmin_yili: int = 5) -> Olcum:
    """Iki asamali indirgenmis nakit akisi -> guvenlik payi.

    Iskonto orani CAPM ile OZ SERMAYE MALIYETIDIR (r = rf + beta * ERP).
    Bu bilincli bir BASITLESTIRMEDIR: tam WACC borc maliyeti ve hedef sermaye
    yapisi varsayimi gerektirir; ikisi de yfinance verisinden guvenilir
    turetilemez. Varsayim ciktida acikca bildirilir.

    Buyume orani, gecmis serbest nakit akisi bilesik buyumesinden turetilir ve
    [-%5, +%15] araligina KIRPILIR — tek yillik bir sicramanin sonsuza
    tasinmasini onlemek icin.

    Sonuc: ICSEL DEGER / FIYAT orani.

    NEDEN KLASIK "GUVENLIK PAYI" DEGIL
    ----------------------------------
    Ilk surum Graham'in klasik olcutunu, (icsel - fiyat)/icsel, donduruyordu.
    CANLI OLCUMDE bozuk davrandigi gorildu: icsel deger kuculdukce ifade
    SINIRSIZ buyuyor (TSLA icin -31.79 cikti) ve icsel deger sifirin altina
    dustugunde kod -1.0'e atliyordu — yani sifirin iki yanindaki iki komsu
    sirket -31.79 ve -1.0 gibi taban tabana zit degerler aliyordu (sureksizlik).

    icsel/fiyat orani ayni bilgiyi tasir ama MONOTON ve SUREKLIDIR: negatif
    ozkaynak dogal olarak <=0 orana, dolayisiyla 0 puana gider. Klasik
    guvenlik payi yine de ayrinti icinde bildirilir.
    """
    if risksiz_faiz is None:
        return olculemedi("Risksiz faiz orani alinamadi (DCF iskonto orani kurulamaz)")
    beta = sirket.piyasa.get("beta")
    fiyat = sirket.piyasa.get("fiyat")
    hisse_adedi = sirket.piyasa.get("hisse_adedi")
    istekler = {"beta": beta, "fiyat": fiyat, "hisse_adedi": hisse_adedi}
    eksik = _eksikleri_bul(istekler)
    if eksik:
        return olculemedi("DCF icin piyasa verisi eksik", eksik)

    fcf_serisi = []
    for d in sirket.donemler:
        f = _al(d.nakit, "Free Cash Flow")
        if f is None:
            cfo = _al(d.nakit, "Operating Cash Flow", "Total Cash From Operating Activities")
            capex = _al(d.nakit, "Capital Expenditure")
            f = None if (cfo is None or capex is None) else cfo + capex  # capex negatif
        if f is not None:
            fcf_serisi.append(f)
    if len(fcf_serisi) < 2:
        return olculemedi("DCF icin en az 2 donem serbest nakit akisi gerekir",
                          ("Free Cash Flow",))
    taban = fcf_serisi[0]
    if taban <= 0:
        return olculemedi("Guncel serbest nakit akisi pozitif degil; "
                          "iki asamali DCF anlamli sonuc uretmez")

    en_eski = fcf_serisi[-1]
    yil = len(fcf_serisi) - 1
    if en_eski > 0:
        buyume = (taban / en_eski) ** (1.0 / yil) - 1.0
    else:
        buyume = surekli_buyume
    buyume = max(-0.05, min(0.15, buyume))

    r = risksiz_faiz + float(beta) * hisse_risk_primi
    if r <= surekli_buyume:
        return olculemedi(f"Iskonto orani ({r:.4f}) surekli buyumenin "
                          f"({surekli_buyume}) altinda/esit; terminal deger tanimsiz")

    def _bugunku_deger(g: float) -> float:
        toplam, nakit = 0.0, taban
        for yil_no in range(1, tahmin_yili + 1):
            nakit = nakit * (1.0 + g)
            toplam += nakit / ((1.0 + r) ** yil_no)
        terminal = nakit * (1.0 + surekli_buyume) / (r - surekli_buyume)
        return toplam + terminal / ((1.0 + r) ** tahmin_yili)

    bugunku = _bugunku_deger(buyume)

    d0 = sirket.donemler[0]
    nakit_varlik = _al(d0.bilanco, "Cash And Cash Equivalents",
                       "Cash Cash Equivalents And Short Term Investments") or 0.0
    toplam_borc = _al(d0.bilanco, "Total Debt")
    if toplam_borc is None:
        ltd = _al(d0.bilanco, "Long Term Debt") or 0.0
        kvb = _al(d0.bilanco, "Current Debt") or 0.0
        toplam_borc = ltd + kvb
    net_borc = toplam_borc - nakit_varlik
    ozkaynak = bugunku - net_borc
    if hisse_adedi <= 0:
        return olculemedi("Hisse adedi pozitif degil")
    icsel = ozkaynak / hisse_adedi
    if float(fiyat) <= 0:
        return olculemedi("Fiyat pozitif degil")
    oran = icsel / float(fiyat)
    guvenlik_payi = None if icsel <= 0 else (icsel - float(fiyat)) / icsel

    # DUYARLILIK BANDI — bu eksen bes eksen icinde VARSAYIMA EN DUYARLI
    # olanidir. Tek bir sayi sunmak, sonuca hak etmedigi bir kesinlik
    # katardi; bu yuzden buyume varsayimi +-5 puan oynatildiginda icsel
    # degerin nereye gittigi de bildirilir.
    band = {}
    for etiket, g in (("dusuk", max(-0.05, buyume - 0.05)),
                      ("yuksek", min(0.15, buyume + 0.05))):
        oz = _bugunku_deger(g) - net_borc
        band[etiket] = {"buyume": g, "icsel_deger": oz / hisse_adedi}

    return olculdu(oran, icsel_deger=icsel, fiyat=float(fiyat),
                   klasik_guvenlik_payi=guvenlik_payi,
                   iskonto_orani=r, buyume=buyume, net_borc=net_borc,
                   duyarlilik=band,
                   varsayim="iskonto = risksiz faiz + beta x %5 hisse risk primi; "
                            "buyume gecmis serbest nakit akisindan turetilip "
                            "[-%5, +%15] araligina kirpildi")


# ------------------------------------------------------- TEMETTU DAYANIKLILIGI
def temettu_dayanikligi(sirket: Sirket) -> Olcum:
    """Bu eksen, digerlerinin aksine YAYIMLANMIS bir olcut degildir; kendi
    bilesimimizdir ve boyle etiketlenir. Uc bilesenin agirlikli ortalamasi:

      - Odeme orani saglami (temettu / net kar)     agirlik 0.40
      - Serbest nakit akisi kapsami (temettu / FCF) agirlik 0.40
      - Odeme surekliligi (kesintisiz yil sayisi)   agirlik 0.20

    Temettu ODEMEYEN sirket icin UYGULANAMAZ doner — sifir DEGIL. Sifir
    "temettusu var ama surdurulemez" demektir; ikisini karistirmak buyume
    sirketlerini haksiz cezalandirirdi.
    """
    if not sirket.donemler:
        return olculemedi("Mali tablo donemi yok")
    d = sirket.donemler[0]
    odenen = _al(d.nakit, "Cash Dividends Paid", "Common Stock Dividend Paid",
                 "Dividends Paid")
    if odenen is not None:
        odenen = abs(odenen)
    kesintisiz_yil = sirket.piyasa.get("temettu_kesintisiz_yil")

    if (odenen is None or odenen == 0) and not kesintisiz_yil:
        return uygulanamaz("Sirket temettu odemiyor; dayaniklilik olcutu "
                           "uygulanamaz (bu bir eksiklik degil, bir tercihtir).")
    if odenen is None:
        return olculemedi("Odenen temettu kalemi bulunamadi",
                          ("Cash Dividends Paid",))

    ni = _al(d.gelir, "Net Income", "Net Income Common Stockholders")
    fcf = _al(d.nakit, "Free Cash Flow")
    if fcf is None:
        cfo = _al(d.nakit, "Operating Cash Flow")
        capex = _al(d.nakit, "Capital Expenditure")
        fcf = None if (cfo is None or capex is None) else cfo + capex
    eksik = _eksikleri_bul({"Net Income": ni, "Free Cash Flow": fcf})
    if eksik:
        return olculemedi("Temettu dayanikliligi icin kalem eksik", eksik)

    def bilesen_puan(oran, iyi, kotu):
        """oran <= iyi -> 100, >= kotu -> 0, arada dogrusal."""
        if oran is None:
            return None
        if oran <= iyi:
            return 100.0
        if oran >= kotu:
            return 0.0
        return 100.0 * (kotu - oran) / (kotu - iyi)

    odeme_orani = None if ni is None or ni <= 0 else odenen / ni
    fcf_orani = None if fcf is None or fcf <= 0 else odenen / fcf
    # Kar veya nakit akisi negatifse temettu tanim geregi surdurulemez:
    # bu OLCULMUS bir sonuctur, eksik veri degil.
    p_odeme = 0.0 if (ni is not None and ni <= 0) else bilesen_puan(odeme_orani, 0.40, 1.00)
    p_fcf = 0.0 if (fcf is not None and fcf <= 0) else bilesen_puan(fcf_orani, 0.40, 1.00)
    yil = float(kesintisiz_yil or 0)
    p_sure = 100.0 * min(yil, 20.0) / 20.0

    if p_odeme is None or p_fcf is None:
        return olculemedi("Temettu bileseni hesaplanamadi")
    puan = 0.40 * p_odeme + 0.40 * p_fcf + 0.20 * p_sure
    return olculdu(puan, odeme_orani=odeme_orani, fcf_orani=fcf_orani,
                   kesintisiz_yil=yil, bilesen_odeme=p_odeme,
                   bilesen_fcf=p_fcf, bilesen_sure=p_sure,
                   not_="Yayimlanmis bir olcut degildir; AlphaWise bilesimidir.")
