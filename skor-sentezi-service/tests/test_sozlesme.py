"""Servis sozlesmesi: yasal uyari metni MAA ile AYNI kalmali."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest


def _anayasa_yolu():
    """maa/src/constitution.py'yi hem host'ta (goreli) hem de test
    konteynerinde (/repo baglantisi) bulur. Yalnizca goreli yola bakan ilk
    surum, konteynerde dosyayi bulamayip testi SESSIZCE ATLIYORDU; atlanan
    bir sozlesme testi, gecmis gibi gorunen bir bosluktur."""
    adaylar = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), "maa", "src", "constitution.py"),
        "/repo/maa/src/constitution.py",
        os.path.join(os.environ.get("DEPO_KOK", ""), "maa", "src", "constitution.py"),
    ]
    for y in adaylar:
        if y and os.path.exists(y):
            return y
    return None


def _maa_uyarisi():
    yol = _anayasa_yolu()
    if yol is None:
        return None
    metin = open(yol, encoding="utf-8").read()
    m = re.search(r"LEGAL_DISCLAIMER = \((.*?)\n\)", metin, re.S)
    if not m:
        return None
    return "".join(re.findall(r'"([^"]*)"', m.group(1)))


#: Yasal uyari metnini tasiyan KUTSAL OLMAYAN servis kopyalari.
KUTSAL_OLMAYAN_KOPYALAR = [
    "skor-sentezi-service",
    "stres-testi-service",
    "portfoy-service",
]


def _servis_ana_yolu(servis):
    """<servis>/src/main.py'yi _anayasa_yolu() ile AYNI cok-adayli desenle
    bulur; bulunamazsa None doner. Cagiran taraf bunu ATLAMA degil
    BASARISIZLIK olarak isler."""
    adaylar = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), servis, "src", "main.py"),
        "/repo/%s/src/main.py" % servis,
        os.path.join(os.environ.get("DEPO_KOK", ""), servis, "src", "main.py"),
    ]
    for y in adaylar:
        if y and os.path.exists(y):
            return y
    return None


def _dosyadan_uyari(yol):
    """YASAL_UYARI metnini SALT-OKUNUR cikarir. Servisi ice AKTARMAZ: ice
    aktarma, denetlenen dosyanin calisma zamani bagimliliklarini surukler ve
    metin esitligi sorusunu ilgisiz bir kurulum sorusuna cevirir."""
    metin = open(yol, encoding="utf-8").read()
    m = re.search(r"YASAL_UYARI = \((.*?)\n\)", metin, re.S)
    if not m:
        return None
    return "".join(re.findall(r'"([^"]*)"', m.group(1)))


@pytest.mark.parametrize("servis", KUTSAL_OLMAYAN_KOPYALAR)
def test_yasal_uyari_kutsal_olmayan_kopyalarda_ayni(servis):
    """Yasal uyari metninin KUTSAL OLMAYAN kopyalari, kaynaktan (maa/src/
    constitution.py) BIREBIR ayrismasin diye kilitlenir.

    KAPSAM DISI -- maa/src/main.py: o dosya KUTSAL'dir ve bu calismada ona
    erisim (yazma VE okuma) yasaktir, bu yuzden testin kapsamina bilerek
    ALINMAMISTIR. O kopyanin denetlenmesi AYRI bir karardir (bkz. AB-018).
    Bu testin YESIL olmasi, kutsal kopyanin dogrulandigi anlamina GELMEZ.

    Bu bir REGRESYON KILIDIDIR: yazildigi anda metinler zaten esittir, bu
    yuzden ilk kosuda GECER. Kapatilan kusur bir metin ayrismasi degil,
    ayrismayi yakalayacak makine garantisinin YOKLUGUDUR."""
    maa = _maa_uyarisi()
    assert maa is not None, \
        "maa/src/constitution.py okunamadi -- bu test ATLANMAZ, BASARISIZ olur"
    yol = _servis_ana_yolu(servis)
    assert yol is not None, \
        "%s/src/main.py bulunamadi -- bu test ATLANMAZ, BASARISIZ olur" % servis
    uyari = _dosyadan_uyari(yol)
    assert uyari is not None, "%s icinde YASAL_UYARI tanimi bulunamadi" % yol
    assert uyari == maa, "yasal uyari metni kaynaktan ayrismis: %s" % yol


def test_yasal_uyari_maa_ile_ayni():
    """Metin servis bagimsizligi icin kopyalandi; SESSIZCE AYRISMASIN diye
    burada denetleniyor. Anayasa Madde 1.4 bu metni zorunlu kiliyor."""
    from src.main import YASAL_UYARI
    maa = _maa_uyarisi()
    if maa is None:
        pytest.skip("maa/src/constitution.py okunamadi")
    assert YASAL_UYARI == maa, "yasal uyari metni MAA'dakiyle ayrismis"


def test_saglik_ucu_eksen_sayisini_bildirir():
    from src.main import health
    h = health()
    assert h["eksen_sayisi"] == 5 and h["asgari_eksen"] == 3
