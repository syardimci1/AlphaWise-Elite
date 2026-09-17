"""
DINAMIK MODEL SECIMI TESTLERI (04.09.2026)

=======================================================================
NEDEN BU DOSYA VAR
=======================================================================
cascade.py'ye 18.08.2026'da eklenen `_models_for()` mekanizmasi bugune
kadar HIC test edilmemisti (canli olculdu: test_langgraph_cascade.py
run_cascade'i ya da model secimini HIC cagirmiyor). Mekanizmanin tum
guvenlik iddiasi "her sorunda sabit listeye geri duser" cumlesine
dayaniyordu ve bu cumle DOGRULANMAMISTI.

Bu dosya o boslugu kapatir ve GERCEKTE olan davranisi sabitler.

=======================================================================
OLCULEN GERCEK, IDDIA EDILENDEN FARKLI (04.09.2026)
=======================================================================
cascade.py:71-72'deki yorum sunu soyluyor:

    "HERHANGI bir sorunda (Redis yok, API erisilemez, bos liste)
     asagidaki SABIT listelere geri duser"

Bu cumle KISMEN dogrudur ve testler bu ayrimi ACIKCA sabitler:

  * model_registry MODUL SEVIYESINDE PATLARSA (import hatasi, beklenmedik
    istisna) -> EVET, cascade.py'nin kendi SABIT listesine duser.
    (test_MODUL_PATLARSA_CASCADE_SABIT_LISTESINE_DUSER)

  * Redis ERISILEMEZSE -> HAYIR. model_registry kendi icinde her hatayi
    yakalayip model_registry.FALLBACK_DEFAULTS dondurur; bu BOS OLMADIGI
    icin _models_for onu kabul eder ve cascade'in SABIT listesine HIC
    ULASILMAZ. (test_REDIS_ERISILEMEZSE_REGISTRY_FALLBACKI_DONER)

Pratik sonucu: cascade.py'deki ANALYST_MODELS / CRITIC_MODELS /
MASTER_MODELS listeleri, gercekcı ariza senaryolarinda ULASILAMAZ.
Ozellikle MASTER_MODELS[0] = 'anthropic/claude-sonnet-4' HICBIR normal
kosulda secilemez. Bu bir KUSUR olabilir ya da bilincli bir tercih
olabilir - testler yalnizca GERCEGI kayda gecirir, karari kullaniciya
birakir.
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cascade            # noqa: E402
import model_registry     # noqa: E402


# =====================================================================
# 1. SOZLESME: _models_for HER ZAMAN bos olmayan bir MODEL ID listesi doner
# =====================================================================

@pytest.mark.parametrize("rol,sabit", [
    ("analyst", cascade.ANALYST_MODELS),
    ("critic", cascade.CRITIC_MODELS),
    ("master", cascade.MASTER_MODELS),
])
def test_HER_ROL_ICIN_BOS_OLMAYAN_LISTE_DONER(rol, sabit):
    d = cascade._models_for(rol, sabit)
    assert isinstance(d, list) and len(d) > 0, f"{rol} icin bos liste dondu"
    assert all(isinstance(m, str) and "/" in m for m in d), (
        f"{rol} listesi model kimligi olmayan eleman iceriyor: {d}")


def test_DONEN_DEGER_YALNIZCA_MODEL_KIMLIGIDIR():
    """EN KRITIK GUVENLIK SOZLESMESI: bu mekanizma HANGI modelin
    kullanilacagini secer; karar esiklerine, konfluans kurallarina ya da
    skorlara DOKUNAMAZ. Donen sey yalnizca bir dize listesidir - icinde
    hicbir esik/skor/karar alani YOKTUR."""
    d = cascade._models_for("master", cascade.MASTER_MODELS)
    assert all(isinstance(m, str) for m in d), (
        "model secimi dize DISINDA bir sey donduruyor - karar yoluna "
        "veri sizdirma yuzeyi olabilir")


# =====================================================================
# 2. ARIZA YOLLARI - hangi ariza NEREYE duser
# =====================================================================

def test_MODUL_PATLARSA_CASCADE_SABIT_LISTESINE_DUSER(monkeypatch):
    """cascade.py'nin yorumundaki iddianin GECERLI OLDUGU tek yol:
    model_registry beklenmedik bir istisna firlatirsa."""
    def patla(role, paket="premium"):
        raise RuntimeError("zorlanmis hata")
    monkeypatch.setattr(model_registry, "get_candidates_for_role_paketli", patla)

    for rol, sabit in (("analyst", cascade.ANALYST_MODELS),
                       ("critic", cascade.CRITIC_MODELS),
                       ("master", cascade.MASTER_MODELS)):
        assert cascade._models_for(rol, sabit) == sabit, (
            f"{rol}: modul patladiginda cascade SABIT listesine DUSMEDI")


def test_BOS_LISTE_DONERSE_CASCADE_SABIT_LISTESINE_DUSER(monkeypatch):
    """Bos liste sessizce kabul edilmemeli - bos aday listesi tum
    kaskadi basarisiz kilardi."""
    monkeypatch.setattr(model_registry, "get_candidates_for_role_paketli",
                        lambda role, paket="premium": [])
    assert cascade._models_for("master", cascade.MASTER_MODELS) == cascade.MASTER_MODELS


def test_LISTE_OLMAYAN_DEGER_DONERSE_SABIT_LISTEYE_DUSER(monkeypatch):
    """Tip kontrolu GERCEKTEN is yapiyor mu (isinstance(dynamic, list))."""
    for bozuk in ("deepseek/deepseek-chat", {"a": 1}, None, 42):
        monkeypatch.setattr(model_registry, "get_candidates_for_role_paketli",
                            lambda role, paket="premium", _b=bozuk: _b)
        assert cascade._models_for("master", cascade.MASTER_MODELS) == cascade.MASTER_MODELS, (
            f"liste olmayan deger ({bozuk!r}) kabul edildi")


def test_REDIS_ERISILEMEZSE_REGISTRY_FALLBACKI_DONER(monkeypatch):
    """OLCULEN GERCEK - cascade.py'nin yorumundan FARKLI.

    Redis erisilemedigi zaman model_registry hatayi KENDI ICINDE yakalar
    ve FALLBACK_DEFAULTS dondurur. Bu liste BOS OLMADIGI icin _models_for
    onu kabul eder; cascade.py'nin SABIT listesine HIC ULASILMAZ.

    Bu testin amaci davranisi savunmak degil, GORUNUR kilmaktir: yorum
    "sabit listeye duser" diyor, gercekte BASKA bir listeye dusuyor."""
    monkeypatch.setenv("REDIS_HOST", "127.0.0.1")
    monkeypatch.setenv("REDIS_PORT", "1")   # baglanti REDDEDILIR (hizli hata)

    d = cascade._models_for("master", cascade.MASTER_MODELS)
    assert d == model_registry.FALLBACK_DEFAULTS["master"], (
        "Redis olu iken model_registry.FALLBACK_DEFAULTS beklenirdi")
    assert d != cascade.MASTER_MODELS, (
        "beklenmedik sekilde cascade SABIT listesine dustu - bu testin "
        "belgeledigi davranis degismis olabilir, cascade.py:71-72'deki "
        "yorum artik dogru olabilir; ikisini birlikte gozden gecirin")


def test_CLAUDE_SONNET_HICBIR_NORMAL_KOSULDA_SECILMEZ(monkeypatch):
    """BELGELEME TESTI (bir iddiayi savunmuyor, bir GERCEGI sabitliyor).

    cascade.MASTER_MODELS[0] = 'anthropic/claude-sonnet-4'. Dinamik secim
    devredeyken bu model ne saglikli durumda ne de Redis arizasinda
    secilebilir - yalnizca model_registry modulu PATLARSA devreye girer.
    Bu, maliyet ve cikti kalitesi acisindan bilinmesi gereken bir
    gercektir."""
    assert cascade.MASTER_MODELS[0] == "anthropic/claude-sonnet-4"

    monkeypatch.setenv("REDIS_HOST", "127.0.0.1")
    monkeypatch.setenv("REDIS_PORT", "1")
    assert "anthropic/claude-sonnet-4" not in cascade._models_for(
        "master", cascade.MASTER_MODELS), (
        "Redis arizasinda claude-sonnet-4 secilebiliyor - bu testin "
        "belgeledigi durum degismis")


# =====================================================================
# 3. ROL CESITLENDIRMESI (25.08.2026 duzeltmesinin korunmasi)
# =====================================================================

def test_ELESTIRMEN_ANALISTLE_AYNI_TEPE_MODELI_KULLANMAZ():
    """374b678'in getirdigi guvence: 'degerlendiren, yazandan FARKLI
    olmali'. Liste UZUNLUGU korunarak yalnizca SIRA degisir."""
    analyst = cascade._models_for("analyst", cascade.ANALYST_MODELS)
    critic = cascade._models_for("critic", cascade.CRITIC_MODELS)
    if len(critic) >= 2 and len(set(critic)) >= 2:
        assert critic[0] != analyst[0], (
            f"elestirmen ve analist AYNI tepe modeli kullaniyor "
            f"({critic[0]}) - kaskad tek modele cokmus olabilir")


