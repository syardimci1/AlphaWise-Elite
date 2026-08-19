"""Birim testleri: factor engine."""
import math
import sys
sys.path.insert(0, "/opt/alphawise/commercial/AlphaWise-Elite/liquidity-signal-service")

from src import factors


def test_net_likidite_temel():
    # WALCL - TGA - RRP*1000 (milyon)
    walcl = [7_000_000]  # 7M USD
    tga = [500_000]      # 500K USD
    rrp = [1_000]        # 1000 milyar = 1M milyon
    r = factors.net_likidite(walcl, tga, rrp)
    assert r[0] == 7_000_000 - 500_000 - 1_000 * 1000
    assert r[0] == 5_500_000


def test_net_likidite_eksik_veri_none_doner():
    r = factors.net_likidite([100.0, None], [50.0, 50.0], [1.0, 1.0])
    assert r[0] is not None
    assert r[1] is None


def test_zscore_sabit_seri_none():
    # Sabit seri -> std 0 -> None
    r = factors.zscore([100.0] * 20)
    assert all(v is None for v in r)


def test_zscore_bilinen_deger():
    # 5 gozlem: [1,2,3,4,5], son deger 5, mean=3, std=sqrt(sum((x-3)^2)/(n-1))
    r = factors.zscore([1.0, 2.0, 3.0, 4.0, 5.0])
    # Son degerin z-skoru pozitif olmali ve makul buyuklukte
    assert r[-1] is not None
    assert r[-1] > 0
    # Ilk deger: sadece 1 gozlem — < 5, None
    assert r[0] is None


def test_yoy_pct_252_donem():
    # 253 elemanlik seri: 253 sonra %10 buyuse
    seri = [100.0] * 252 + [110.0]
    r = factors.yoy_pct(seri)
    assert r[-1] is not None
    assert abs(r[-1] - 10.0) < 1e-9


def test_yoy_yetersiz_donem_none():
    r = factors.yoy_pct([100.0, 110.0, 120.0])
    assert r[-1] is None  # 252 gun yok


def test_momentum_20g():
    seri = [100.0] * 20 + [105.0]
    r = factors.momentum(seri)
    assert r[-1] is not None
    assert abs(r[-1] - 5.0) < 1e-9


def test_rejim_belirsiz_kisa_seride():
    seri = [100.0] * 10
    mom = [None] * 10
    assert factors.rejim(5, seri, mom) == "belirsiz"


def test_rejim_genisleme_hizlaniyor():
    # Uzun surekli artan seri: short_ma > long_ma, momentum degisimi > 0
    seri = [100.0 + i * 2 for i in range(100)]
    mom = factors.momentum(seri)
    r = factors.rejim(len(seri) - 1, seri, mom)
    # Ilerideki degere gore artan momentum: expansion accelerating veya decelerating
    assert r.startswith("genisleme_") or r == "belirsiz"


def test_composite_skor_belirsiz_rejim_notr():
    """Belirsiz rejim + None faktorler -> skor ~0."""
    s = factors.composite_skor("belirsiz", None, None, None, None)
    assert s == 0.0


def test_composite_skor_maksimum_pozitif():
    """genisleme_hizlaniyor + scissors z=2.5 -> rejim sig=2. deviation=-2 -> t_sig=2.
    liq_mom>0 & > ast_mom -> m_sig=1. Skor: 0.5*2 + 0.3*2 + 0.2*1 = 1.8"""
    s = factors.composite_skor("genisleme_hizlaniyor", 2.5, -2.0, 3.0, 1.0)
    assert abs(s - 1.8) < 1e-9


def test_composite_skor_maksimum_negatif():
    s = factors.composite_skor("daralma_hizlaniyor", -2.5, 2.0, -3.0, -1.0)
    # rejim=-2, threshold=-2, momentum=-1
    assert abs(s - (0.5 * -2 + 0.3 * -2 + 0.2 * -1)) < 1e-9
    assert abs(s - (-1.8)) < 1e-9


def test_scissors_deviation_basit():
    assert factors.scissors([10.0], [3.0]) == [7.0]
    assert factors.deviation([1.5], [0.5]) == [1.0]


def test_ffill_temel():
    gunler = ["2026-01-01", "2026-01-02", "2026-01-03"]
    seri = {"2026-01-01": 100.0, "2026-01-03": 200.0}
    r = factors.ffill(gunler, seri)
    assert r == [100.0, 100.0, 200.0]


def test_gunluk_esik_haftaici_sadece():
    r = factors.gunluk_esik("2026-08-14", "2026-08-17")  # Cuma-Pzt
    assert r == ["2026-08-14", "2026-08-17"]  # Cts/Paz atlar


if __name__ == "__main__":
    import subprocess
    subprocess.run(["python3", "-m", "pytest", __file__, "-v"], check=True)
