"""
FMP CAPRAZ DOGRULAMA (madde 37, 12.09.2026) - ikinci bagimsiz kaynaktan sapma olcumu.

NE YAPAR: skorlar.py'nin Z/M/F/DCF hesaplarinda kullandigi HAM mali tablo
kalemlerini financetoolkit (FMP) uzerinden BAGIMSIZ olarak ceker ve
yfinance-kaynakli degerle KAVRAM BAZINDA karsilastirir. Sapma OLCULUR ve
raporlanir; hangi kaynagin "dogru" oldugu KARAR VERILMEZ.

NE YAPMAZ: mevcut skor hesabini DEGISTIRMEZ. yfinance hala BIRINCIL
kaynaktir (skorlar.py/veri.py, degismedi, /skor/{ticker} akisi
etkilenmedi). Bu modul SALT-OKUNUR bir teshis katmanidir; yalnizca
GET /capraz-dogrula/{ticker} ucundan erisilir.

=======================================================================
KAVRAM ESLEMESI OLCULEREK KURULDU (tahmin edilmedi)
=======================================================================
AAPL/MSFT gercek verisiyle deger deger dogrulandi (12.09.2026):

  - yfinance 'Receivables' == FMP 'Net Receivables' (AAPL 2024: 66.243M,
    ikisi de). FMP'nin 'Accounts Receiv able' (33.410M) FARKLI, DAR bir
    alt kalemdir - kor bir isim eslemesi burada 2 KAT'lik SAHTE sapma
    uretirdi.
  - FMP donem etiketleri 'Y-DEC' desin, MSFT'nin fiskal yili Haziran'da
    bitiyor. Eslesme YIL SAYISINA gore yapilir, tarihe gore DEGIL: MSFT
    2026 icin FMP ve yfinance Total Assets BIREBIR ayni cikti (758.376M),
    yani FMP'nin 'Y-DEC' etiketi literal bir takvim ay'i degil, kutuphanenin
    kendi periyot adlandirma sozlesmesidir.
  - 'Ordinary Shares Number'/'Share Issued' FMP'nin UC TEMEL tablosunda
    (bilanco/gelir/nakit) HIC YOK - ESLENEMEZ olarak isaretlenir, sessizce
    atlanmaz.
  - 'Total Debt' GERCEK bir metodoloji farki tasir: FMP 119.059M vs
    yfinance 106.629M (AAPL 2024, %11,7 fark) - muhtemelen kira
    yukumluluklerinin (lease obligations) dahil edilme farki. Bu bir HATA
    DEGIL, olculen ve raporlanan bir sapmadir.
  - 'EBIT' de KUCUK bir sapma tasir: FMP 123.485M vs yfinance 123.216M
    (%0,22) - yontem farki (muhtemelen non-operating kalemlerin farkli
    siniflandirilmasi).

BUYUK_SAPMA_ESIGI (%5) bu iki OLCULEN sapmayi AYIRT EDECEK sekilde
secildi: EBIT'in dogal sapmasi (%0,22) esigin rahat altinda kalir, Total
Debt'in dogal sapmasi (%11,7) esigin rahat ustunde kalir. Esik keyfi bir
yuvarlak sayi degil, olculen iki gercek sapmanin ARASINA yerlestirildi.
"""
from __future__ import annotations

import math
import os
from typing import Optional

from .skorlar import Sirket


class CaprazHatasi(RuntimeError):
    """FMP erisim/bicim hatasi - sessizce yutulmaz."""


