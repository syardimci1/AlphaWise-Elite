"""Gomme onbellegi testleri — madde 48.

En kritik sozlesme: model degisirse onbellek KENDILIGINDEN gecersizlesir.
Eski vektorlerle yeni modeli karistirmak sessizce yanlis arama sonucu
uretirdi ve bunu fark etmenin bir yolu olmazdi.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, "/app/src")
sys.path.insert(0, "/app")

from gomme_onbellek import DENEME_METNI, GommeOnbellegi  # noqa: E402


def sahte_model(tohum=1.0, sayac=None):
    """Deterministik sahte gomme; cagri sayisini sayar."""
    def fn(metinler):
        out = []
        for m in metinler:
            if sayac is not None:
                sayac.append(m)
            h = sum(ord(c) for c in m)
            out.append([tohum * h % 7, tohum * len(m) % 5, tohum])
        return out
    return fn


# ------------------------------------------------------------- temel
def test_ayni_metin_IKINCI_KEZ_hesaplanmaz():
    cagrilar = []
    o = GommeOnbellegi(sahte_model(sayac=cagrilar))
    a = o.gom("gamma exposure")
    b = o.gom("gamma exposure")
    assert a == b
    # parmak izi icin 1 cagri + metin icin 1 cagri = 2; ikincisi eklenmemeli
    assert cagrilar.count("gamma exposure") == 1, (
        f"metin iki kez gommelendi: {cagrilar}")
    assert o.isabet == 1 and o.iska == 1


def test_farkli_metin_ayri_hesaplanir():
    cagrilar = []
    o = GommeOnbellegi(sahte_model(sayac=cagrilar))
    o.gom("a"); o.gom("b")
    assert o.iska == 2 and o.isabet == 0


def test_kapasite_asilinca_EN_ESKI_atilir():
    cagrilar = []
    o = GommeOnbellegi(sahte_model(sayac=cagrilar), kapasite=2)
    o.gom("bir"); o.gom("iki"); o.gom("uc")     # 'bir' atilmali
    o.gom("iki")                                 # hala onbellekte -> isabet
    assert o.isabet == 1
    o.gom("bir")                                 # atilmisti -> iska
    assert o.iska == 4


def test_kullanim_sirasi_LRU_olarak_guncellenir():
    o = GommeOnbellegi(sahte_model(), kapasite=2)
    o.gom("bir"); o.gom("iki")
    o.gom("bir")                 # 'bir' tazelenir
    o.gom("uc")                  # 'iki' atilmali, 'bir' kalmali
    isabet_once = o.isabet
    o.gom("bir")
    assert o.isabet == isabet_once + 1, "LRU sirasi guncellenmemis"


# ----------------------------------------------- model parmak izi
def test_model_degisince_ONBELLEK_GECERSIZLESIR():
    """Eski vektorlerle yeni modeli karistirmak sessizce yanlis sonuc uretirdi."""
    o1 = GommeOnbellegi(sahte_model(tohum=1.0))
    o2 = GommeOnbellegi(sahte_model(tohum=2.0))
    assert o1.parmak_izi() != o2.parmak_izi(), (
        "farkli modeller ayni parmak izini uretti")
    # ayni metin, farkli modelde farkli anahtar
    assert o1._anahtar("x") != o2._anahtar("x")


def test_ayni_model_ayni_parmak_izi():
    a = GommeOnbellegi(sahte_model(tohum=1.0)).parmak_izi()
    b = GommeOnbellegi(sahte_model(tohum=1.0)).parmak_izi()
    assert a == b


def test_parmak_izi_bir_kez_hesaplanir():
    cagrilar = []
    o = GommeOnbellegi(sahte_model(sayac=cagrilar))
    o.parmak_izi(); o.parmak_izi(); o.gom("x")
    assert cagrilar.count(DENEME_METNI) == 1


def test_anahtar_metni_de_ayirir():
    o = GommeOnbellegi(sahte_model())
    assert o._anahtar("a") != o._anahtar("b")


# ------------------------------------------------------------ durum
def test_hic_sorgu_yokken_isabet_orani_None():
    """Sifir degil None: 'olculemedi' ile 'hic isabet yok' ayni sey degil."""
    o = GommeOnbellegi(sahte_model())
    assert o.durum()["isabet_orani"] is None


def test_isabet_orani_hesaplanir():
    o = GommeOnbellegi(sahte_model())
    o.gom("a"); o.gom("a"); o.gom("a")
    assert o.durum()["isabet_orani"] == pytest.approx(2 / 3, abs=0.001)


def test_durum_surec_ici_oldugunu_bildirir():
    o = GommeOnbellegi(sahte_model())
    assert "KAYBOLUR" in o.durum()["not"] and "PAYLASILMAZ" in o.durum()["not"]


def test_bosaltma_parmak_izini_de_sifirlar():
    o = GommeOnbellegi(sahte_model())
    o.gom("a"); o.parmak_izi()
    o.bosalt()
    assert o.durum()["dolu"] == 0 and o.durum()["model_parmak_izi"] is None


# ------------------------------------------------------ gecersiz girdi
def test_cagrilamaz_model_reddedilir():
    with pytest.raises(TypeError):
        GommeOnbellegi(None)
    with pytest.raises(TypeError):
        GommeOnbellegi("model")


@pytest.mark.parametrize("k", [0, -1])
def test_gecersiz_kapasite_reddedilir(k):
    with pytest.raises(ValueError):
        GommeOnbellegi(sahte_model(), kapasite=k)


def test_metin_olmayan_girdi_reddedilir():
    o = GommeOnbellegi(sahte_model())
    for cop in (None, 5, ["a"]):
        with pytest.raises(TypeError):
            o.gom(cop)


def test_bos_metin_kabul_edilir():
    """Bos sorgu gecerli bir girdi; hata degil."""
    o = GommeOnbellegi(sahte_model())
    assert o.gom("") == o.gom("")


def test_unicode_metin_ayni_anahtari_uretir():
    o = GommeOnbellegi(sahte_model())
    o.gom("şirket değerlemesi")
    o.gom("şirket değerlemesi")
    assert o.isabet == 1
