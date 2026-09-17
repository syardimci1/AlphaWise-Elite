"""kuyruk_olasiligi.py testleri - oipd sarmalayicisi.

Audit #6'da (grup5_raporlar/06_oipd.md) canli SPY zinciriyle olculmus
davranislar burada REGRESYON testine cevrilir: negatif fiyat ValueError
(K3), <5 strike ValueError (K5), determinizm (K1)."""
import pandas as pd
import pytest

from kuyruk_olasiligi import openbb_zincirini_oipd_bicimine_cevir, hesapla


def _ornek_kontratlar():
    # audit #6'daki gercek SPY zincirinden kucultulmus, gercekci bir alt kume
    # oipd requires call/put pairs at matching strikes for forward inference
    # SVI calibration needs at least 5 unique strikes after parity processing
    kontratlar = []
    for strike, iv, tip in [
        # Puts: wider range to ensure survival after parity processing
        (730, 0.24, "put"), (740, 0.22, "put"), (750, 0.20, "put"), (760, 0.18, "put"), (770, 0.16, "put"),
        # Calls: matching strikes plus additional ones
        (740, 0.21, "call"), (750, 0.19, "call"), (760, 0.17, "call"), (770, 0.15, "call"), (780, 0.14, "call"),
    ]:
        kontratlar.append({
            "strike": strike, "option_type": tip,
            "implied_volatility": iv, "open_interest": 100,
            "expiration": "2026-10-16",
            "last_trade_price": max(0.5, (765.96 - strike) if tip == "call" else (strike - 765.96)),
        })
    return kontratlar


def test_donusum_tek_vade_dataframe_uretir():
    df = openbb_zincirini_oipd_bicimine_cevir(_ornek_kontratlar(), vade="2026-10-16")
    assert set(df["option_type"].unique()) <= {"call", "put"}
    assert len(df) == 10
    assert "strike" in df.columns and "last_price" in df.columns


def test_hesapla_gercekci_zincirle_calisir():
    sonuc = hesapla(_ornek_kontratlar(), spot=765.96, risksiz_oran=0.03775,
                    vade="2026-10-16", degerleme_tarihi="2026-09-08")
    assert sonuc["ortalama"] > 0
    assert "carpiklik" in sonuc
    assert 0.0 <= sonuc["spot_alti_olasilik"] <= 1.0
    assert set(sonuc["yuzdelikler"].keys()) == {"p05", "p50", "p95"}


def test_negatif_fiyat_ACIK_HATAYLA_reddedilir():
    """audit K3: negatif last_price -> ValueError, SESSIZCE yutulmaz."""
    kontratlar = _ornek_kontratlar()
    kontratlar[0]["last_trade_price"] = -5.0
    with pytest.raises(ValueError, match="negatif"):
        hesapla(kontratlar, spot=765.96, risksiz_oran=0.03775,
                vade="2026-10-16", degerleme_tarihi="2026-09-08")


def test_yetersiz_strike_ACIK_HATAYLA_reddedilir():
    """audit K5: <5 strike -> ValueError."""
    kontratlar = _ornek_kontratlar()[:2]
    with pytest.raises(ValueError, match="[Yy]etersiz"):
        hesapla(kontratlar, spot=765.96, risksiz_oran=0.03775,
                vade="2026-10-16", degerleme_tarihi="2026-09-08")


def test_determinizm_ayni_girdi_ayni_cikti():
    """audit K1: ayni girdi -> ayni ortalama/varyans (bit-birebir)."""
    kwargs = dict(spot=765.96, risksiz_oran=0.03775, vade="2026-10-16",
                  degerleme_tarihi="2026-09-08")
    s1 = hesapla(_ornek_kontratlar(), **kwargs)
    s2 = hesapla(_ornek_kontratlar(), **kwargs)
    assert s1["ortalama"] == s2["ortalama"]
    assert s1["varyans"] == s2["varyans"]
