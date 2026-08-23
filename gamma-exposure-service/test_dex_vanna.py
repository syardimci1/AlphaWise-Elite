"""DEX/Vanna matematiginin birim testleri.

En guclu testler SAYISAL TUREV testleridir: vanna GERCEKTEN d(delta)/d(sigma)
mi, gamma GERCEKTEN d(delta)/d(S) mi — analitik formul yanlissa burada patlar.
"""
import math
import sys

sys.path.insert(0, "/app")
import dex_vanna as dv


def _yakin(a, b, tol=1e-6, ad=""):
    assert abs(a - b) < tol, f"{ad}: {a} != {b} (fark {abs(a-b):.3e}, tol {tol})"


def test_put_call_paritesi_delta():
    """delta_call - delta_put = e^{-qT}  (BS ozdesligi)"""
    for q in (0.0, 0.02):
        for S, K, T, s in ((100, 100, 0.5, 0.25), (309.69, 300, 0.1, 0.3),
                           (50, 80, 1.0, 0.6)):
            c = dv.yunanlar(S, K, T, s, "call", q=q)
            p = dv.yunanlar(S, K, T, s, "put", q=q)
            _yakin(c["delta"] - p["delta"], math.exp(-q * T), 1e-10,
                   f"parite q={q} S={S} K={K}")
    print("  [OK] put-call paritesi: delta_call - delta_put = e^(-qT)")


def test_gamma_ve_vanna_call_put_ayni():
    """Ayni strike/vadede gamma ve vanna call ile put icin AYNIDIR."""
    for S, K, T, s in ((100, 110, 0.25, 0.3), (309.69, 250, 0.75, 0.45)):
        c = dv.yunanlar(S, K, T, s, "call")
        p = dv.yunanlar(S, K, T, s, "put")
        _yakin(c["gamma"], p["gamma"], 1e-12, "gamma call/put")
        _yakin(c["vanna"], p["vanna"], 1e-12, "vanna call/put")
    print("  [OK] gamma ve vanna call/put icin ozdes")


def test_vanna_sayisal_turev():
    """vanna == d(delta)/d(sigma) — SAYISAL dogrulama."""
    h = 1e-5
    en_kotu = 0.0
    for S, K, T, s, tip in ((100, 100, 0.5, 0.25, "call"),
                            (100, 120, 0.25, 0.40, "call"),
                            (100, 80, 1.0, 0.30, "put"),
                            (309.69, 300, 0.1, 0.35, "put")):
        analitik = dv.yunanlar(S, K, T, s, tip)["vanna"]
        d_arti = dv.yunanlar(S, K, T, s + h, tip)["delta"]
        d_eksi = dv.yunanlar(S, K, T, s - h, tip)["delta"]
        sayisal = (d_arti - d_eksi) / (2 * h)
        bagil = abs(analitik - sayisal) / max(abs(sayisal), 1e-9)
        en_kotu = max(en_kotu, bagil)
        assert bagil < 1e-4, (f"vanna S={S} K={K} tip={tip}: "
                              f"analitik={analitik:.8f} sayisal={sayisal:.8f} "
                              f"bagil_hata={bagil:.2e}")
    print(f"  [OK] vanna = d(delta)/d(sigma) — 4 senaryo, en kotu bagil hata {en_kotu:.2e}")


def test_gamma_sayisal_turev():
    """gamma == d(delta)/d(S) — SAYISAL dogrulama."""
    h = 1e-4
    en_kotu = 0.0
    for S, K, T, s, tip in ((100, 100, 0.5, 0.25, "call"),
                            (100, 90, 0.25, 0.40, "put"),
                            (309.69, 320, 0.2, 0.30, "call")):
        analitik = dv.yunanlar(S, K, T, s, tip)["gamma"]
        sayisal = (dv.yunanlar(S + h, K, T, s, tip)["delta"] -
                   dv.yunanlar(S - h, K, T, s, tip)["delta"]) / (2 * h)
        bagil = abs(analitik - sayisal) / max(abs(sayisal), 1e-9)
        en_kotu = max(en_kotu, bagil)
        assert bagil < 1e-4, (f"gamma S={S} K={K}: analitik={analitik:.8f} "
                              f"sayisal={sayisal:.8f} hata={bagil:.2e}")
    print(f"  [OK] gamma = d(delta)/d(S) — 3 senaryo, en kotu bagil hata {en_kotu:.2e}")


