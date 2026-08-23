"""Formasyon modulu birim testleri — BILINEN formasyonlarla dogrulama.

Calistirma: python3 /app/src/test_formasyon.py  (taa konteynerinde)
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, "/app/src")
import formasyon as F


def _df(barlar):
    """barlar: (open, high, low, close) listesi -> TAA bicimi DataFrame."""
    idx = pd.bdate_range("2026-01-01", periods=len(barlar))
    return pd.DataFrame(barlar, columns=["Open", "High", "Low", "Close"], index=idx)


def _dolgu(n, taban=100.0):
    """Formasyon tetiklemeyen notr dolgu barlari (govde belirgin, golge kucuk)."""
    return [(taban, taban + 1.2, taban - 0.2, taban + 1.0) for _ in range(n)]


def test_doji():
    # acilis ~ kapanis, govde/aralik < 0.1
    barlar = _dolgu(25) + [(100.0, 102.0, 98.0, 100.05)]
    s = F.tespit_et(_df(barlar))
    assert bool(s["doji"].iloc[-1]), "doji tespit edilmedi"
    assert not bool(s["doji"].iloc[-2]), "dolgu bari yanlislikla doji sayildi"
    print("  [OK] doji: son bar True, onceki bar False")


def test_bogazlama_bullish():
    # onceki AYI (105->103), bugun BOGA (102->106): tam sarma
    barlar = _dolgu(25) + [(105.0, 105.5, 102.5, 103.0), (102.0, 106.5, 101.5, 106.0)]
    s = F.tespit_et(_df(barlar))
    assert bool(s["bullish_engulfing"].iloc[-1]), "bogazlama (boga) tespit edilmedi"
    assert not bool(s["bearish_engulfing"].iloc[-1]), "ayni barda ayi bogazlamasi da isaretlendi"
    print("  [OK] bullish_engulfing: True, bearish_engulfing: False")


def test_bogazlama_bearish():
    # onceki BOGA (102->106), bugun AYI (107->101)
    barlar = _dolgu(25) + [(102.0, 106.5, 101.5, 106.0), (107.0, 107.5, 100.5, 101.0)]
    s = F.tespit_et(_df(barlar))
    assert bool(s["bearish_engulfing"].iloc[-1]), "bogazlama (ayi) tespit edilmedi"
    assert not bool(s["bullish_engulfing"].iloc[-1]), "ayni barda boga bogazlamasi da isaretlendi"
    print("  [OK] bearish_engulfing: True, bullish_engulfing: False")


def test_cekic():
    # kucuk govde, uzun ALT golge, neredeyse yok ust golge
    barlar = _dolgu(25) + [(100.0, 100.3, 94.0, 100.1)]
    s = F.tespit_et(_df(barlar))
    assert bool(s["hammer"].iloc[-1]), "cekic tespit edilmedi"
    print("  [OK] hammer")


def test_tum_sutunlar_bool():
    """Kaynak koddaki hata: engulfing int donuyordu, digerleri bool."""
    s = F.tespit_et(_df(_dolgu(30)))
    for k in F.FORMASYONLAR:
        assert s[k].dtype == bool, f"{k} bool degil: {s[k].dtype}"
    print(f"  [OK] {len(F.FORMASYONLAR)} sutunun hepsi bool (kaynak kod hatasi giderildi)")


def test_yon_siniflandirmasi_calisiyor():
    """Kaynak koddaki hata: ada gore 'bullish' arayinca hep 0 cikiyordu."""
    boga = [k for k, v in F.YON_SINIFI.items() if v == "boga"]
    ayi = [k for k, v in F.YON_SINIFI.items() if v == "ayi"]
    assert len(boga) >= 5 and len(ayi) >= 5, (len(boga), len(ayi))
    assert set(F.YON_SINIFI) == set(F.FORMASYONLAR)
    barlar = _dolgu(25) + [(105.0, 105.5, 102.5, 103.0), (102.0, 106.5, 101.5, 106.0)]
    o = F.son_bar_ozeti(_df(barlar), gun=5)
    assert o["boga_formasyonu_sayisi"] >= 1, o
    print(f"  [OK] yon siniflandirmasi: {len(boga)} boga / {len(ayi)} ayi, "
          f"ozet boga sayisi={o['boga_formasyonu_sayisi']}")


def test_look_ahead_yok():
    """Bir barin tespiti, KENDINDEN SONRAKI barlar degisince degismemeli."""
    barlar = _dolgu(30) + [(105.0, 105.5, 102.5, 103.0), (102.0, 106.5, 101.5, 106.0)]
    tam = F.tespit_et(_df(barlar))
    kisa = F.tespit_et(_df(barlar[:-1]))
    ortak = kisa.index
    fark = (tam.loc[ortak] != kisa).sum().sum()
    assert fark == 0, f"gelecek bar eklenince gecmis tespitler degisti: {fark} hucre"
    print("  [OK] look-ahead yok: sonraki bar eklenince gecmis tespitler degismiyor")


def test_kalibrasyon_uyarisi_var():
    o = F.son_bar_ozeti(_df(_dolgu(30)))
    assert o["kalibrasyon_gecerli"] is False
    assert "KALIBRE EDILMEMISTIR" in o["not"]
    print("  [OK] kalibrasyon uyarisi ciktida var")


if __name__ == "__main__":
    testler = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    hata = 0
    for t in testler:
        try:
            t()
        except AssertionError as e:
            hata += 1; print(f"  [FAIL] {t.__name__}: {e}")
        except Exception as e:
            hata += 1; print(f"  [HATA] {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(testler)-hata}/{len(testler)} test PASS")
    sys.exit(1 if hata else 0)
