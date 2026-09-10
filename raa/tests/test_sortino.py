"""
SORTINO ORANI TESTLERI (10.09.2026).

=======================================================================
NEDEN BU DOSYA VAR
=======================================================================
raa/src/main.py:276-279'daki Sortino hesabi iki hata tasiyordu ve ikisi de
uzun sure fark edilmedi cunku hesap `analyze()` govdesine GOMULUYDU -
dogrulamak icin FastAPI/redis/psycopg2/yfinance yiginini ayaga kaldirmak
gerekiyordu. Matematik ayri bir module tasindi ve bu testler onu, kapali
formdan ELLE hesaplanmis degerlere karsi sinar.

Bir duzeltmenin degeri, YENIDEN BOZULDUGUNDA kirilan bir testi varsa
kalicidir; bu yuzden asagida eski (hatali) formul de acikca yeniden
uretilir ve YENI sonucun ondan FARKLI oldugu dogrulanir.
"""
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from risk_metrikleri import (ISLEM_GUNU, asagi_yonlu_sapma,  # noqa: E402
                             sortino_orani)


def _eski_hatali_sortino(r, rf=0.04):
    """Duzeltmeden ONCEKI uygulama - yalnizca karsilastirma icin."""
    r = np.asarray(r, dtype=float)
    mra = float(np.mean(r) * 252)
    dn = r[r < 0]
    std = float(np.std(dn) * np.sqrt(252)) if len(dn) else 0.0
    return (mra - rf) / std if std > 0 else None


# ================================================== 1. AYNI MAR KULLANILIYOR
def test_pay_ve_payda_AYNI_esigi_kullanir():
    """Cekirdek hata buydu: pay MAR=%4, payda MAR=0 kullaniyordu.

    Kanit: risksiz orani degistirdigimizde PAYDA da degismeli. Eski kodda
    payda risksiz orandan tamamen BAGIMSIZDI.
    """
    r = np.array([0.01, -0.02, 0.005, -0.001, 0.003, -0.008] * 20)
    p0 = asagi_yonlu_sapma(r, risksiz_oran=0.0)
    p4 = asagi_yonlu_sapma(r, risksiz_oran=0.04)
    p20 = asagi_yonlu_sapma(r, risksiz_oran=0.20)
    assert p0 < p4 < p20, (
        f"payda risksiz orana duyarli olmali; {p0}, {p4}, {p20}")


def test_eski_payda_risksiz_orandan_BAGIMSIZDI_yeni_degil():
    r = np.array([0.01, -0.02, 0.005, -0.001] * 30)
    # eski: risksiz oran paydayi HIC etkilemiyordu
    dn = r[r < 0]
    eski_payda = float(np.std(dn) * np.sqrt(252))
    assert asagi_yonlu_sapma(r, 0.0) != pytest.approx(eski_payda), \
        "yeni payda eski formulle ayni cikiyorsa duzeltme uygulanmamis"


# ============================================ 2. KAPALI FORMDAN ELLE HESAP
def test_asagi_yonlu_sapma_ELLE_hesaplanan_degere_esit():
    """Dort gozlem, MAR=0 (risksiz oran 0) -> elle hesaplanabilir.

    eksikler = [0, -0.02, 0, -0.04]
    kare ortalama = (0 + 0.0004 + 0 + 0.0016) / 4 = 0.0005
    sqrt = 0.02236068...  -> yillik: * sqrt(252)
    """
    r = np.array([0.03, -0.02, 0.01, -0.04])
    beklenen = math.sqrt(0.0005) * math.sqrt(252)
    assert asagi_yonlu_sapma(r, risksiz_oran=0.0) == pytest.approx(beklenen, rel=1e-12)


def test_bolme_TUM_gozlemlere_yapilir_negatif_sayisina_DEGIL():
    """Eski kod yalnizca negatif gun sayisina boluyordu.

    Ayni iki negatif getiriye pozitif gunler EKLENDIGINDE asagi yonlu
    sapma DUSMELIDIR (risk seyreliyor). Eski formulde hic degismezdi.
    """
    az = np.array([-0.02, -0.02])
    cok = np.array([-0.02, -0.02] + [0.01] * 18)
    assert asagi_yonlu_sapma(cok, 0.0) < asagi_yonlu_sapma(az, 0.0)
    # eski formulde ikisi de AYNI cikardi (std([-0.02,-0.02]) = 0 her ikisinde)
    assert float(np.std(az[az < 0])) == float(np.std(cok[cok < 0]))


def test_sabit_negatif_seride_eski_formul_SACMA_deger_uretir():
    """En keskin ornek: her gun tam -%2. Asagi yonlu risk BUYUKTUR.

    OLCULDU (10.09.2026) - ilk beklentim yanlisti ve gercek daha kotu cikti:
    np.std([-0.02]*100) kayan noktada TAM sifir degildir (~1e-18). Yani eski
    formul "payda 0" diye guvenli sekilde None DONMEZ; o mikroskobik sayiya
    boler ve -9,2e16 mertebesinde bir deger uretir. Bu sayi rapora girer ve
    okuyan kisi icin tamamen anlamsizdir.

    Yeni formul ayni seride makul bir deger verir:
      pay   = -0,02*252 - 0,04 = -5,08
      payda = 0,0201587 * sqrt(252) = 0,32001
      ~ -15,87
    """
    r = np.array([-0.02] * 100)
    ham_std = float(np.std(r[r < 0]))
    assert 0 < ham_std < 1e-15, f"kayan nokta artigi bekleniyordu, cikan {ham_std}"

    eski = _eski_hatali_sortino(r)
    assert abs(eski) > 1e10, f"eski formul sacma buyuklukte deger uretmeliydi: {eski}"

    yeni = sortino_orani(r)
    assert asagi_yonlu_sapma(r, 0.0) == pytest.approx(0.02 * math.sqrt(252), rel=1e-12)
    assert yeni == pytest.approx(-15.87, abs=0.05), yeni
    assert abs(yeni) < 100, "yeni deger makul buyuklukte olmali"


# ================================================== 3. YON: ESKI ABARTIYORDU
def test_eski_formul_sortinoyu_ABARTIYORDU():
    """Gercek veride olculen yon: eski payda kucuk -> Sortino buyuk."""
    rng = np.random.default_rng(42)
    for _ in range(15):
        r = rng.normal(0.0005, 0.012, 260)
        eski, yeni = _eski_hatali_sortino(r), sortino_orani(r)
        if eski is None or yeni is None or eski <= 0:
            continue
        assert yeni <= eski + 1e-12, f"yeni deger eskisinden buyuk cikti: {yeni} > {eski}"


# ============================================================ 4. SINIR HALLERI
def test_hicbir_gun_esigin_altinda_degilse_TANIMSIZ():
    """Payda 0 -> buyuk bir sayi UYDURULMAZ, None doner."""
    r = np.array([0.01] * 50)
    assert asagi_yonlu_sapma(r, 0.0) == 0.0
    assert sortino_orani(r, 0.0) is None


def test_bos_seri_None():
    assert sortino_orani(np.array([])) is None
    assert asagi_yonlu_sapma(np.array([])) == 0.0


def test_liste_girdisi_de_kabul_edilir():
    assert sortino_orani([0.01, -0.02, 0.005, -0.001] * 30) is not None


def test_periyot_parametresi_etkili():
    r = np.array([0.01, -0.02, 0.005, -0.001] * 30)
    assert asagi_yonlu_sapma(r, 0.04, periyot=12) != asagi_yonlu_sapma(r, 0.04, periyot=252)


def test_yillik_carpani_252():
    assert ISLEM_GUNU == 252