def test_delta_sinir_degerleri():
    """Cok ITM call delta -> 1, cok OTM call delta -> 0, ATM ~ 0.5."""
    itm = dv.yunanlar(100, 1, 0.5, 0.2, "call")["delta"]
    otm = dv.yunanlar(100, 10000, 0.5, 0.2, "call")["delta"]
    atm = dv.yunanlar(100, 100, 0.01, 0.2, "call")["delta"]
    assert itm > 0.999, f"derin ITM delta={itm}"
    assert otm < 0.001, f"derin OTM delta={otm}"
    assert 0.45 < atm < 0.55, f"ATM delta={atm}"
    print(f"  [OK] sinir degerleri: ITM={itm:.6f} OTM={otm:.2e} ATM={atm:.4f}")


def test_bilinen_referans_degeri():
    """Ders kitabi ornegi (Hull): S=49, K=50, r=0.05, s=0.20, T=20/52.
    Beklenen call delta ~ 0.522."""
    g = dv.yunanlar(49, 50, 20 / 52, 0.20, "call", r=0.05, q=0.0)
    assert 0.515 < g["delta"] < 0.530, f"Hull ornegi delta={g['delta']}"
    print(f"  [OK] bilinen referans (Hull S=49,K=50,r=5%,s=20%,T=20/52): "
          f"delta={g['delta']:.4f} (beklenen ~0.522)")


def test_gecersiz_girdi_reddediliyor():
    assert dv.yunanlar(0, 100, 0.5, 0.2, "call") is None
    assert dv.yunanlar(100, 0, 0.5, 0.2, "call") is None
    assert dv.yunanlar(100, 100, 0.0, 0.2, "call") is None      # vade dolmus
    assert dv.yunanlar(100, 100, 0.5, 0.0, "call") is None      # IV=0
    assert dv.yunanlar(100, 100, 0.5, 99.0, "call") is None     # IV absurt
    print("  [OK] gecersiz girdiler (S=0, K=0, T=0, IV=0, IV=99) reddedildi")


def test_toplama_isaret_sozlesmesi():
    """Bayi varsayimi: call KISA (-), put UZUN (+). Ham degerler isaretsiz."""
    kontratlar = [
        {"strike": 100, "expiration": "2027-08-23", "option_type": "call",
         "open_interest": 10, "implied_volatility": 0.3},
        {"strike": 100, "expiration": "2027-08-23", "option_type": "put",
         "open_interest": 10, "implied_volatility": 0.3},
    ]
    from datetime import date
    r = dv.maruziyet_hesapla(kontratlar, spot=100.0, bugun=date(2026, 8, 23))
    assert r["kullanilan_kontrat"] == 2, r
    # gamma call == gamma put oldugu icin bayi GEX'i sifirlanmali
    assert abs(r["bayi_varsayimli"]["gex"]) < 1e-6, r["bayi_varsayimli"]
    # ham GEX ise iki katina cikmali (ikisi de pozitif)
    assert r["ham"]["gex"] > 0, r["ham"]
    assert r["call_dex"] > 0 and r["put_dex"] < 0, (r["call_dex"], r["put_dex"])
    print(f"  [OK] isaret sozlesmesi: bayi GEX={r['bayi_varsayimli']['gex']} "
          f"(esit call+put -> 0), ham GEX={r['ham']['gex']:.0f}")


