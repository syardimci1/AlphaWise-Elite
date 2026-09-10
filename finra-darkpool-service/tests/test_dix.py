"""DIX metodolojisi testleri — madde 41.

En kritik iki sozlesme:
  1. Sepette olup dosyada bulunmayan sembol SIFIR SAYILMAZ (sayilsaydi
     endeks yapay olarak asagi cekilirdi).
  2. Agirlik sessizce degistirilemez: dolar agirligi mumkun degilse
     hisse agirligina DUSULUR ama bu her yanitta acikca bildirilir.
"""
import sys

import pytest

sys.path.insert(0, "/app")

from src import dix  # noqa: E402
from src.dix import DOLAR_AGIRLIK, HISSE_AGIRLIK  # noqa: E402


def _v(**kv):
    """{'MSFT': (kisa, muaf, toplam)} kurar."""
    return {s.upper(): (k, 0.0, t) for s, (k, t) in kv.items()}


# --------------------------------------------------------------- temel
def test_tek_sembol_orani():
    r = dix.dix_hesapla(_v(MSFT=(40.0, 100.0)), ["MSFT"])
    assert r["olculdu"] is True and r["dix_yuzde"] == 40.0
    assert r["agirlik"] == HISSE_AGIRLIK


def test_hisse_agirligi_hacme_gore_tartar():
    """Buyuk hacimli sembol endeksi daha cok cekmeli."""
    v = _v(A=(10.0, 100.0), B=(90.0, 900.0))     # A %10, B %10 -> %10
    assert dix.dix_hesapla(v, ["A", "B"])["dix_yuzde"] == 10.0
    v2 = _v(A=(50.0, 100.0), B=(90.0, 900.0))    # A %50 ama kucuk
    r = dix.dix_hesapla(v2, ["A", "B"])
    assert r["dix_yuzde"] == pytest.approx(14.0), "(50+90)/1000"


def test_dolar_agirligi_fiyatla_tartar():
    v = _v(UCUZ=(50.0, 1000.0), PAHALI=(10.0, 100.0))
    hisse = dix.dix_hesapla(v, ["UCUZ", "PAHALI"])
    dolar = dix.dix_hesapla(v, ["UCUZ", "PAHALI"], {"UCUZ": 1.0, "PAHALI": 100.0})
    assert hisse["agirlik"] == HISSE_AGIRLIK
    assert dolar["agirlik"] == DOLAR_AGIRLIK
    assert dolar["dix_yuzde"] != hisse["dix_yuzde"], (
        "dolar agirligi sonucu degistirmeli, yoksa test anlamsiz")
    # UCUZ orani %5 (50/1000), PAHALI orani %10 (10/100).
    # hisse agirligi : (50 + 10) / 1100                      = %5,45
    # dolar agirligi : (0,05*1000 + 0,10*10000) / 11000      = %9,55
    # Pahali sembol dolar agirliginda baskin oldugu icin endeks yukseliyor.
    assert hisse["dix_yuzde"] == pytest.approx(5.45, abs=0.01)
    assert dolar["dix_yuzde"] == pytest.approx(9.55, abs=0.01)


# ------------------------------------------------- kapsam disi semboller
def test_dosyada_olmayan_sembol_SIFIR_SAYILMAZ():
    """Sifir saymak endeksi yapay olarak asagi cekerdi."""
    v = _v(A=(40.0, 100.0))
    r = dix.dix_hesapla(v, ["A", "YOK1", "YOK2"])
    assert r["dix_yuzde"] == 40.0, "eksik semboller orani dusurmus"
    assert r["katilan_sembol"] == 1 and r["kapsanmayan_sembol"] == 2
    assert r["kapsam_yuzde"] == pytest.approx(33.3, abs=0.1)
    assert set(r["kapsanmayanlar"]) == {"YOK1", "YOK2"}


def test_sifir_hacimli_sembol_kapsam_disi():
    v = _v(A=(40.0, 100.0), B=(0.0, 0.0))
    r = dix.dix_hesapla(v, ["A", "B"])
    assert r["katilan_sembol"] == 1 and "B" in r["kapsanmayanlar"]


