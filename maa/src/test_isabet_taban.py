"""Taban orani VERIDEN yeniden hesaplanip belgelenen degere baglanir.

NEDEN BU TEST VAR (10.09.2026)
==============================
isabet_olcut.py'nin ilk surumunde taban orani "goreli %58,4" diye
yaziliyordu ve bu YANLISTI. Iki hata birlikte calisiyordu:

  1. YANLIS EVREN — taban, kararlarin gercekten verildigi semboller
     yerine genel bir buyuk-sirket listesiyle olculmustu.
  2. YANLIS PENCERE — seri market-data'nin /price ucundan alinmisti ve
     o uc VARSAYILAN 60 bar donuyor; 30 barlik ufukla bu, sembol basina
     30 TAMAMEN ORTUSEN pencere demekti.

Somut zarari: yanlis taban (0,584) verildiginde bir TUT sayimi "tabanin
ustunde" (BECERI) diye yargilaniyordu; dogru taban (0,730) verildiginde
ayni sayim "sanstan ayirt edilemedi" cikiyordu. Ayni veriden zit iki
yargi - ve yanlis olan, sistemin LEHINE olan yargiydi.

Belgeye yazilan bir sayi sessizce eskiyebilir. Bu test onu veriden
yeniden hesaplar; docstring ile veri ayrisirsa test kirilir.

Veri yoksa test ATLANMAZ, cunku atlanan test hicbir sey korumaz —
verinin varligi ayrica dogrulanir ve yoksa acikca basarisiz olur.
"""
import csv
from pathlib import Path

import pytest

from isabet_olcut import TUT_GORELI_ESIK, TUT_GORELI_TABAN

def _veri_dizini():
    """Veri dizinini bulur.

    Iki kosum bicimi var ve ikisinde de calismali:
      - dogrudan: depo agacindan (maa/src -> maa -> depo)
      - regresyon kosucusu: yalnizca maa/ /app'e baglanir, depo koku /repo'ya
    Sabit tek bir yol varsaymak, testin kosucuda SESSIZCE atlanmasina yol
    acardi - ve atlanan test hicbir sey korumaz.
    """
    adaylar = [
        Path(__file__).resolve().parents[2],   # depo agaci
        Path("/repo"),                          # regresyon kosucusu
    ]
    for k in adaylar:
        d = k / "qlib-service" / "csv_data_persistent" / "us_data"
        if d.is_dir():
            return d
    return adaylar[0] / "qlib-service" / "csv_data_persistent" / "us_data"


VERI = _veri_dizini()

# decision_log'da karar verilmis GERCEK semboller (10.09.2026 dokumu).
# Genel bir buyuk-sirket listesi DEGIL - ilk olcumdeki hata tam buydu.
KARAR_EVRENI = ["ASML", "CAT", "GOOGL", "JEPI", "LLY",
                "NVDA", "O", "SCHD", "TSM", "WDC"]
VEKIL = "SPY"
UFUK = 30
TOLERANS = 0.02          # +-2 puan


def _kapanis(sembol):
    p = VERI / f"{sembol}.csv"
    if not p.exists():
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                out.append((r["date"], float(r["close"])))
            except (KeyError, TypeError, ValueError):
                continue
    return out


def _taban(esik):
    vekil = dict(_kapanis(VEKIL))
    saglanan = toplam = 0
    for t in KARAR_EVRENI:
        k = _kapanis(t)
        for i in range(len(k) - UFUK):
            d0, c0 = k[i]
            d1, c1 = k[i + UFUK]
            if c0 <= 0 or d0 not in vekil or d1 not in vekil or vekil[d0] <= 0:
                continue
            r = (c1 - c0) / c0
            rp = (vekil[d1] - vekil[d0]) / vekil[d0]
            toplam += 1
            saglanan += abs(r - rp) < esik
    return (saglanan / toplam if toplam else None), toplam


def test_veri_MEVCUT():
    """Atlanan test hicbir sey korumaz; verinin varligi acikca sinanir."""
    assert VERI.is_dir(), f"veri dizini yok: {VERI}"
    eksik = [s for s in KARAR_EVRENI + [VEKIL] if not (VERI / f"{s}.csv").exists()]
    assert not eksik, f"karar evreninde eksik sembol: {eksik}"


def test_ornek_sayisi_yeterli():
    """Ilk olcumdeki hata kismen KUCUK ve ORTUSEN ornekten geliyordu."""
    _, n = _taban(TUT_GORELI_ESIK)
    assert n > 10000, f"ornek cok kucuk: {n} (ortusen pencere tuzagi)"


def test_BELGELENEN_taban_veriden_dogrulanir():
    """docstring'teki sayi ile gercek veri AYRISAMAZ."""
    olculen, n = _taban(TUT_GORELI_ESIK)
    assert olculen is not None
    assert abs(olculen - TUT_GORELI_TABAN) < TOLERANS, (
        f"belgelenen taban {TUT_GORELI_TABAN:.3f} ama veriden olculen "
        f"{olculen:.3f} (n={n}). isabet_olcut.py'deki deger eskimis olabilir.")


def test_secilen_esik_YAZI_TURA_civarinda():
    """Esigin secilme gerekcesi: taban ~%50 olmali.

    Cok yuksek bir taban (eski +-%15 mutlak bant gibi) olcutu bilgisiz
    kilar; cok dusuk bir taban ise TUT'u neredeyse her zaman yanlis
    gosterir. Ikisi de ayirt edici degildir.
    """
    olculen, _ = _taban(TUT_GORELI_ESIK)
    assert 0.40 <= olculen <= 0.60, (
        f"secilen esik {TUT_GORELI_ESIK:.0%} icin taban {olculen:.1%} — "
        f"ayirt edici bandin (%40-%60) disinda")


def test_ESKI_esik_gercekten_bilgisizdi():
    """Test anlamli olsun: degistirme gerekcesi veriden dogrulanmali."""
    eski_goreli, _ = _taban(0.10)
    assert eski_goreli > 0.65, (
        f"+-%10 goreli bandin tabani {eski_goreli:.1%}; degistirme gerekcesi "
        "veriyle desteklenmiyor")


@pytest.mark.parametrize("esik,en_az,en_cok", [
    (0.03, 0.25, 0.40), (0.05, 0.40, 0.55), (0.10, 0.65, 0.80)])
def test_kalibrasyon_egrisi_monoton_ve_beklenen_bantta(esik, en_az, en_cok):
    """Kalibrasyon egrisi kayarsa (veri degisirse) bu test haber verir."""
    olculen, _ = _taban(esik)
    assert en_az <= olculen <= en_cok, f"esik {esik}: taban {olculen:.3f}"
