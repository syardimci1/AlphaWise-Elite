"""IZOLE BIRIM TESTI — zincir_istatistik.py (24.08.2026).

Ag erisimi YOK: openbb-service cagrilmaz, sahte zincir sozlukleri kullanilir.
test_dex_vanna.py'nin uslubunu izler: her test [OK] satiri basar, sonda
PASS sayisi yazilir ve basarisizlikta exit 1 doner.
"""
import re
import sys

import zincir_istatistik as zi


def test_temel_oranlar():
    zincir = [
        {"option_type": "call", "volume": 100, "open_interest": 200},
        {"option_type": "call", "volume": 50, "open_interest": 100},
        {"option_type": "put", "volume": 75, "open_interest": 150},
    ]
    s = zi.zincir_istatistikleri(zincir)
    assert s["call"]["hacim"] == 150.0, s["call"]
    assert s["put"]["hacim"] == 75.0, s["put"]
    assert s["put_call_hacim_orani"] == 0.5, s["put_call_hacim_orani"]
    assert s["put_call_acik_pozisyon_orani"] == 0.5, s
    assert s["toplam_hacim"] == 225.0 and s["toplam_acik_pozisyon"] == 450.0, s
    assert s["hacim_acik_pozisyon_orani"] == 0.5, s
    print("  [OK] put/call hacim ve acik pozisyon oranlari dogru")


def test_sifir_payda_none_doner():
    """Call yoksa oran UYDURULMAZ (0 veya sonsuz degil) — None doner."""
    s = zi.zincir_istatistikleri(
        [{"option_type": "put", "volume": 10, "open_interest": 20}])
    assert s["put_call_hacim_orani"] is None, s["put_call_hacim_orani"]
    assert s["put_call_acik_pozisyon_orani"] is None, s
    bos = zi.zincir_istatistikleri([])
    assert bos["hacim_acik_pozisyon_orani"] is None, bos
    assert bos["toplam_hacim"] == 0.0, bos
    print("  [OK] sifir paydali oranlar None (0/sonsuz uydurulmuyor)")


def test_nan_alanlar_toplami_bozmaz():
    """NaN, `> 0` kontrolunu gecip toplami NaN'a cevirmemeli."""
    nan = float("nan")
    zincir = [
        {"option_type": "call", "volume": nan, "open_interest": 100},
        {"option_type": "call", "volume": 40, "open_interest": nan},
        {"option_type": "put", "volume": 10, "open_interest": 10},
    ]
    s = zi.zincir_istatistikleri(zincir)
    assert s["call"]["hacim"] == 40.0, s["call"]
    assert s["call"]["acik_pozisyon"] == 100.0, s["call"]
    assert s["kapsam"]["hacim_alani_eksik"] == 1, s["kapsam"]
    assert s["kapsam"]["acik_pozisyon_alani_eksik"] == 1, s["kapsam"]
    # toplamlarin hicbiri NaN olmamali
    for alan in ("toplam_hacim", "toplam_acik_pozisyon"):
        assert s[alan] == s[alan], f"{alan} NaN oldu"
    print("  [OK] NaN alanlar elenir, toplamlar NaN'a donmez")


def test_gecersiz_tip_ayri_sayilir():
    zincir = [
        {"option_type": "call", "volume": 1, "open_interest": 1},
        {"option_type": "", "volume": 999, "open_interest": 999},
        {"option_type": "straddle", "volume": 999, "open_interest": 999},
        {"volume": 999, "open_interest": 999},
    ]
    s = zi.zincir_istatistikleri(zincir)
    assert s["kapsam"]["gecersiz_tip"] == 3, s["kapsam"]
    assert s["kapsam"]["degerlendirilen_kontrat"] == 1, s["kapsam"]
    assert s["toplam_hacim"] == 1.0, s
    print("  [OK] gecersiz tipler sessizce toplama karismiyor (3/3 ayri sayildi)")


def test_acik_pozisyonsuz_hacimli_kontrat_sayilir():
    """OI=0 & hacim>0 kontratlar elenmez, ayrica sayilir."""
    zincir = [
        {"option_type": "call", "volume": 500, "open_interest": 0},
        {"option_type": "put", "volume": 300, "open_interest": 0},
        {"option_type": "call", "volume": 0, "open_interest": 0},
        {"option_type": "call", "volume": 10, "open_interest": 5},
    ]
    s = zi.zincir_istatistikleri(zincir)
    assert s["acik_pozisyonsuz_hacimli_kontrat"] == 2, s
    # hacimleri toplama DAHIL edilmis olmali (elenmemis)
    assert s["call"]["hacim"] == 510.0, s["call"]
    assert s["put"]["hacim"] == 300.0, s["put"]
    print("  [OK] OI=0 hacimli kontratlar elenmiyor, ayrica sayiliyor (2 adet)")


