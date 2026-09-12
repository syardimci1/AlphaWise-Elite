"""
FMP CAPRAZ DOGRULAMA TESTLERI (madde 37, 12.09.2026).

AGA CIKMAZ - sahte bir Toolkit nesnesi enjekte edilir. Kullanilan sayilar
GERCEK olculen AAPL/MSFT verileridir (12.09.2026'da canli dogrulandi),
uydurulmadi:
  - Receivables: yfinance 66.243M == FMP Net Receivables 66.243M
    (FMP'nin Accounts Receivable'i 33.410M, FARKLI ve DAR bir alt kalem)
  - Total Debt: yfinance 106.629M vs FMP 119.059M (%11,7 GERCEK sapma)
  - EBIT: yfinance 123.216M vs FMP 123.485M (%0,22 GERCEK sapma)
"""
import math
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import fmp_capraz as FC
from src.skorlar import Donem, Sirket


class _SahteToolkit:
    """financetoolkit.Toolkit'in get_*_statement() yuzeyini taklit eder."""

    def __init__(self, bilanco: dict, gelir: dict, nakit: dict):
        self._bilanco, self._gelir, self._nakit = bilanco, gelir, nakit

    def _df(self, veri):
        return pd.DataFrame(veri) if veri else pd.DataFrame()

    def get_balance_sheet_statement(self):
        return self._df(self._bilanco)

    def get_income_statement(self):
        return self._df(self._gelir)

    def get_cash_flow_statement(self):
        return self._df(self._nakit)


def _fabrika(bilanco=None, gelir=None, nakit=None):
    def f(ticker, api_key):
        return _SahteToolkit(bilanco or {}, gelir or {}, nakit or {})
    return f


def _aapl_donem_2024():
    """OLCULEN gercek AAPL 2024 degerleri (yfinance tarafi)."""
    return Donem(
        tarih="2024-09-28",
        bilanco={"Total Assets": 364980000000.0,
                 "Receivables": 66243000000.0,
                 "Total Debt": 106629000000.0,
                 "Retained Earnings": -19154000000.0},
        gelir={"EBIT": 123216000000.0, "Total Revenue": 391035000000.0},
        nakit={"Operating Cash Flow": 118254000000.0},
    )


def _aapl_fmp_bilanco_2024():
    """OLCULEN gercek AAPL 2024 degerleri (FMP tarafi) - AYNI donem."""
    return {"2024": {"Total Assets": 364980000000.0,
                     "Net Receivables": 66243000000.0,
                     "Accounts Receivable": 33410000000.0,   # TUZAK: yanlis eslenirse yakalanmali
                     "Total Debt": 119059000000.0,
                     "Retained Earnings": -19154000000.0}}


# ===================================================== 1. TEMEL DOGRULUK
def test_ayni_degerde_sapma_SIFIR():
    d = _aapl_donem_2024()
    s = Sirket(ticker="AAPL", donemler=[d])
    fabrika = _fabrika(bilanco=_aapl_fmp_bilanco_2024())
    r = FC.capraz_dogrula(s, api_key="x", toolkit_fabrikasi=fabrika)
    assert r["olculebildi"] is True
    ta = next(x for x in r["tum_sonuclar"] if x["kavram"] == "toplam_varlik")
    assert ta["durum"] == "karsilastirildi"
    assert ta["goreli_fark"] == pytest.approx(0.0)
    assert ta["buyuk_sapma"] is False


def test_RECEIVABLES_DOGRU_kavrama_eslenir_YANLISA_DEGIL():
    """OLCULEN tuzak: FMP'nin 'Accounts Receivable'i (33.410M) yfinance'in
    'Receivables'inden (66.243M) YARI buyuklugundedir - kor bir isim
    eslemesi burada 2 KAT'lik SAHTE sapma uretirdi."""
    d = _aapl_donem_2024()
    s = Sirket(ticker="AAPL", donemler=[d])
    fabrika = _fabrika(bilanco=_aapl_fmp_bilanco_2024())
    r = FC.capraz_dogrula(s, api_key="x", toolkit_fabrikasi=fabrika)
    al = next(x for x in r["tum_sonuclar"] if x["kavram"] == "alacaklar")
    assert al["fmp_deger"] == pytest.approx(66243000000.0), (
        "FMP'nin DAR 'Accounts Receivable' kalemi yanlislikla secilmis")
    assert al["goreli_fark"] == pytest.approx(0.0)


