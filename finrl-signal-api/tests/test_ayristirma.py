"""FinRL sinyal ayristirma testleri — madde 43.

Iki sey kilitlenir:
  1. Ayristirma basarisiz oldugunda BOS SINYAL DONULMEZ. Tuketici tarafta
     bunun bedeli olculdu: signal-ledger "isinstance(portfoy, dict)" diye
     bakiyor ve BOS SOZLUK bu kontrolu geciyor - yani bos portfoy gun boyu
     gecerli sinyal olarak onbellege alinirdi.
  2. Mesru bos portfoy (risk_off / tam nakit) ile ayristirma hatasi
     BIRBIRINDEN AYRILIR. Ayirt edici: mesru bos portfoy yine de rejim ve
     yuzde alanlarini tasir.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.main import _parse_deploy_output  # noqa: E402


GERCEK_CIKTI = """
=== FinRL-X Adaptive Rotation ===
Market Regime: risk_on
  MSFT : 16.67%
  META : 16.67%
  TSLA : 16.67%
  XOM  : 16.67%
  COP  : 16.67%
  FCX  : 16.67%
Total Invested: 100.0%
Cash Position: 0.0%
"""


def test_gercek_cikti_ayristirilir():
    p = _parse_deploy_output(GERCEK_CIKTI)
    assert p["market_regime"] == "risk_on"
    assert p["total_invested_pct"] == 100.0
    assert p["cash_position_pct"] == 0.0
    assert len(p["target_portfolio"]) == 6
    assert p["target_portfolio"]["MSFT"] == pytest.approx(16.67)


def test_ozet_satirlari_portfoye_KARISMAZ():
    """'Total Invested' ve 'Cash Position' hisse gibi gorunuyor."""
    p = _parse_deploy_output(GERCEK_CIKTI)
    assert "Total Invested" not in p["target_portfolio"]
    assert "Cash Position" not in p["target_portfolio"]


def test_risk_off_tam_nakit_MESRU():
    """Bos portfoy tek basina hata DEGILDIR - rejim ve yuzdeler varsa mesru."""
    cikti = """
Market Regime: risk_off
Total Invested: 0.0%
Cash Position: 100.0%
"""
    p = _parse_deploy_output(cikti)
    assert p["market_regime"] == "risk_off"
    assert p["cash_position_pct"] == 100.0
    assert p["target_portfolio"] == {}


def test_bicim_degisince_HIC_alan_eslesmez():
    """Ayristirma hatasinin imzasi: hicbir alan eslesmiyor."""
    p = _parse_deploy_output("BEKLENMEYEN BICIM\nrejim=riskli\nagirlik MSFT 0.16\n")
    assert p["market_regime"] is None
    assert p["total_invested_pct"] is None
    assert p["cash_position_pct"] is None
    assert p["target_portfolio"] == {}


def test_bos_cikti():
    p = _parse_deploy_output("")
    assert all(p[a] is None for a in ("market_regime", "total_invested_pct",
                                      "cash_position_pct"))
    assert p["target_portfolio"] == {}


def test_kismi_ayristirma_alanlari_None_birakir():
    """Rejim var ama yuzdeler yok: bu ayristirma hatasi DEGIL, eksik veri."""
    p = _parse_deploy_output("Market Regime: risk_on\n  MSFT : 50.0%\n")
    assert p["market_regime"] == "risk_on"
    assert p["total_invested_pct"] is None
    assert p["target_portfolio"] == {"MSFT": 50.0}


def test_ondalikli_yuzdeler():
    p = _parse_deploy_output("Market Regime: x\n  AAA : 33.333%\n  BBB : 0.5%\n")
    assert p["target_portfolio"] == {"AAA": 33.333, "BBB": 0.5}


# ------------------------------- uc noktanin hata sozlesmesi (dogrudan)
def _sinyal_yaniti(parsed):
    """main.py'deki hata kararinin AYNI kosulu — sozlesme testi."""
    return (parsed["market_regime"] is None
            and parsed["total_invested_pct"] is None
            and parsed["cash_position_pct"] is None
            and not parsed["target_portfolio"])