def test_CESITLENDIRME_LISTEYI_KISALTMAZ():
    """Fallback dayanikliligi korunmali: cesitlendirme yalnizca sira
    degistirir, aday SAYISI dusmez."""
    ham = model_registry._ham_adaylar("critic")
    cesitli = model_registry.get_candidates_for_role_paketli("critic")
    assert len(cesitli) == len(ham), (
        f"cesitlendirme aday sayisini dusurdu: {len(ham)} -> {len(cesitli)}")
    assert set(cesitli) == set(ham), "cesitlendirme aday KUMESINI degistirdi"


# =====================================================================
# 4. 'paket' PARAMETRESI - OLCULEN KOPUKLUK
# =====================================================================

def test_PAKET_PARAMETRESI_MODELS_FOR_A_ILETILMIYOR():
    """OLCULEN KUSUR (04.09.2026): run_cascade(paket=...) parametresini
    main.py'den ALIR (main.py:1001) ama _models_for cagrilarinin HICBIRINE
    iletmez - dordu de varsayilan 'premium' kullanir.

    Yani /narrative-verified?paket=basic cagrisi SESSIZCE premium model
    secimi kullanir. Bu test o kopuklugu KAYDA GECIRIR; duzeltilirse
    test kirilir ve durum yeniden degerlendirilir."""
    import inspect
    kaynak = inspect.getsource(cascade.run_cascade)
    cagrilar = [s for s in kaynak.splitlines() if "_models_for(" in s]
    assert cagrilar, "run_cascade icinde _models_for cagrisi bulunamadi"
    paket_ileten = [s for s in cagrilar if "paket" in s]
    assert not paket_ileten, (
        "paket parametresi artik iletiliyor - bu OLUMLU bir degisiklik "
        "olabilir; testi ve cascade.py'deki notu birlikte guncelleyin")