def test_hicbir_sembol_kapsanmazsa_OLCULEMEDI():
    r = dix.dix_hesapla({}, ["A", "B"])
    assert r["olculdu"] is False and r["dix_yuzde"] is None
    assert r["sepet_boyu"] == 2 and r["kapsanmayan_sembol"] == 2
    assert "OLCULEMEDI" in r["not"]


def test_bos_sepet_olculemedi():
    r = dix.dix_hesapla(_v(A=(1.0, 2.0)), [])
    assert r["olculdu"] is False and "TANIMSIZ" in r["not"]
    r2 = dix.dix_hesapla(_v(A=(1.0, 2.0)), ["", "   ", None])
    assert r2["olculdu"] is False


def test_sepet_normalize_edilir():
    v = _v(MSFT=(40.0, 100.0))
    assert dix.dix_hesapla(v, [" msft "])["dix_yuzde"] == 40.0


# ------------------------------------------------------- agirlik dururstlugu
def test_fiyat_eksikse_agirlik_SESSIZCE_degismez():
    """Sepetin bir kismini dolar, kalanini hisse ile tartmak tanimsiz bir
    karisim uretirdi. Dolar agirligi TAMAMEN birakilir ve BILDIRILIR."""
    v = _v(A=(40.0, 100.0), B=(10.0, 100.0))
    r = dix.dix_hesapla(v, ["A", "B"], {"A": 10.0})      # B'nin fiyati yok
    assert r["agirlik"] == HISSE_AGIRLIK
    assert r["fiyati_olmayanlar"] == ["B"]
    assert "FARKLI bir olcumdur" in r["not"]
    assert r["dix_yuzde"] == 25.0, "hisse agirligiyla (40+10)/200"


@pytest.mark.parametrize("fiyat", [0, -1, None])
def test_gecersiz_fiyat_dolar_agirligini_dusurur(fiyat):
    v = _v(A=(40.0, 100.0), B=(10.0, 100.0))
    r = dix.dix_hesapla(v, ["A", "B"], {"A": 10.0, "B": fiyat})
    assert r["agirlik"] == HISSE_AGIRLIK and "B" in r["fiyati_olmayanlar"]


def test_kapsanmayan_sembolun_fiyatsizligi_dolar_agirligini_DUSURMEZ():
    """Dosyada zaten olmayan sembol icin fiyat aranmasi anlamsizdir."""
    v = _v(A=(40.0, 100.0))
    r = dix.dix_hesapla(v, ["A", "YOK"], {"A": 10.0})
    assert r["agirlik"] == DOLAR_AGIRLIK, (
        "kapsam disi sembol dolar agirligini dusurmus")
    assert r["fiyati_olmayanlar"] == []


def test_fiyat_verilmezse_dolar_iddia_edilmez():
    r = dix.dix_hesapla(_v(A=(40.0, 100.0)), ["A"])
    assert r["agirlik"] == HISSE_AGIRLIK
    assert "DIX dolar hacmiyle" in r["not"]


# -------------------------------------------------------- metodoloji notu
def test_resmi_dix_oldugu_IDDIA_EDILMEZ():
    r = dix.dix_hesapla(_v(A=(40.0, 100.0)), ["A"], {"A": 5.0})
    assert r["resmi_dix_mi"] is False
    assert "RESMI DIX DEGILDIR" in r["not"]
    assert "kalibre EDILMEMISTIR" in r["not"]


def test_sinir_oranlari():
    assert dix.dix_hesapla(_v(A=(0.0, 100.0)), ["A"])["dix_yuzde"] == 0.0
    assert dix.dix_hesapla(_v(A=(100.0, 100.0)), ["A"])["dix_yuzde"] == 100.0


def test_gercek_olcum_bandi():
    """10.09.2026'da CDN'den olculen degerlere yakin bir sepet."""
    v = _v(AAPL=(29846115.0, 77000000.0), MSFT=(4914333.0, 12000000.0),
           NVDA=(35128760.0, 78000000.0))
    r = dix.dix_hesapla(v, ["AAPL", "MSFT", "NVDA"])
    assert 35.0 < r["dix_yuzde"] < 55.0, (
        f"beklenen bant disinda: {r['dix_yuzde']}")