def test_hata_kosulu_yalnizca_TAM_basarisizlikta_tetiklenir():
    assert _sinyal_yaniti(_parse_deploy_output("cop")) is True
    assert _sinyal_yaniti(_parse_deploy_output(GERCEK_CIKTI)) is False
    # risk_off tam nakit: bos portfoy ama rejim var -> hata DEGIL
    riskoff = _parse_deploy_output(
        "Market Regime: risk_off\nTotal Invested: 0.0%\nCash Position: 100.0%\n")
    assert _sinyal_yaniti(riskoff) is False, (
        "mesru tam-nakit sinyali ayristirma hatasi sayildi")


def test_yalnizca_portfoy_eslesirse_hata_DEGIL():
    """Rejim satiri kaybolmus ama portfoy okunmus - eksik, ama cop degil."""
    p = _parse_deploy_output("  MSFT : 50.0%\n  AAPL : 50.0%\n")
    assert _sinyal_yaniti(p) is False
    assert p["target_portfolio"] == {"MSFT": 50.0, "AAPL": 50.0}


def test_olu_audit_dali_kaldirildi():
    """Kaldirilan dal geri gelmemeli: audit dizini host'ta hic olusmuyor.

    Denetim YORUMLARI DEGIL KODU tarar. Ilk yazimda ham metinde arama
    yapiyordu ve dalin neden kaldirildigini anlatan YORUMU yakaliyordu -
    yani aciklamayi silmeye zorluyordu. Aciklama degerli; silinmesi
    gereken kodun kendisiydi.
    """
    kaynak = (Path(__file__).resolve().parents[1] / "src" / "main.py").read_text()
    kod = "\n".join(s for s in kaynak.splitlines()
                    if not s.lstrip().startswith("#"))
    assert "AUDIT_DIR_TEMPLATE" not in kod
    assert "os.path.exists" not in kod, (
        "audit dosyasi dali geri konmus; o dal hicbir zaman calismiyor")
    assert "os.path.exists" in kaynak, (
        "dalin neden kaldirildigini anlatan aciklama da silinmis")


# ------------------------------- ozet etiketi filtresi (olu koruma duzeltmesi)
def test_tek_kelimelik_ozet_etiketi_portfoye_GIRMEZ():
    """OLCULEN HATA: eski filtre 'Total Invested'/'Cash Position' ariyordu
    ama regex cok kelimeli etiketi zaten yakalamiyordu. Tek kelimelik
    'Cash: 5.0%' ise yakalaniyor ve ELENMIYORDU."""
    p = _parse_deploy_output("Market Regime: x\n  MSFT : 50.0%\nCash: 5.0%\n")
    assert "Cash" not in p["target_portfolio"], "nakit satiri hisse sayildi"
    assert p["target_portfolio"] == {"MSFT": 50.0}


@pytest.mark.parametrize("etiket", ["Cash", "Total", "Invested", "Position",
                                    "Portfolio", "Regime", "cash", "TOTAL"])
def test_ozet_etiketleri_buyuk_kucuk_farketmeksizin_elenir(etiket):
    p = _parse_deploy_output(f"  {etiket} : 10.0%\n  MSFT : 90.0%\n")
    assert etiket not in p["target_portfolio"]
    assert p["target_portfolio"] == {"MSFT": 90.0}


@pytest.mark.parametrize("sembol", ["MSFT", "F", "GOOGL", "BRK.B", "BF-B"])
def test_gercek_semboller_gecer(sembol):
    p = _parse_deploy_output(f"  {sembol} : 25.0%\n")
    assert p["target_portfolio"] == {sembol: 25.0}


@pytest.mark.parametrize("cop", ["msft", "TOOLONGSYM", "12345", "MS_FT", "-"])
def test_sembole_benzemeyen_etiket_elenir(cop):
    p = _parse_deploy_output(f"  {cop} : 25.0%\n  AAPL : 75.0%\n")
    assert p["target_portfolio"] == {"AAPL": 75.0}, f"{cop!r} portfoye girdi"