def test_kalibrasyon_uyarisi():
    from datetime import date
    r = dv.maruziyet_hesapla(
        [{"strike": 100, "expiration": "2027-08-23", "option_type": "call",
          "open_interest": 1, "implied_volatility": 0.3}],
        spot=100.0, bugun=date(2026, 8, 23))
    assert r["kalibrasyon_gecerli"] is False
    assert r["yon_kodu_uretir"] is False
    assert "KALIBRE EDILMEMISTIR" in r["not"]
    print("  [OK] kalibrasyon uyarisi ve yon_kodu_uretir=False ciktida var")


# ===== CEKISMELI INCELEME BULGULARININ REGRESYON TESTLERI (23.08.2026) =====

def test_bozuk_vade_tum_istegi_cokertmiyor():
    """BULGU: _yil_kesri try blogunun DISINDAYDI; bozuk expiration tum
    hesabi cokertiyordu."""
    from datetime import date
    kotu = [
        {"strike": 100, "option_type": "call", "open_interest": 10,
         "implied_volatility": 0.3},                       # expiration YOK
        {"strike": 100, "expiration": None, "option_type": "call",
         "open_interest": 10, "implied_volatility": 0.3},
        {"strike": 100, "expiration": "", "option_type": "call",
         "open_interest": 10, "implied_volatility": 0.3},
        {"strike": 100, "expiration": 1790000000, "option_type": "call",
         "open_interest": 10, "implied_volatility": 0.3},  # epoch
        {"strike": 100, "expiration": "31/12/2026", "option_type": "call",
         "open_interest": 10, "implied_volatility": 0.3},  # ISO degil
        {"strike": 100, "expiration": "2027-08-23", "option_type": "call",
         "open_interest": 10, "implied_volatility": 0.3},  # SAGLIKLI
    ]
    r = dv.maruziyet_hesapla(kotu, spot=100.0, bugun=date(2026, 8, 23))
    assert r["kullanilan_kontrat"] == 1, r
    assert r["atlanan_kontrat"] == 5, r
    assert r["ham"]["gex"] > 0, r
    print(f"  [OK] bozuk vade: 5 kontrat atlandi, saglikli 1 tanesi islendi "
          f"(cokme YOK) — nedenler={r['atlanma_nedeni']}")


def test_nan_acik_pozisyon_toplamlari_bozmuyor():
    """BULGU: NaN OI `oi <= 0` kontrolunu geciyor, tum toplamlar NaN oluyordu."""
    from datetime import date
    import math
    k = [
        {"strike": 100, "expiration": "2027-08-23", "option_type": "call",
         "open_interest": 10, "implied_volatility": 0.3},
        {"strike": 105, "expiration": "2027-08-23", "option_type": "put",
         "open_interest": float("nan"), "implied_volatility": 0.3},
    ]
    r = dv.maruziyet_hesapla(k, spot=100.0, bugun=date(2026, 8, 23))
    assert r["kullanilan_kontrat"] == 1, r
    assert r["atlanan_kontrat"] == 1, r
    for grup in ("ham", "bayi_varsayimli"):
        for ad, v in r[grup].items():
            assert not math.isnan(v), f"{grup}.{ad} NaN: {r[grup]}"
    assert not math.isnan(r["toplam_acik_pozisyon"])
    print("  [OK] NaN open_interest elendi, hicbir toplam NaN degil")


def test_0dte_kontratlar_dusmuyor():
    """BULGU: vadesi BUGUN olan (0DTE) kontratlar T=0 alip sessizce
    atiliyordu — gamma'nin en buyuk oldugu vade."""
    from datetime import date
    k = [{"strike": 100, "expiration": "2026-08-23", "option_type": "call",
          "open_interest": 100, "implied_volatility": 0.3}]
    r = dv.maruziyet_hesapla(k, spot=100.0, bugun=date(2026, 8, 23))
    assert r["kullanilan_kontrat"] == 1, f"0DTE hala dusuyor: {r}"
    assert r["ham"]["gex"] > 0, r
    T = dv._yil_kesri("2026-08-23", bugun=date(2026, 8, 23))
    assert T > 0, f"0DTE icin T={T}"
    print(f"  [OK] 0DTE islendi: T={T:.6f} yil ({T*365*24:.1f} saat), "
          f"ham GEX={r['ham']['gex']:.0f}")


