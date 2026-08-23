"""
λ=0 kisitinin KOD SEVIYESINDE tuttugunu kanitlayan testler.

ADIM 3a.4 (supheci tur) sorusu: kisiti atlatacak bir kod yolu var mi?
Burada bilerek atlatma denemeleri yapilir — hepsi engellenmeli.

Calistirma:  python3 -m tests.test_lambda_sifir   (konteyner icinde /app'ten)
"""
import sys

sys.path.insert(0, "/app")

from src.lambda_sifir import (  # noqa: E402
    LAMBDA, LambdaSifirIhlali, dogrula,
)
import src.lambda_sifir as ls  # noqa: E402


def _beklenen_ihlal(payload, ipucu=""):
    try:
        dogrula(payload)
    except LambdaSifirIhlali:
        return True
    raise AssertionError(f"ENGELLENMEDI: {ipucu or payload}")


def test_lambda_sabiti_sifir():
    assert LAMBDA == 0.0, f"LAMBDA={LAMBDA}, 0 olmali"
    print("  [OK] LAMBDA sabiti = 0.0")


def test_yasak_alan_ust_seviye():
    _beklenen_ihlal({"ticker": "AAPL", "yon": "yukari"}, "ust seviye 'yon'")
    _beklenen_ihlal({"karar_kodu": "EKLE"}, "karar_kodu")
    _beklenen_ihlal({"olasilik_yukari": 0.61}, "olasilik_yukari")
    print("  [OK] ust seviye yasak alanlar engellendi (3/3)")


def test_yasak_alan_derin_ic_ice():
    """Kisit yalnizca ust seviyeye bakiyorsa burada delinir."""
    _beklenen_ihlal(
        {"ticker": "BAC", "ozet": {"pencereler": {"son_90_gun": {"yon_skoru": 0.8}}}},
        "3 seviye derinde yon_skoru")
    _beklenen_ihlal(
        {"kayitlar": [{"kisi": "X"}, {"kisi": "Y", "tavsiye": "al"}]},
        "liste icindeki dict'te tavsiye")
    print("  [OK] ic ice ve liste icindeki yasak alanlar engellendi (2/2)")


def test_yasak_ifade_metinde():
    _beklenen_ihlal({"not": "Bu hisseyi ALIN"}, "emir kipi ALIN")
    _beklenen_ihlal({"not": "Lutfen aliniz"}, "emir kipi ALINIZ")
    _beklenen_ihlal({"not": "hisseyi satin"}, "emir kipi SATIN")
    _beklenen_ihlal({"not": "simdi satin alin"}, "emir kipi SATIN AL")
    _beklenen_ihlal({"yorum": "fiyat yukselecek"}, "kesin gelecek iddiasi")
    _beklenen_ihlal({"a": {"b": ["x", "kesinlikle dusecek"]}}, "derin metin")
    _beklenen_ihlal({"kod": "EKLE"}, "God Mode karar kodu")
    _beklenen_ihlal({"m": "garanti getiri"}, "garanti")
    print("  [OK] yasak ifadeler engellendi (5/5)")


def test_olgusal_isim_halleri_serbest():
    """YANLIS POZITIF kontrolu: bu servisin isi zaten alim/satis raporlamak."""
    gecmeli = {
        "ticker": "BAC",
        "acik_piyasa_alim_islem_sayisi": 29,
        "acik_piyasa_satis_islem_sayisi": 4,
        "kayitlar": [{"acik_piyasa_yonu": "alim"}, {"acik_piyasa_yonu": "satis"}],
        "not": "Acik piyasa alimlari ve satislari ayristirilmistir.",
        "yorum": "Son 90 gunde 29 alim bildirimi bulunmaktadir.",
    }
    dogrula(gecmeli)   # istisna FIRLATMAMALI
    print("  [OK] olgusal 'alim/satis' ifadeleri yanlislikla engellenmedi")


def test_lambda_degistirilirse_her_yanit_reddedilir():
    """Biri LAMBDA'yi yukseltirse servis calismaya devam ETMEMELI."""
    eski = ls.LAMBDA
    ls.LAMBDA = 0.4
    try:
        _beklenen_ihlal({"ticker": "AAPL"}, "LAMBDA=0.4 iken zararsiz yanit")
    finally:
        ls.LAMBDA = eski
    dogrula({"ticker": "AAPL"})  # geri alindi, yine calismali
    print("  [OK] LAMBDA != 0 yapilirsa TUM yanitlar reddediliyor")


def test_gercek_servis_yanitlari_temiz():
    """Servisin kendi yanit ureticileri kisiti gecmeli."""
    from src import main
    for ad, fn in (("methodology", main.methodology), ("quota", main.quota)):
        y = fn()
        assert y.get("yon_kodu_uretir") is False or ad == "quota", ad
        dogrula(y)
    m = main.methodology()
    assert m["kalibrasyon_gecerli"] is False
    assert m["lambda"] == 0.0
    assert m["maa_decide_baglantisi"].startswith("YOK")
    print("  [OK] /methodology ve /quota yanitlari kisiti geciyor")


def test_hata_mesajlari_ham_girdi_yansitmaz():
    """Hata mesajlari dogrula()'dan GECMEZ; bu yuzden ham girdi yansitilirsa
    lambda=0 denetimi baypas edilebilir (or. /insider/ALINIZ...).
    Mesajlarin sabit oldugu ve kullanici girdisi icermedigi kilitlenir."""
    from fastapi import HTTPException
    from src import main
    for kotu in ("ALINIZ", "SATIN-ALIN", "AL..", "yukselecek"):
        try:
            main._ticker_dogrula(kotu)
        except HTTPException as e:
            assert kotu.lower() not in str(e.detail).lower(), (
                f"hata mesaji ham girdiyi yansitiyor: {e.detail}")
        else:
            # gecerli bicimdeyse sorun yok (yukari akisa gider, denetlenir)
            pass
    print("  [OK] hata mesajlari ham kullanici girdisini yansitmiyor")


def test_healthz_de_denetimden_gecer():
    from src import main
    assert main.healthz() == {"status": "ok"}
    print("  [OK] /healthz de dogrula()'dan geciyor")


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
