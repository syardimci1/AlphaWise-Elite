"""Kullanici bazli kota muhasebesi ve yumusak pay testleri (I-7).

NEDEN VAR (olculdu, 17.09.2026): kota sayaci YALNIZCA API anahtari basinaydi
(gex:quota:<anahtar>:<gun>). Iki somut sonucu vardi:
  1. ADALET  : bir kullanici gunun tamamini tek basina yakabiliyordu.
  2. MUHASEBE: "kim harcadi" HIC olculemiyordu, dolayisiyla CLAUDE.md'nin
               Butce Onay Kurali kullanici basina UYGULANAMIYORDU.

EN KRITIK DAVRANIS ve neden testi var: kullanici payi dolduysa ANAHTAR
sayacina HIC DOKUNULMAMALI. Aksi halde REDDEDILEN bir istek ucuncu tarafin
kotasini tuketmis gorunurdu - yani kullaniciya verilmeyen bir hak, satin
alinmis butceden dusulurdu.
"""
import sys
import types

# code 4'un pandas gerektiren modulleri icin saplama; bu testin onlarla
# ilgisi yok ve o bagimliliklar imajda henuz kurulu degil.
for _ad in ("pandas", "numpy", "oipd", "oipd_sarmalayici", "zincir_istatistik"):
    sys.modules.setdefault(_ad, types.ModuleType(_ad))
sys.modules["zincir_istatistik"].zincir_istatistikleri = lambda *a, **k: {}
_ko = types.ModuleType("kuyruk_olasiligi")
_ko.KuyrukOlasiligiHatasi = type("KuyrukOlasiligiHatasi", (Exception,), {})
_ko.kuyruk_olasiligi_hesapla = lambda *a, **k: {}
sys.modules.setdefault("kuyruk_olasiligi", _ko)

sys.path.insert(0, "/app")
import main


class SahteRedis:
    """Sayaclarin GERCEK davranisini taklit eder (incr/decr/expire/get/scan)."""

    def __init__(self):
        self.d = {}
        self.sureler = {}

    def incr(self, k):
        self.d[k] = self.d.get(k, 0) + 1
        return self.d[k]

    def decr(self, k):
        self.d[k] = self.d.get(k, 0) - 1
        return self.d[k]

    def expire(self, k, s):
        self.sureler[k] = s

    def get(self, k):
        v = self.d.get(k)
        return str(v).encode() if v is not None else None

    def scan_iter(self, match=None, count=None):
        import fnmatch
        for k in list(self.d):
            if match is None or fnmatch.fnmatch(k, match):
                yield k.encode()


def _kur(pay_yuzde=80, anahtar_basina=5, anahtar_sayisi=1):
    r = SahteRedis()
    main._redis_client = r
    main._get_redis = lambda: r
    main.KULLANICI_AZAMI_PAY_YUZDE = pay_yuzde
    main.ANAHTAR_BASINA_GUNLUK_KOTA = anahtar_basina
    main._flashalpha_anahtarlari = lambda: [
        (f"FLASHALPHA_API_KEY_{i+1}", f"k{i}") for i in range(anahtar_sayisi)
    ]
    return r


A = "c59c7853-b752-44ca-b40d-c4eb09798b50"
B = "d7e28a7c-d217-4abd-8fa5-ddc93d869d60"


def test_geriye_uyumluluk_kullanici_verilmezse_davranis_ayni():
    """kullanici=None ise davranis BUGUNKU ile birebir ayni olmali."""
    r = _kur(anahtar_basina=3)
    for i in range(3):
        izin, n = main._tek_anahtar_kota_ayir("K1")
        assert izin is True and n == i + 1, f"{i}: {izin} {n}"
    izin, n = main._tek_anahtar_kota_ayir("K1")
    assert izin is False and n == 3
    # Hicbir kullanici sayaci olusmamis olmali
    assert not [k for k in r.d if "kullanim" in k], r.d
    print("  [OK] kullanici verilmezse eski davranis birebir korunuyor")


def test_muhasebe_kim_harcadi_olculuyor():
    """Asil bosluk: 'kim harcadi' sorusu artik cevaplanabiliyor."""
    _kur(anahtar_basina=10, pay_yuzde=100)
    for _ in range(3):
        main._tek_anahtar_kota_ayir("K1", A)
    for _ in range(2):
        main._tek_anahtar_kota_ayir("K1", B)
    d = main.kullanici_kullanim_durumu()["kullanici_basina"]
    assert d[A] == 3, d
    assert d[B] == 2, d
    print(f"  [OK] kullanim dokumu: A={d[A]}, B={d[B]}")


def test_yumusak_pay_bir_kullanici_gunun_TAMAMINI_yakamaz():
    """ADALET: tek kullanici toplamin en fazla payi kadarini kullanabilir."""
    _kur(pay_yuzde=80, anahtar_basina=10, anahtar_sayisi=1)   # toplam 10, pay 8
    assert main._kullanici_azami_pay() == 8
    verilen = sum(1 for _ in range(10) if main._tek_anahtar_kota_ayir("K1", A)[0])
    assert verilen == 8, f"A'ya {verilen} verildi, 8 olmaliydi"
    # Geri kalan REZERVE: B hala hizmet alabilmeli.
    izin, _ = main._tek_anahtar_kota_ayir("K1", B)
    assert izin is True, "B, A yuzunden hizmet alamadi - rezerv calismiyor"
    print("  [OK] A payini doldurdu (8/10) ama B hala hizmet alabiliyor")