# concept_id: (yfinance_tablo, [yfinance_adaylar], fmp_tablo, fmp_etiket)
# fmp_etiket None ise kavram FMP'nin uc temel tablosunda YOKTUR (eslenemez).
KAVRAM_ESLEME = {
    "toplam_varlik":         ("bilanco", ["Total Assets"], "bilanco", "Total Assets"),
    "donen_varlik":          ("bilanco", ["Current Assets", "Total Current Assets"], "bilanco", "Total Current Assets"),
    "kv_yukumluluk":         ("bilanco", ["Current Liabilities", "Total Current Liabilities"], "bilanco", "Total Current Liabilities"),
    "dagitilmamis_kar":      ("bilanco", ["Retained Earnings"], "bilanco", "Retained Earnings"),
    "toplam_yukumluluk":     ("bilanco", ["Total Liabilities Net Minority Interest", "Total Liabilities"], "bilanco", "Total Liabilities"),
    "uzun_vadeli_borc":      ("bilanco", ["Long Term Debt"], "bilanco", "Long Term Debt"),
    "alacaklar":             ("bilanco", ["Receivables", "Accounts Receivable"], "bilanco", "Net Receivables"),
    "net_maddi_duran":       ("bilanco", ["Net PPE", "Net Property Plant And Equipment"], "bilanco", "Property, Plant and Equipment"),
    "nakit_ve_benzeri":      ("bilanco", ["Cash And Cash Equivalents"], "bilanco", "Cash and Cash Equivalents"),
    "toplam_borc":           ("bilanco", ["Total Debt"], "bilanco", "Total Debt"),
    "kisa_vadeli_borc":      ("bilanco", ["Current Debt"], "bilanco", "Short Term Debt"),
    "hisse_sayisi":          ("bilanco", ["Ordinary Shares Number", "Share Issued"], None, None),
    "faiz_vergi_oncesi_kar": ("gelir", ["EBIT", "Operating Income"], "gelir", "EBIT"),
    "hasilat":               ("gelir", ["Total Revenue", "Operating Revenue"], "gelir", "Revenue"),
    "net_kar":               ("gelir", ["Net Income", "Net Income Common Stockholders"], "gelir", "Net Income"),
    "brut_kar":              ("gelir", ["Gross Profit"], "gelir", "Gross Profit"),
    "satislarin_maliyeti":   ("gelir", ["Cost Of Revenue", "Cost Of Goods Sold"], "gelir", "Cost of Goods Sold"),
    "faaliyet_gideri":       ("gelir", ["Selling General And Administration"], "gelir", "Selling, General and Administrative Expenses"),
    "amortisman_gelir":      ("gelir", ["Reconciled Depreciation"], "gelir", "Depreciation and Amortization"),
    "faaliyet_nakit_akisi":  ("nakit", ["Operating Cash Flow", "Total Cash From Operating Activities"], "nakit", "Operating Cash Flow"),
    "serbest_nakit_akisi":   ("nakit", ["Free Cash Flow"], "nakit", "Free Cash Flow"),
    "yatirim_harcamasi":     ("nakit", ["Capital Expenditure"], "nakit", "Capital Expenditure"),
    "amortisman_nakit":      ("nakit", ["Depreciation And Amortization"], "nakit", "Depreciation and Amortization"),
    "odenen_temettu":        ("nakit", ["Cash Dividends Paid", "Common Stock Dividend Paid"], "nakit", "Common Dividends Paid"),
}

BUYUK_SAPMA_ESIGI = 0.05


def _anahtar_hazir_mi() -> tuple[bool, str]:
    k = os.getenv("FMP_API_KEY", "").strip()
    if not k:
        return False, "FMP_API_KEY tanimsiz; hicbir ag cagrisi YAPILMADI."
    return True, k


def _yfinance_deger(donem, tablo: str, adaylar: list) -> Optional[float]:
    """skorlar.py'deki Donem nesnesinden ayni adaylik mantigiyla deger okur."""
    sozluk = getattr(donem, tablo)
    for ad in adaylar:
        if ad in sozluk:
            v = sozluk[ad]
            if v is not None:
                return float(v)
    return None


def fmp_veri_getir(ticker: str, api_key: str, toolkit_fabrikasi=None) -> dict:
    """FMP'den (financetoolkit uzerinden) yil->tablo->kalem sozlugu doner.

    toolkit_fabrikasi enjekte edilebilir - testler AGA CIKMAZ, sahte bir
    Toolkit nesnesi verir (bkz. tests/test_fmp_capraz.py).
    """
    try:
        if toolkit_fabrikasi is None:
            from financetoolkit import Toolkit
            tk = Toolkit([ticker.upper()], api_key=api_key, quarterly=False)
        else:
            tk = toolkit_fabrikasi(ticker, api_key)
        bs = tk.get_balance_sheet_statement()
        ins = tk.get_income_statement()
        cf = tk.get_cash_flow_statement()
    except Exception as e:  # noqa: BLE001
        raise CaprazHatasi(f"FMP verisi alinamadi: {type(e).__name__}: {e}")

    if bs is None or getattr(bs, "empty", True):
        raise CaprazHatasi(f"{ticker}: FMP bilanco verisi bos dondu")

    def _yila_gore(df):
        cikti = {}
        if df is None or getattr(df, "empty", True):
            return cikti
        for kolon in df.columns:
            yil = str(kolon)[:4]
            cikti.setdefault(yil, {})
            for kalem in df.index:
                try:
                    v = float(df.loc[kalem, kolon])
                except (TypeError, ValueError):
                    continue
                if math.isnan(v):
                    continue
                cikti[yil][str(kalem)] = v
        return cikti

    return {"bilanco": _yila_gore(bs), "gelir": _yila_gore(ins), "nakit": _yila_gore(cf)}