def test_isaret_sozlesmesi_kamu_standardi():
    """BULGU: isaret TERSTI. Standart: GEX = call gamma - put gamma."""
    from datetime import date
    tek_call = [{"strike": 100, "expiration": "2027-08-23", "option_type": "call",
                 "open_interest": 10, "implied_volatility": 0.3}]
    tek_put = [{"strike": 100, "expiration": "2027-08-23", "option_type": "put",
                "open_interest": 10, "implied_volatility": 0.3}]
    c = dv.maruziyet_hesapla(tek_call, 100.0, bugun=date(2026, 8, 23))
    p_ = dv.maruziyet_hesapla(tek_put, 100.0, bugun=date(2026, 8, 23))
    assert c["bayi_varsayimli"]["gex"] > 0, f"call GEX pozitif olmali: {c['bayi_varsayimli']}"
    assert p_["bayi_varsayimli"]["gex"] < 0, f"put GEX negatif olmali: {p_['bayi_varsayimli']}"
    assert "UZUN" in c["varsayimlar"]["bayi_konumu"]
    print(f"  [OK] kamu sozlesmesi: call GEX={c['bayi_varsayimli']['gex']:.0f} (+), "
          f"put GEX={p_['bayi_varsayimli']['gex']:.0f} (-)")


def test_ham_gamma_yogunlasmasi_ayrica_donuyor():
    """BULGU: en_buyuk_gex_strike bayi-isaretli oldugu icin ayni strike'taki
    call+put birbirini goturuyor, gercek gamma duvari '0' gorunuyordu."""
    from datetime import date
    k = [
        {"strike": 100, "expiration": "2027-08-23", "option_type": "call",
         "open_interest": 1000, "implied_volatility": 0.3},
        {"strike": 100, "expiration": "2027-08-23", "option_type": "put",
         "open_interest": 1000, "implied_volatility": 0.3},
        {"strike": 120, "expiration": "2027-08-23", "option_type": "call",
         "open_interest": 300, "implied_volatility": 0.3},
    ]
    r = dv.maruziyet_hesapla(k, 100.0, bugun=date(2026, 8, 23))
    bayi = {x["strike"]: x["gex"] for x in r["en_buyuk_gex_strike_bayi_isaretli"]}
    ham = {x["strike"]: x["gex"] for x in r["en_buyuk_gamma_yogunlasmasi_ham"]}
    assert abs(bayi.get(100.0, 0)) < 1e-6, f"bayi 100 strike sifirlanmali: {bayi}"
    assert ham[100.0] > ham.get(120.0, 0), f"ham listede 100 strike ONDE olmali: {ham}"
    print(f"  [OK] ham yogunlasma gercek duvari gosteriyor: "
          f"100->{ham[100.0]:.0f}, 120->{ham.get(120.0,0):.0f} "
          f"(bayi-isaretli listede 100 -> {bayi.get(100.0,0):.0f})")


def test_veri_yetersiz_bayragi():
    """BULGU: tum kontratlar elenince gex=0.0 donuyordu ve 'gamma yok' ile
    'veri yok' ayirt edilemiyordu (ustelik 15 dk onbellege yaziliyordu)."""
    from datetime import date
    # IV yuzde bicimde gelirse (saglayici bicim degistirirse) hepsi elenir
    k = [{"strike": 100, "expiration": "2027-08-23", "option_type": "call",
          "open_interest": 10, "implied_volatility": 25.0}]
    r = dv.maruziyet_hesapla(k, 100.0, bugun=date(2026, 8, 23))
    assert r["veri_yetersiz"] is True, r
    assert r["kullanilan_kontrat"] == 0
    assert r["atlanma_orani_yuzde"] == 100.0
    print(f"  [OK] veri_yetersiz=True, atlanma_orani=%{r['atlanma_orani_yuzde']}, "
          f"neden={r['atlanma_nedeni']}")


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