def test_REDDEDILEN_istek_ucuncu_taraf_kotasini_TUKETMEZ():
    """EN KRITIK: pay dolduysa ANAHTAR sayacina HIC dokunulmamali.

    Aksi halde kullaniciya VERILMEYEN bir hak, satin alinmis butceden dusulur.
    """
    r = _kur(pay_yuzde=50, anahtar_basina=10, anahtar_sayisi=1)  # toplam 10, pay 5
    for _ in range(5):
        assert main._tek_anahtar_kota_ayir("K1", A)[0] is True
    anahtar_once = r.d[main._kota_redis_anahtari("K1")]
    izin, _ = main._tek_anahtar_kota_ayir("K1", A)      # pay doldu -> RED
    assert izin is False
    anahtar_sonra = r.d[main._kota_redis_anahtari("K1")]
    assert anahtar_once == anahtar_sonra == 5, (
        f"reddedilen istek anahtar kotasini tuketti: {anahtar_once} -> {anahtar_sonra}")
    print("  [OK] reddedilen istek ucuncu taraf kotasindan DUSMEDI")


def test_anahtar_kotasi_dolunca_kullaniciya_harcamadigi_istek_YAZILMAZ():
    """Simetrik durum: anahtar kotasi dolarsa kullanici sayaci geri alinmali.

    MUTASYONLA YAKALANAN TEST ZAYIFLIGI (17.09.2026): ilk surum
    anahtar_sayisi=1 kullaniyordu. O durumda toplam kota = anahtar kotasi
    oldugu icin KULLANICI payi her zaman once dolup erken donuyordu ve
    anahtar-dolu dali HIC CALISMIYORDU - test, geri alma mantigi
    KALDIRILDIGINDA bile yesil kaliyordu (M14 hayatta kalmisti).
    Duzeltme: 3 anahtar tanimlanir (toplam 6) ama hep AYNI anahtar kullanilir,
    boylece anahtar 2'de dolar, kullanici payi (6) ise dolmaz.
    """
    r = _kur(pay_yuzde=100, anahtar_basina=2, anahtar_sayisi=3)
    for _ in range(2):
        assert main._tek_anahtar_kota_ayir("K1", A)[0] is True
    kullanici_once = r.d[main._kullanici_kullanim_anahtari(A)]
    izin, _ = main._tek_anahtar_kota_ayir("K1", A)      # anahtar doldu -> RED
    assert izin is False
    kullanici_sonra = r.d[main._kullanici_kullanim_anahtari(A)]
    assert kullanici_once == kullanici_sonra == 2, (
        f"kullaniciya harcamadigi istek yazildi: {kullanici_once} -> {kullanici_sonra}")
    print("  [OK] anahtar kotasi dolunca kullaniciya fazladan istek YAZILMADI")


def test_pay_yuzde_100_ise_kisit_YOK():
    """Kapatma yolu: yuzde 100 verilirse bugunku davranisa donulur."""
    _kur(pay_yuzde=100, anahtar_basina=6, anahtar_sayisi=1)
    assert main._kullanici_azami_pay() == 6
    verilen = sum(1 for _ in range(6) if main._tek_anahtar_kota_ayir("K1", A)[0])
    assert verilen == 6, verilen
    print("  [OK] pay=100 -> kisit tamamen kapali (geri donus yolu)")


def test_ucuncu_taraf_TAVANI_BUYUMUYOR():
    """Pay, tavanin ICINDE bir bolumdur; tavani ASLA buyutmez."""
    for yuzde in (10, 50, 80, 100):
        _kur(pay_yuzde=yuzde, anahtar_basina=5, anahtar_sayisi=3)  # toplam 15
        assert main._toplam_gunluk_kota() == 15
        assert main._kullanici_azami_pay() <= 15, yuzde
    print("  [OK] hicbir yuzde degerinde ucuncu taraf tavani asilmiyor")


def test_kimlik_dogrulama_enjeksiyona_kapali():
    """Redis anahtarina giren deger DAR olmali."""
    for kotu in ["../gizli", "a:b:c", "DROP TABLE", "", None, "sistem2", "x" * 200]:
        assert main._kullanici_dogrula(kotu) == main.SISTEM_KIRACI, kotu
    assert main._kullanici_dogrula(A) == A
    assert main._kullanici_dogrula(A.upper()) == A
    for kotu in ["../gizli", "a:b:c"]:
        a = main._kullanici_kullanim_anahtari(main._kullanici_dogrula(kotu))
        assert a.count(":") == 3 and ".." not in a, a
    print("  [OK] kimlik dogrulama enjeksiyona kapali")


if __name__ == "__main__":
    testler = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    hata = 0
    for t in testler:
        try:
            t()
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            hata += 1
    print(f"\nSONUC: {len(testler) - hata}/{len(testler)} PASS")
    sys.exit(1 if hata else 0)