# Kelime SINIRLI desenler. Ilk yazimda duz alt dizgi araniyordu ve
# "olgusal sayimdir" ifadesindeki "al " yanlislikla emir kipi sanilmisti;
# Turkce'de "al/sat" hemen her kelimenin icinde gecebildigi icin alt dizgi
# aramasi bu is icin YANLIS aractir. Desenler, sistemde bu isi zaten dogru
# yapan insider-trading-service/src/lambda_sifir.py:39-54 ile ayni
# disiplinde (kelime sinirli, olgusal isim halleri serbest) yazildi.
YASAK_IFADELER = [
    (re.compile(r"\b(EKLE|TUT|BEKLE)\b"), "MAA karar kodu"),
    (re.compile(r"\bD[İI]KKAT\s+ET\b", re.I), "MAA karar kodu"),
    (re.compile(r"\bal[ıi]n(?:[ıi]z)?\b", re.I), "emir kipi (alin/aliniz)"),
    (re.compile(r"\bsat[ıi]n\s+al", re.I), "emir kipi (satin al)"),
    (re.compile(r"\by[üu]kselecek\b", re.I), "kesin gelecek iddiasi"),
    (re.compile(r"\bd[üu][şs]ecek\b", re.I), "kesin gelecek iddiasi"),
    (re.compile(r"\byukar[ıi]\s+gidecek\b", re.I), "kesin gelecek iddiasi"),
    (re.compile(r"\bgaranti\b", re.I), "kesinlik ifadesi"),
    (re.compile(r"\bkesinlikle\b", re.I), "kesinlik ifadesi"),
    (re.compile(r"\bmutlaka\b", re.I), "kesinlik ifadesi"),
    # Sondaki \b BILEREK yok: Turkce ek aldiginda ("tavsiyesi", "tavsiyeler")
    # kelime siniri kelimenin sonunda olusmaz ve desen kacirirdi. Bunu
    # asagidaki negatif kontrol testi yakaladi.
    (re.compile(r"\btavsiye", re.I), "yatirim tavsiyesi"),
]


def test_yon_iddiasi_ve_kalibrasyon_disiplini():
    """Cikti hicbir yon/emir ifadesi tasimamali, kalibrasyon bayragi False olmali."""
    s = zi.zincir_istatistikleri(
        [{"option_type": "call", "volume": 1, "open_interest": 1}])
    assert s["kalibrasyon_gecerli"] is False, s
    metin = " ".join(str(v) for v in s.values())
    for desen, aciklama in YASAK_IFADELER:
        m = desen.search(metin)
        assert m is None, f"yasak ifade ciktida: {m.group(0)!r} ({aciklama})"
    print(f"  [OK] ciktida yon/emir ifadesi yok ({len(YASAK_IFADELER)} desen), "
          "kalibrasyon_gecerli=False")


def test_yasak_ifade_deseni_gercekten_yakaliyor():
    """Yukaridaki testin 'hep gecen' bos bir test olmadigini kanitlar."""
    ornekler = ["Bu hisseyi ALIN", "satin al", "yukselecek", "garanti",
                "EKLE", "DIKKAT ET", "kesinlikle", "yatirim tavsiyesi degildir"]
    for o in ornekler:
        assert any(d.search(o) for d, _ in YASAK_IFADELER), f"yakalanmadi: {o!r}"
    # olgusal/nötr ifadeler YANLIS pozitif URETMEMELI
    for temiz in ["olgusal sayimdir", "alis/satis yonu atanamaz",
                  "mutlak bir esik yoktur", "toplam acik pozisyon"]:
        assert not any(d.search(temiz) for d, _ in YASAK_IFADELER), \
            f"yanlis pozitif: {temiz!r}"
    print(f"  [OK] desenler {len(ornekler)}/{len(ornekler)} yasak ifadeyi "
          "yakaliyor, 4 olgusal ifadede yanlis pozitif yok")


def test_dex_vanna_moduluyle_cakismaz():
    """Bu modul dex_vanna'nin sayaclarina DOKUNMAZ (ayri tutulmus olmali)."""
    import dex_vanna as dv
    sonuc = dv.maruziyet_hesapla(
        [{"strike": 100, "expiration": "2030-01-18", "option_type": "call",
          "open_interest": 10, "implied_volatility": 0.3}], 100.0)
    # dex_vanna ciktisinda yeni alanlarimiz OLMAMALI
    for alan in ("put_call_hacim_orani", "acik_pozisyonsuz_hacimli_kontrat"):
        assert alan not in sonuc, f"dex_vanna ciktisina sizmis: {alan}"
    assert set(sonuc["atlanma_nedeni"]) == {
        "bozuk_alan", "acik_pozisyon_yok", "gecersiz_tip",
        "gecersiz_vade", "gecersiz_iv_veya_vade"}, sonuc["atlanma_nedeni"]
    print("  [OK] dex_vanna.atlanma_nedeni anahtarlari degismemis (5/5)")


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
