"""Takilabilir olcut katmani testleri — Madde 38.

Katmanin varlik nedeni "yeni olcut eklemek kolay olsun" DEGIL, her olcutun
"olculemedi" diyebilmesidir. Testlerin agirligi orada.
"""
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, "/app/src")
sys.path.insert(0, "/app")

import olcut_katmani as ok  # noqa: E402


def _baglam(getiriler, **ek):
    t = {"getiriler": pd.Series(getiriler), "baslangic_nakit": 10000}
    t.update(ek)
    return t


# ----------------------------------------------------------- Olcut sozlesmesi
def test_olculemedi_durumunda_deger_none_olmali():
    with pytest.raises(ValueError):
        ok.Olcut(0.0, ok.OLCULEMEDI, "x")


def test_olculdu_durumunda_deger_none_olamaz():
    with pytest.raises(ValueError):
        ok.Olcut(None, ok.OLCULDU)


@pytest.mark.parametrize("bozuk", [float("inf"), float("-inf"), float("nan")])
def test_sonsuz_veya_nan_olcum_sayilmaz(bozuk):
    """Sonsuz bir oran olcum degil, bolme kazasidir."""
    with pytest.raises(ValueError):
        ok.Olcut(bozuk, ok.OLCULDU)


def test_gecersiz_durum_reddedilir():
    with pytest.raises(ValueError):
        ok.Olcut(1.0, "belki")


# --------------------------------------------------------- SHARPE (duzeltme)
def test_sharpe_degiskenlik_sifirken_OLCULEMEDI():
    """Onceki davranis 0.0 yaziyordu; ekranda 'olculdu, vasat' okunuyordu."""
    s = ok.calistir(_baglam([0.0] * 50))["sharpe"]
    assert s.durum == ok.OLCULEMEDI
    assert s.deger is None
    assert "TANIMSIZ" in s.gerekce


def test_sharpe_tek_gunde_OLCULEMEDI():
    s = ok.calistir(_baglam([0.01]))["sharpe"]
    assert s.durum == ok.OLCULEMEDI and "en az 2 gun" in s.gerekce


def test_sharpe_gercek_veride_olculur():
    rng = np.random.default_rng(42)
    g = rng.normal(0.0005, 0.01, 500)
    s = ok.calistir(_baglam(g))["sharpe"]
    assert s.durum == ok.OLCULDU and np.isfinite(s.deger)


def test_sharpe_bilinen_deger():
    """Sabit gunluk getiride Sharpe = sqrt(252)*ort/std; elle dogrulanir."""
    g = [0.01, -0.005] * 100
    ser = pd.Series(g)
    beklenen = float(np.sqrt(252) * ser.mean() / ser.std())
    s = ok.calistir(_baglam(g))["sharpe"]
    assert s.deger == pytest.approx(round(beklenen, 3), abs=1e-3)


# ------------------------------------------------------------------ SORTINO
def test_sortino_hic_kayip_yoksa_OLCULEMEDI():
    """Sonsuz Sortino bir olcum degildir."""
    s = ok.calistir(_baglam([0.01] * 100))["sortino"]
    assert s.durum == ok.OLCULEMEDI and s.deger is None
    assert "TANIMSIZ" in s.gerekce


def test_sortino_sharpeden_yuksek_olur_pozitif_carpikta():
    """Yukari yonlu oynaklik Sortino'yu cezalandirmaz, Sharpe'i cezalandirir."""
    g = [0.05] * 20 + [-0.001] * 80          # buyuk kazanclar, kucuk kayiplar
    r = ok.calistir(_baglam(g))
    assert r["sortino"].durum == ok.OLCULDU and r["sharpe"].durum == ok.OLCULDU
    assert r["sortino"].deger > r["sharpe"].deger


def test_sortino_tek_gunde_OLCULEMEDI():
    assert ok.calistir(_baglam([-0.01]))["sortino"].durum == ok.OLCULEMEDI


# ------------------------------------------------------------------- CALMAR
def test_calmar_dusus_yokken_OLCULEMEDI():
    s = ok.calistir(_baglam([0.001] * 300))["calmar"]
    assert s.durum == ok.OLCULEMEDI and "TANIMSIZ" in s.gerekce


def test_calmar_hic_islem_yokken_OLCULEMEDI():
    """Duz sifir getiri: dusus de sifir. Calmar 0 degil, olculemedi."""
    assert ok.calistir(_baglam([0.0] * 300))["calmar"].durum == ok.OLCULEMEDI


def test_calmar_olculur_ve_isaret_dogru():
    g = [0.01] * 150 + [-0.02] * 50 + [0.01] * 100
    s = ok.calistir(_baglam(g))["calmar"]
    assert s.durum == ok.OLCULDU and np.isfinite(s.deger)


def test_calmar_toplam_kayipta_olculemedi():
    """Birikimli deger sifira inerse yillik getiri tanimsizdir."""
    s = ok.calistir(_baglam([-1.0] + [0.01] * 10))["calmar"]
    assert s.durum == ok.OLCULEMEDI


