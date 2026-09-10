"""Karar isabeti testleri — madde 47.

Kilitlenen sozlesme: guven araligi taban orani iciyorsa oran "basarili"
diye raporlanamaz. Bu, sistemin kendini oldugundan iyi gostermesini
engelleyen tek mekanizma.
"""
import math

import pytest

from isabet import (ASGARI_ORNEK, isabet_degerlendir, taban_orani_olc,
                    wilson_araligi)


# ------------------------------------------------------ Wilson araligi
def test_wilson_bilinen_deger():
    """n=100, k=50 icin %95 Wilson araligi yaklasik [0.404, 0.596]."""
    alt, ust = wilson_araligi(50, 100)
    assert alt == pytest.approx(0.4038, abs=0.001)
    assert ust == pytest.approx(0.5962, abs=0.001)


def test_wilson_uc_oranlarda_SIFIR_GENISLIK_uretmez():
    """Normal yaklasim 0/5 ve 5/5'te sifir genislikte aralik verir ve yanilir."""
    for basari, toplam in ((0, 5), (5, 5), (0, 20), (20, 20)):
        alt, ust = wilson_araligi(basari, toplam)
        assert ust - alt > 0.05, f"{basari}/{toplam}: aralik cok dar"


def test_wilson_ornek_buyudukce_daralir():
    g = [wilson_araligi(n // 2, n) for n in (10, 100, 1000)]
    genislikler = [u - a for a, u in g]
    assert genislikler[0] > genislikler[1] > genislikler[2]


def test_wilson_sinirlarin_disina_tasmaz():
    for basari, toplam in ((0, 6), (6, 6), (1, 7)):
        alt, ust = wilson_araligi(basari, toplam)
        assert 0.0 <= alt <= ust <= 1.0


def test_wilson_gecersiz_girdi():
    with pytest.raises(ValueError):
        wilson_araligi(1, 0)
    with pytest.raises(ValueError):
        wilson_araligi(5, 3)
    with pytest.raises(ValueError):
        wilson_araligi(-1, 5)


# ------------------------------------------------ taban ile karsilastirma
def test_taban_araligin_icindeyse_SANSTAN_AYIRT_EDILEMEDI():
    """OLCULEN GERCEK DURUM: 4/7 EKLE dogru, taban %41,1."""
    r = isabet_degerlendir(4, 7, 0.411)
    assert r["olculdu"] is True
    assert r["yargi"] == "sanstan_ayirt_edilemedi"
    assert "AYIRT EDILEMEZ" in r["aciklama"]


def test_TUT_yuzde_yuz_bile_sanstan_ayirt_edilemez():
    """OLCULEN GERCEK DURUM: 5/5 TUT dogru ama olcut tabani %71,9.

    'TUT kararlarinin %100'u dogru' cumlesi tek basina hicbir sey soylemez.
    """
    r = isabet_degerlendir(5, 5, 0.719)
    assert r["yargi"] == "sanstan_ayirt_edilemedi", (
        f"5/5 basarili gosterildi: {r['aciklama']}")


def test_yeterince_buyuk_ornekte_ustunluk_gorulebilir():
    """Test anlamli olsun: gercek bir ustunluk YAKALANABILMELI."""
    r = isabet_degerlendir(90, 100, 0.411)
    assert r["yargi"] == "tabanin_ustunde"
    assert r["guven_araligi"][0] > 0.411


def test_tabanin_altinda_da_bildirilir():
    r = isabet_degerlendir(5, 100, 0.411)
    assert r["yargi"] == "tabanin_altinda"


def test_kucuk_ornek_ORAN_URETMEZ():
    """n < asgari: oran hesaplanmaz, None doner."""
    for n in range(0, ASGARI_ORNEK):
        r = isabet_degerlendir(max(0, n - 1), n, 0.5)
        assert r["olculdu"] is False
        assert r["oran"] is None and r["guven_araligi"] is None
        assert r["yargi"] == "olculemedi"


def test_asgari_ornekte_olculur():
    r = isabet_degerlendir(3, ASGARI_ORNEK, 0.5)
    assert r["olculdu"] is True


@pytest.mark.parametrize("taban", [-0.1, 1.1, 2.0])
def test_gecersiz_taban_olculemedi(taban):
    assert isabet_degerlendir(5, 10, taban)["olculdu"] is False


def test_gecersiz_sayimlar_olculemedi():
    assert isabet_degerlendir(11, 10, 0.5)["olculdu"] is False
    assert isabet_degerlendir(-1, 10, 0.5)["olculdu"] is False


# --------------------------------------------------------- taban olcumu
def test_taban_orani_bilinen_seride():
    """Duzenli artan seride r>0 olcutu her zaman saglanir."""
    k = {"A": [100 + i for i in range(40)]}
    r = taban_orani_olc(k, 30, lambda x: x > 0)
    assert r["olculdu"] is True and r["taban_orani"] == 1.0
    assert r["ornek"] == 10


def test_taban_orani_dusen_seride_sifir():
    k = {"A": [200 - i for i in range(40)]}
    r = taban_orani_olc(k, 30, lambda x: x > 0)
    assert r["taban_orani"] == 0.0, "gercek sifir bir OLCUMdur"
    assert r["olculdu"] is True


def test_kisa_seri_SIFIR_DEGIL_None():
    """Yeterli bar olmayan sembol 'tabani 0' saglamaz, OLCULEMEDI'dir."""
    r = taban_orani_olc({"A": [1, 2, 3]}, 30, lambda x: x > 0)
    assert r["olculdu"] is False
    assert r["sembol_bazinda"]["A"] is None
    assert r["taban_orani"] is None


def test_kisa_seri_digerlerini_bozmaz():
    k = {"KISA": [1, 2], "UZUN": [100 + i for i in range(40)]}
    r = taban_orani_olc(k, 30, lambda x: x > 0)
    assert r["olculdu"] is True and r["taban_orani"] == 1.0
    assert r["sembol_bazinda"]["KISA"] is None
    assert r["sembol_bazinda"]["UZUN"] == 1.0


def test_taban_donemin_genel_sabit_OLMADIGI_bildirilir():
    k = {"A": [100 + i for i in range(40)]}
    assert "genel bir piyasa sabiti DEGILDIR" in taban_orani_olc(k, 30, lambda x: x > 0)["aciklama"]


def test_sifir_fiyatli_bar_bolme_yapmaz():
    k = {"A": [0.0] + [100 + i for i in range(40)]}
    r = taban_orani_olc(k, 30, lambda x: x > 0)
    assert r["olculdu"] is True


def test_bos_girdi():
    r = taban_orani_olc({}, 30, lambda x: x > 0)
    assert r["olculdu"] is False and r["ornek"] == 0


def test_TUT_olcutu_gercek_tabani_yansitir():
    """Olculen gercek: TUT olcutu (|r|<0.15) tabani, r>0 tabanindan
    belirgin sekilde YUKSEK olmali."""
    import random
    rnd = random.Random(7)
    k = {f"S{i}": [100.0] for i in range(8)}
    for s in k:
        for _ in range(80):
            k[s].append(k[s][-1] * (1 + rnd.gauss(0.0005, 0.015)))
    tut = taban_orani_olc(k, 30, lambda r: abs(r) < 0.15)["taban_orani"]
    ekle = taban_orani_olc(k, 30, lambda r: r > 0)["taban_orani"]
    assert tut > ekle, f"TUT tabani ({tut}) EKLE tabanindan ({ekle}) yuksek degil"
    assert tut > 0.5, f"TUT olcutu beklendigi kadar musamahakar degil: {tut}"