def _fmp_deger(fmp_veri: dict, yil: str, tablo: str, etiket: Optional[str]) -> Optional[float]:
    if etiket is None:
        return None
    return fmp_veri.get(tablo, {}).get(yil, {}).get(etiket)


def capraz_dogrula(sirket: Sirket, api_key: Optional[str] = None,
                   toolkit_fabrikasi=None) -> dict:
    """Sirket'in (yfinance kaynakli) donemlerini FMP ile kavram kavram karsilastirir.

    HICBIR SEY KARAR VERMEZ: hangi kaynagin dogru oldugu soylenmez, yalnizca
    sapma olculur. `hisse_sayisi` gibi FMP'nin uc temel tablosunda hic
    olmayan kavramlar ESLENEMEZ olarak ayri listelenir - sessizce atlanmaz.
    """
    if not sirket.donemler:
        return {"olculebildi": False, "asama": "veri",
                "neden": "Sirket'te hic donem yok - once yfinance'ten mali tablo cekilmeli."}

    if api_key is None:
        hazir, deger = _anahtar_hazir_mi()
        if not hazir:
            return {"olculebildi": False, "asama": "anahtar", "neden": deger}
        api_key = deger

    try:
        fmp_veri = fmp_veri_getir(sirket.ticker, api_key, toolkit_fabrikasi)
    except CaprazHatasi as e:
        return {"olculebildi": False, "asama": "kaynak", "neden": str(e)}

    eslenemez = sorted(k for k, (_, _, ft, fe) in KAVRAM_ESLEME.items() if fe is None)
    sonuclar = []
    for donem in sirket.donemler:
        yil = donem.tarih[:4]
        for kavram, (y_tablo, y_adaylar, f_tablo, f_etiket) in KAVRAM_ESLEME.items():
            if f_etiket is None:
                continue
            yv = _yfinance_deger(donem, y_tablo, y_adaylar)
            fv = _fmp_deger(fmp_veri, yil, f_tablo, f_etiket)
            if yv is None or fv is None:
                sonuclar.append({"kavram": kavram, "yil": yil, "durum": "eksik",
                                 "yfinance_deger": yv, "fmp_deger": fv})
                continue
            # NEDEN math.inf DONDURULMEZ: JSON sonsuz deger TASIYAMAZ (bu
            # projede anomali servisinde OLCULEN ayni ders - bkz.
            # godmode-anomali-servisi/tests/test_anomali.py). yv=0 iken
            # fv!=0 goreli farki TANIMSIZ kilar; bu durum ACIKCA
            # `sifir_referans` ile isaretlenir, uydurma bir sayi (0 ya da
            # inf) JSON govdesine KONULMAZ.
            if yv == 0:
                if fv == 0:
                    goreli_fark, sifir_referans, buyuk = 0.0, False, False
                else:
                    goreli_fark, sifir_referans, buyuk = None, True, True
            else:
                goreli_fark = round((fv - yv) / abs(yv), 6)
                sifir_referans = False
                buyuk = abs(goreli_fark) >= BUYUK_SAPMA_ESIGI
            sonuclar.append({
                "kavram": kavram, "yil": yil, "durum": "karsilastirildi",
                "yfinance_deger": yv, "fmp_deger": fv,
                "goreli_fark": goreli_fark, "sifir_referans": sifir_referans,
                "buyuk_sapma": buyuk,
            })

    karsilastirilan = [s for s in sonuclar if s["durum"] == "karsilastirildi"]
    buyuk_sapmalar = [s for s in karsilastirilan if s["buyuk_sapma"]]
    return {
        "olculebildi": True,
        "ticker": sirket.ticker,
        "donem_sayisi": len(sirket.donemler),
        "kavram_sayisi": len(KAVRAM_ESLEME),
        "eslenemez_kavramlar": eslenemez,
        "eslenemez_gerekce": ("Bu kavramlar FMP'nin bilanco/gelir/nakit uc temel "
                             "tablosunda HIC yok; ESLENEMEZ, 'sapma yok' ile "
                             "KARISTIRILMAMALIDIR."),
        "karsilastirilan_gozlem": len(karsilastirilan),
        "eksik_gozlem": len(sonuclar) - len(karsilastirilan),
        "buyuk_sapma_esigi": BUYUK_SAPMA_ESIGI,
        "buyuk_sapma_sayisi": len(buyuk_sapmalar),
        "buyuk_sapmalar": buyuk_sapmalar,
        "tum_sonuclar": sonuclar,
        "not": ("Bu bir KARAR DEGIL, bir OLCUMDUR: hangi kaynagin dogru oldugu "
                "soylenmez. yfinance skor hesabinda BIRINCIL kaynak olarak "
                "KALDI, bu ciktinin skor uzerinde hicbir etkisi YOKTUR."),
    }