def test_GERCEK_SAPMA_total_debt_BAYRAK_KALDIRIR():
    """OLCULEN gercek metodoloji farki: %11,7 sapma esigi (%5) asar."""
    d = _aapl_donem_2024()
    s = Sirket(ticker="AAPL", donemler=[d])
    fabrika = _fabrika(bilanco=_aapl_fmp_bilanco_2024())
    r = FC.capraz_dogrula(s, api_key="x", toolkit_fabrikasi=fabrika)
    td = next(x for x in r["tum_sonuclar"] if x["kavram"] == "toplam_borc")
    assert td["goreli_fark"] == pytest.approx((119059000000.0 - 106629000000.0) / 106629000000.0, abs=1e-6)
    assert td["buyuk_sapma"] is True
    assert any(b["kavram"] == "toplam_borc" for b in r["buyuk_sapmalar"])


def test_KUCUK_SAPMA_ebit_BAYRAK_KALDIRMAZ():
    """OLCULEN gercek yontem farki: %0,22 sapma esigin (%5) rahat altinda."""
    d = _aapl_donem_2024()
    s = Sirket(ticker="AAPL", donemler=[d])
    fabrika = _fabrika(bilanco=_aapl_fmp_bilanco_2024(),
                       gelir={"2024": {"EBIT": 123485000000.0}})
    r = FC.capraz_dogrula(s, api_key="x", toolkit_fabrikasi=fabrika)
    e = next(x for x in r["tum_sonuclar"] if x["kavram"] == "faiz_vergi_oncesi_kar")
    assert abs(e["goreli_fark"]) < 0.05
    assert e["buyuk_sapma"] is False


# =========================================== 2. ESLENEMEZ KAVRAM (hisse_sayisi)
def test_hisse_sayisi_ESLENEMEZ_listede_sessizce_ATLANMAZ():
    d = _aapl_donem_2024()
    s = Sirket(ticker="AAPL", donemler=[d])
    fabrika = _fabrika(bilanco=_aapl_fmp_bilanco_2024())
    r = FC.capraz_dogrula(s, api_key="x", toolkit_fabrikasi=fabrika)
    assert "hisse_sayisi" in r["eslenemez_kavramlar"]
    assert not any(x["kavram"] == "hisse_sayisi" for x in r["tum_sonuclar"]), (
        "eslenemez kavram karsilastirma listesine sizmis")
    assert "KARISTIRILMAMALIDIR" in r["eslenemez_gerekce"]


# ===================================================== 3. EKSIK VERI
def test_FMP_veri_yoksa_EKSIK_denir_SIFIR_DEGIL():
    """FMP'nin GENEL olarak veri dondugu ama BU KALEMIN o yil icin eksik
    oldugu durum - 'eksik' denir, sessizce 0/None ile doldurulmaz."""
    d = _aapl_donem_2024()
    s = Sirket(ticker="AAPL", donemler=[d])
    eksik_bilanco = {"2024": {"Retained Earnings": -19154000000.0}}  # Total Assets YOK
    fabrika = _fabrika(bilanco=eksik_bilanco)
    r = FC.capraz_dogrula(s, api_key="x", toolkit_fabrikasi=fabrika)
    ta = next(x for x in r["tum_sonuclar"] if x["kavram"] == "toplam_varlik")
    assert ta["durum"] == "eksik"
    assert ta.get("goreli_fark") is None


# ===================================================== 4. SIFIRA BOLME
def test_sifir_referansta_JSON_GUVENLI_deger_doner():
    """math.inf DEGIL - JSON sonsuz deger tasiyamaz (anomali servisinde
    olculen ayni ders)."""
    import json
    d = Donem(tarih="2024-01-01", bilanco={"Retained Earnings": 0.0}, gelir={}, nakit={})
    s = Sirket(ticker="X", donemler=[d])
    fabrika = _fabrika(bilanco={"2024": {"Retained Earnings": 500.0}})
    r = FC.capraz_dogrula(s, api_key="x", toolkit_fabrikasi=fabrika)
    re_ = next(x for x in r["tum_sonuclar"] if x["kavram"] == "dagitilmamis_kar")
    assert re_["sifir_referans"] is True
    assert re_["goreli_fark"] is None
    assert re_["buyuk_sapma"] is True
    json.dumps(r)   # patlamamali


