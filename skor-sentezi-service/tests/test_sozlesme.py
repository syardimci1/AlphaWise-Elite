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
