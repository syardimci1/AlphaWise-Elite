"""
Backtest ↔ canli parite olcerinin regresyon agi (Madde 33).

BU TESTLER NEYI KORUR
=====================
09.09.2026 denetiminde olculen ayrisma SESSIZ olmaktan cikarildi. Testler
iki sey yapar:
  1. Olcerin DOGRU olctugunu kanitlar (Wilder formulu TA-Lib ile birebir mi).
  2. Ayrismanin HALEN VAR oldugunu kilitler. Biri iki yolu birlestirirse bu
     test duser ve denetim raporunun guncellenmesi gerektigi anlasilir —
     "ayni oldugunu varsayma" hatasi bir daha sessizce olusamaz.
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parite  # noqa: E402


def _seri(n=400, tohum=5):
    rng = np.random.default_rng(tohum)
    fiyat = 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.018, n)))
    return pd.Series(fiyat, index=pd.bdate_range("2020-01-01", periods=n))


# ---------------------------------------------------- olcerin dogrulugu
def test_wilder_formulu_TALIB_ile_AYNI():
    """Modul TA-Lib'e bagimli degil; ayni sonucu uretmesi TEST ile kilitlenir.
    TA-Lib yoksa test atlanmaz — ATLANAN TEST KORUMAZ; onun yerine acikca
    bildirilir ki eksiklik gorunur olsun."""
    try:
        import talib
    except ImportError:
        pytest.skip("TA-Lib bu ortamda yok — bu kilit yalnizca konteynerde kosar")
    s = _seri()
    beklenen = pd.Series(talib.RSI(s.values.astype(float), timeperiod=14), index=s.index)
    bizim = parite.rsi_wilder(s, 14)
    ortak = beklenen.notna() & bizim.notna()
    assert int(ortak.sum()) > 300
    fark = (beklenen[ortak] - bizim[ortak]).abs().max()
    assert fark < 1e-6, f"Wilder formulu TA-Lib'den sapiyor: maks fark {fark}"


def test_basit_formul_VECTORBT_ile_AYNI():
    try:
        import vectorbt as vbt
    except ImportError:
        pytest.skip("vectorbt bu ortamda yok — bu kilit yalnizca konteynerde kosar")
    s = _seri()
    beklenen = vbt.RSI.run(s, window=14).rsi.squeeze()
    bizim = parite.rsi_basit(s, 14)
    ortak = beklenen.notna() & bizim.notna()
    assert int(ortak.sum()) > 300
    fark = (beklenen[ortak] - bizim[ortak]).abs().max()
    assert fark < 1e-6, f"Basit formul vectorbt'den sapiyor: maks fark {fark}"


def test_iki_formul_BIRBIRINDEN_FARKLI():
    """Ayni girdide ayni sonucu verselerdi zaten ayrisma olmazdi."""
    s = _seri()
    a, b = parite.rsi_basit(s, 14), parite.rsi_wilder(s, 14)
    ortak = a.notna() & b.notna()
    assert (a[ortak] - b[ortak]).abs().max() > 1.0


# ------------------------------------------------- ayrismanin kilitlenmesi
def test_ayrisma_OLCULUYOR_ve_HALEN_VAR():
    """KILIT: iki yol birlestirilirse bu test duser ve denetim raporunun
    (docs/denetim_raporlari/backtest_canli_parite_2026-09-09.md)
    guncellenmesi gerektigi anlasilir."""
    o = parite.rsi_ayrismasi(_seri())
    assert o["durum"] == "olculdu"
    assert o["ortalama_fark"] > 0.5, (
        "Iki RSI yolu artik ayni gorunuyor — birlestirildiyse denetim raporu "
        "guncellenmeli, bu test ve raporun A1 bolumu gozden gecirilmeli.")
    assert o["esik_ayrisan_bar"] > 0, "esik karari hic ayrismiyorsa raporu guncelle"


def test_kisa_seride_OLCULEMEDI_der_SIFIR_demez():
    o = parite.rsi_ayrismasi(_seri(n=5))
    assert o["durum"] == "olculemedi"
    assert "gerekce" in o and "bar yok" in o["gerekce"]
    assert "ortalama_fark" not in o, "olculemedigi halde sayi uretilmemeli"


def test_esik_ayrisma_orani_SIFIR_ILE_BIR_arasinda():
    o = parite.rsi_ayrismasi(_seri(n=600, tohum=9))
    assert 0.0 <= o["esik_ayrisma_orani"] <= 1.0
    assert o["esik_ayrisan_bar"] <= o["bar"]


# ------------------------------------------------------ giris kosulu farki
def test_giris_kosulu_iki_yolda_FARKLI_sayida_tetikleniyor():
    """Denetimin en carpici olcumu: MSFT'te 57 gun (backtest) vs 2 gun (canli)."""
    o = parite.giris_kosulu_ayrismasi(_seri(n=800, tohum=3))
    assert o["backtest_giris_gun"] != o["canli_esdeger_giris_gun"]
    assert o["yalnizca_backtest"] + o["yalnizca_canli"] > 0


def test_giris_kosulu_sayimlari_TUTARLI():
    o = parite.giris_kosulu_ayrismasi(_seri(n=800, tohum=3))
    assert o["backtest_giris_gun"] == o["ortak_gun"] + o["yalnizca_backtest"]
    assert o["canli_esdeger_giris_gun"] == o["ortak_gun"] + o["yalnizca_canli"]


def test_trend_kosulu_saglanmayan_seride_giris_YOK():
    """Surekli dusen seride sma_hizli > sma_yavas olmaz -> hicbir yolda giris."""
    dusen = pd.Series(np.linspace(200, 100, 300),
                      index=pd.bdate_range("2020-01-01", periods=300))
    o = parite.giris_kosulu_ayrismasi(dusen)
    assert o["backtest_giris_gun"] == 0 and o["canli_esdeger_giris_gun"] == 0