def test_iki_taraf_da_sifirsa_sapma_sifir():
    d = Donem(tarih="2024-01-01", bilanco={"Retained Earnings": 0.0}, gelir={}, nakit={})
    s = Sirket(ticker="X", donemler=[d])
    fabrika = _fabrika(bilanco={"2024": {"Retained Earnings": 0.0}})
    r = FC.capraz_dogrula(s, api_key="x", toolkit_fabrikasi=fabrika)
    re_ = next(x for x in r["tum_sonuclar"] if x["kavram"] == "dagitilmamis_kar")
    assert re_["goreli_fark"] == 0.0 and re_["buyuk_sapma"] is False


# =========================================== 5. FISKAL YIL HIZALAMASI
def test_FISKAL_yil_haziran_bitse_de_YIL_SAYISIYLA_eslesir():
    """OLCULDU (MSFT): FMP 'Y-DEC' etiketi tasir ama fiskal yil Haziran'da
    biter. Eslesme yfinance tarihinin YIL SAYISIYLA yapilir."""
    d = Donem(tarih="2026-06-30", bilanco={"Total Assets": 758376000000.0}, gelir={}, nakit={})
    s = Sirket(ticker="MSFT", donemler=[d])
    fabrika = _fabrika(bilanco={"2026": {"Total Assets": 758376000000.0}})
    r = FC.capraz_dogrula(s, api_key="x", toolkit_fabrikasi=fabrika)
    ta = next(x for x in r["tum_sonuclar"] if x["kavram"] == "toplam_varlik")
    assert ta["goreli_fark"] == pytest.approx(0.0)


# ===================================================== 6. FAIL-LOUD
def test_anahtar_yoksa_AG_CAGRISI_YAPILMAZ(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    d = _aapl_donem_2024()
    s = Sirket(ticker="AAPL", donemler=[d])
    cagrildi = []
    def patlatan_fabrika(t, k):
        cagrildi.append(1); raise RuntimeError("ag'a cikildi")
    r = FC.capraz_dogrula(s, toolkit_fabrikasi=patlatan_fabrika)
    assert r["olculebildi"] is False and r["asama"] == "anahtar"
    assert not cagrildi, "anahtar yokken FMP'ye istek gitmis"


def test_toolkit_hata_verirse_OLCULEMEDI():
    def patlat(t, k): raise ValueError("gecersiz ticker")
    d = _aapl_donem_2024()
    s = Sirket(ticker="AAPL", donemler=[d])
    r = FC.capraz_dogrula(s, api_key="x", toolkit_fabrikasi=patlat)
    assert r["olculebildi"] is False and r["asama"] == "kaynak"


def test_donem_yoksa_OLCULEMEDI():
    s = Sirket(ticker="AAPL", donemler=[])
    r = FC.capraz_dogrula(s, api_key="x", toolkit_fabrikasi=_fabrika())
    assert r["olculebildi"] is False and r["asama"] == "veri"


def test_bos_FMP_bilanco_KaynakHatasi():
    with pytest.raises(FC.CaprazHatasi, match="bos"):
        FC.fmp_veri_getir("AAPL", "x", toolkit_fabrikasi=_fabrika())


# =========================================== 7. KARAR ETKISI YOK (izolasyon)
def test_capraz_dogrulama_SKOR_HESABINA_KARISMAZ():
    """Yapisal kanit: sentez.py capraz dogrulamayi import etmiyor."""
    import inspect
    from src import sentez
    kaynak = inspect.getsource(sentez)
    assert "fmp_capraz" not in kaynak


def test_sonuc_HER_ZAMAN_karar_uretmez_notu_tasir():
    d = _aapl_donem_2024()
    s = Sirket(ticker="AAPL", donemler=[d])
    r = FC.capraz_dogrula(s, api_key="x", toolkit_fabrikasi=_fabrika(bilanco=_aapl_fmp_bilanco_2024()))
    assert "KARAR DEGIL" in r["not"]
