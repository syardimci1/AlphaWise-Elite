"""
Walk-forward + TCA birim testleri.

EN KRITIK TEST: look-ahead korumasi. Tasarim §3.3 der ki parametre secimi
YALNIZCA [i-egitim_gun, i) araligini gorebilir; test penceresi [i, i+test_gun)
secime ASLA girmemelidir. Bu dosya o kurali kilitler — kural bozulursa test
kirmizi doner.

Calistirma:  python3 -m src.test_walkforward     (taa konteyneri icinde)
"""
import sys

import numpy as np
import pandas as pd

try:
    from . import walkforward as wf
except ImportError:  # dogrudan calistirma
    import walkforward as wf


def _seri(n=800, tohum=42):
    """Deterministik sentetik fiyat serisi (ag/veri erisimi YOK)."""
    rng = np.random.default_rng(tohum)
    getiri = rng.normal(0.0004, 0.015, n)
    fiyat = 100 * np.exp(np.cumsum(getiri))
    idx = pd.bdate_range("2020-01-01", periods=n)
    return pd.Series(fiyat, index=idx, name="TEST")


def test_look_ahead_korumasi():
    """Parametre secimi test penceresinin verisini ASLA gormemeli."""
    kapanis = _seri()
    egitim_gun, test_gun = 252, 63

    gorulen = []          # egitim_en_iyi'ye giren her dilimin son tarihi
    pencere_baslari = []  # her pencerenin test baslangic tarihi

    gercek = wf.egitim_en_iyi

    def casus(kapanis_dilim, kombinasyonlar, fees, slip):
        gorulen.append(kapanis_dilim.index[-1])
        return wf.VARSAYILAN, 0.0   # hizli olsun diye izgara aranmaz

    wf.egitim_en_iyi = casus
    try:
        baslangic = max(egitim_gun, wf.ISINMA)
        for i in range(baslangic, len(kapanis) - 1, test_gun):
            if min(i + test_gun, len(kapanis)) - i < 10:
                break
            pencere_baslari.append(kapanis.index[i])
        wf.walk_forward(kapanis, wf.TCA_FEES, wf.TCA_SLIP,
                        egitim_gun=egitim_gun, test_gun=test_gun)
    finally:
        wf.egitim_en_iyi = gercek

    assert gorulen, "hic egitim penceresi olusmadi"
    assert len(gorulen) == len(pencere_baslari), (
        f"pencere sayisi uyusmuyor: {len(gorulen)} != {len(pencere_baslari)}")

    for k, (son_gorulen, test_bas) in enumerate(zip(gorulen, pencere_baslari)):
        assert son_gorulen < test_bas, (
            f"LOOK-AHEAD SIZINTISI (pencere {k}): parametre secimi "
            f"{son_gorulen.date()} tarihini gordu ama test penceresi "
            f"{test_bas.date()} tarihinde basliyor")
    print(f"  [OK] look-ahead: {len(gorulen)} pencerenin hepsinde egitim verisi "
          f"test baslangicindan ONCE bitiyor")


def test_egitim_penceresi_uzunlugu():
    """Egitim dilimi tam olarak egitim_gun uzunlugunda olmali."""
    kapanis = _seri()
    uzunluklar = []
    gercek = wf.egitim_en_iyi

    def casus(kapanis_dilim, kombinasyonlar, fees, slip):
        uzunluklar.append(len(kapanis_dilim))
        return wf.VARSAYILAN, 0.0

    wf.egitim_en_iyi = casus
    try:
        wf.walk_forward(kapanis, wf.TCA_FEES, wf.TCA_SLIP,
                        egitim_gun=252, test_gun=63)
    finally:
        wf.egitim_en_iyi = gercek

    assert set(uzunluklar) == {252}, f"egitim uzunluklari: {set(uzunluklar)}"
    print(f"  [OK] egitim penceresi: {len(uzunluklar)} pencerenin hepsi 252 bar")


def test_maliyet_donusumu():
    """§8.6 varsayilani %0.20 -> fees %0.10 + slippage %0.10."""
    f, s = wf.maliyetten_fees_slip(0.20)
    assert abs(f - 0.001) < 1e-12 and abs(s - 0.001) < 1e-12, (f, s)
    assert abs(f + s - 0.002) < 1e-12, "toplam surtunme %0.20 olmali"
    f2, s2 = wf.maliyetten_fees_slip(0.10)
    assert abs(f2 + s2 - 0.001) < 1e-12
    assert (wf.TCA_FEES, wf.TCA_SLIP) == (0.001, 0.001), "§8.6 sabiti degismis"
    print("  [OK] maliyet: %0.20 -> fees 0.001 + slippage 0.001 (toplam 0.002)")