# --------------------------------------------------------------- DUSUS SURESI
def test_en_uzun_dusus_bilinen_dizide():
    # 3 gun yukari, 4 gun asagi, sonra toparlanma
    g = [0.10, 0.10, 0.10, -0.05, -0.05, -0.05, -0.05, 0.50]
    s = ok.calistir(_baglam(g))["en_uzun_dusus_gun"]
    assert s.durum == ok.OLCULDU and s.deger == 4


def test_en_uzun_dusus_hic_dususte_sifir():
    s = ok.calistir(_baglam([0.01] * 10))["en_uzun_dusus_gun"]
    assert s.durum == ok.OLCULDU and s.deger == 0, (
        "gercek sifir bir OLCUMdur, olculemedi degil")


def test_en_uzun_kayip_serisi():
    g = [0.01, -0.01, -0.01, 0.01, -0.01, -0.01, -0.01, 0.01]
    s = ok.calistir(_baglam(g))["en_uzun_kayip_serisi"]
    assert s.deger == 3


# ------------------------------------------------------- diger olcutler
def test_bos_seride_hepsi_olculemedi():
    r = ok.calistir({"getiriler": pd.Series([], dtype=float)})
    getiriye_bagli = ["toplam_getiri_yuzde", "sharpe", "sortino", "calmar",
                      "maks_dusus_yuzde", "en_uzun_dusus_gun", "gun_sayisi"]
    for ad in getiriye_bagli:
        assert r[ad].durum == ok.OLCULEMEDI, f"{ad} bos seride olcum uretti"


def test_kazanma_orani_yoksa_olculemedi():
    r = ok.calistir(_baglam([0.01, -0.01]))
    assert r["kazanma_orani_yuzde"].durum == ok.OLCULEMEDI
    assert "TANIMSIZ" in r["kazanma_orani_yuzde"].gerekce


def test_kazanma_orani_sifir_gercek_olcumdur():
    r = ok.calistir(_baglam([0.01, -0.01], kazanan_oran=0.0))
    assert r["kazanma_orani_yuzde"].durum == ok.OLCULDU
    assert r["kazanma_orani_yuzde"].deger == 0.0


def test_islem_sayisi_sifir_gercek_olcumdur():
    r = ok.calistir(_baglam([0.0, 0.0], islem_sayisi=0))
    assert r["islem_sayisi"].durum == ok.OLCULDU and r["islem_sayisi"].deger == 0


def test_son_deger_nakit_bilinmiyorsa_olculemedi():
    r = ok.calistir({"getiriler": pd.Series([0.01, 0.01])})
    assert r["son_deger"].durum == ok.OLCULEMEDI


def test_toplam_getiri_bilinen_deger():
    r = ok.calistir(_baglam([0.10, 0.10]))
    assert r["toplam_getiri_yuzde"].deger == pytest.approx(21.0, abs=0.01)
    assert r["son_deger"].deger == pytest.approx(12100.0, abs=0.5)


# ------------------------------------------------------------ kosucu davranisi
def test_bilinmeyen_analizci_hata_degil_olculemedi():
    r = ok.calistir(_baglam([0.01, -0.01]), secim=["yok_boyle_bir_olcut"])
    assert r["yok_boyle_bir_olcut"].durum == ok.OLCULEMEDI
    assert "kayitli degil" in r["yok_boyle_bir_olcut"].gerekce


def test_bir_analizcinin_hatasi_digerlerini_GOTURMEZ():
    """Takilabilir katmanin butun anlami budur."""
    @ok.analizci("test_patlayan")
    def _patla(baglam):
        raise RuntimeError("kasitli hata")
    try:
        r = ok.calistir(_baglam([0.01, -0.01, 0.02]))
        assert r["test_patlayan"].durum == ok.OLCULEMEDI
        assert "kasitli hata" in r["test_patlayan"].gerekce
        assert r["sharpe"].durum == ok.OLCULDU, "saglam olcut de goturuldu"
    finally:
        ok.ANALIZCILER.pop("test_patlayan", None)


def test_ayni_ad_iki_kez_kaydedilemez():
    with pytest.raises(ValueError):
        ok.analizci("sharpe")(lambda b: None)


def test_secim_yalnizca_istenenleri_calistirir():
    r = ok.calistir(_baglam([0.01, -0.01]), secim=["sharpe", "sortino"])
    assert set(r) == {"sharpe", "sortino"}


def test_duz_sozluk_olculemedigi_none_yapar():
    d = ok.duz_sozluk(ok.calistir(_baglam([0.0] * 10)))
    assert d["sharpe"] is None, "olculemedi 0 olarak duzlestirildi"
    assert d["gun_sayisi"] == 10


def test_gerekceler_yalnizca_olculemeyenleri_listeler():
    g = ok.gerekceler(ok.calistir(_baglam([0.0] * 10)))
    assert "sharpe" in g and "gun_sayisi" not in g