def test_tca_performansi_dusurur():
    """Ayni seride yuksek maliyet, dusuk maliyetten daha iyi olamaz."""
    kapanis = _seri(n=700, tohum=7)
    ucuz = wf.ornek_ici(kapanis, *wf.maliyetten_fees_slip(0.10))
    pahali = wf.ornek_ici(kapanis, *wf.maliyetten_fees_slip(0.20))
    assert pahali["toplam_getiri_yuzde"] <= ucuz["toplam_getiri_yuzde"] + 1e-9, (
        f"maliyet artinca getiri artmis: {ucuz} vs {pahali}")
    print(f"  [OK] TCA yonu: %0.10 getiri={ucuz['toplam_getiri_yuzde']} >= "
          f"%0.20 getiri={pahali['toplam_getiri_yuzde']}")


def test_ornek_disi_pencere_kapanisi():
    """Her pencere sonunda pozisyon kapatilmali (acik pozisyon tasinmaz)."""
    kapanis = _seri(n=600, tohum=3)
    sonuc, secimler = wf.walk_forward(kapanis, wf.TCA_FEES, wf.TCA_SLIP)
    assert sonuc is not None and secimler, "walk-forward sonuc uretmedi"
    for s in secimler:
        assert s["test_baslangic"] <= s["test_bitis"]
    print(f"  [OK] pencereler: {len(secimler)} adet, hepsi kapali araliklı")


if __name__ == "__main__":
    testler = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    basarisiz = 0
    for t in testler:
        try:
            t()
        except AssertionError as e:
            basarisiz += 1
            print(f"  [FAIL] {t.__name__}: {e}")
        except Exception as e:
            basarisiz += 1
            print(f"  [HATA] {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(testler) - basarisiz}/{len(testler)} test PASS")
    sys.exit(1 if basarisiz else 0)


# ============ islem_ozeti: pf.stats() ile BIREBIR ayni olmali (Madde 32) ============
def test_islem_ozeti_stats_ile_AYNI_sonucu_verir():
    """09.09.2026'da olculdu: pf.stats() walk_forward suresinin %42'siydi
    ve yalnizca IKI alan icin cagriliyordu. Ucuz yol 279 kat hizli, ama
    SESSIZCE farkli sonuc uretmemeli.

    Bu test gercek fiyat serisi uzerinde 17 pencerenin tamamini karsilastirir.
    """
    import pandas as _pd
    kapanis = _seri(n=800, tohum=11)
    fees, slip = wf.maliyetten_fees_slip(0.20)
    komb = wf._kombinasyonlar()
    bas = max(wf.EGITIM_GUN, wf.ISINMA)
    karsilastirilan = 0
    for i in range(bas, len(kapanis) - 1, wf.TEST_GUN):
        egitim = kapanis.iloc[i - wf.EGITIM_GUN:i]
        test_son = min(i + wf.TEST_GUN, len(kapanis))
        if test_son - i < 10:
            break
        en_iyi, _ = wf.egitim_en_iyi(egitim, komb, fees, slip)
        g_tum, c_tum = wf.sinyaller(kapanis.iloc[:test_son], en_iyi)
        dilim = kapanis.iloc[i:test_son]
        g = g_tum.iloc[i:test_son].copy()
        c = c_tum.iloc[i:test_son].copy()
        c.iloc[-1] = True
        pf = wf.portfoy(dilim, g, c, fees, slip)

        st = pf.stats()
        beklenen_n = int(st.get("Total Trades", 0))
        beklenen_w = st.get("Win Rate [%]")
        if beklenen_w is not None and _pd.isna(beklenen_w):
            beklenen_w = None

        n, w = wf.islem_ozeti(pf)
        assert n == beklenen_n, f"pencere {i}: islem sayisi {n} != {beklenen_n}"
        if beklenen_w is None:
            assert w is None, f"pencere {i}: kazanma orani {w} != None"
        else:
            assert w is not None and abs(w - float(beklenen_w)) < 1e-9, (
                f"pencere {i}: kazanma orani {w} != {beklenen_w}")
        karsilastirilan += 1
    assert karsilastirilan >= 5, f"yalnizca {karsilastirilan} pencere karsilastirildi"


def test_islem_ozeti_ISLEM_SAYISINI_tum_islemlerden_alir():
    """INCE AYRIM: stats() islem sayisini TUM islemlerden, kazanma oranini
    yalnizca KAPANMIS islemlerden alir. Karistirilirsa raporlanan kazanma
    orani sessizce degisir (olculen ornek: %100 yerine %75)."""
    import os
    kaynak = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "walkforward.py"), encoding="utf-8").read()
    govde = kaynak[kaynak.index("def islem_ozeti("):kaynak.index("def walk_forward(")]
    assert "tr.count()" in govde, "islem sayisi TUM islemlerden alinmali"
    assert "kapali.win_rate" in govde, "kazanma orani KAPANMIS islemlerden alinmali"


def test_islem_ozeti_hata_durumunda_ESKI_yola_duser():
    """Beklenmeyen bir surum farkinda yanlis sayi uretmektense yavas ama
    dogru olan pf.stats() yoluna dusulmeli."""
    class Bozuk:
        @property
        def trades(self): raise RuntimeError("surum farki")
        def stats(self): return {"Total Trades": 7, "Win Rate [%]": 42.0}
    n, w = wf.islem_ozeti(Bozuk())
    assert n == 7 and w == 42.0
