"""Mercek (persona/lens) regresyon agi (Madde 31)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from src.mercek import (MERCEKLER, MERCEK_HARITASI, TARAFSIZ, mercek_bul, uygula)
from src.sentez import EKSEN_TANIMLARI


def sentez(puanlar=None, genel=70.0):
    adlar = ["finansal_saglik", "kazanc_kalitesi", "temel_guc", "degerleme", "temettu"]
    p = puanlar or {a: 50.0 for a in adlar}
    return {
        "ticker": "TEST", "genel_puan": genel, "olculebilen_eksen": 5,
        "genel_gerekce": "test",
        "eksenler": [{"anahtar": a, "ad": a, "puan": p.get(a), "durum":
                      "olculdu" if p.get(a) is not None else "olculemedi"}
                     for a in adlar],
    }


# ------------------------------------------------- EN ONEMLI KURAL
def test_mercek_PUANLARI_DEGISTIRMEZ():
    girdi = sentez({"finansal_saglik": 90, "kazanc_kalitesi": 80, "temel_guc": 70,
                    "degerleme": 20, "temettu": 100})
    onceki = {e["anahtar"]: e["puan"] for e in girdi["eksenler"]}
    for m in MERCEKLER:
        c = uygula(girdi, m["anahtar"])
        sonraki = {e["anahtar"]: e["puan"] for e in c["eksenler"]}
        assert sonraki == onceki, f"{m['anahtar']} puanlari degistirdi"


def test_mercek_GENEL_PUANI_DEGISTIRMEZ():
    girdi = sentez(genel=63.4)
    for m in MERCEKLER:
        assert uygula(girdi, m["anahtar"])["genel_puan"] == 63.4


def test_mercek_HICBIR_EKSENI_GIZLEMEZ():
    girdi = sentez()
    for m in MERCEKLER:
        c = uygula(girdi, m["anahtar"])
        assert len(c["eksenler"]) == len(girdi["eksenler"])
        assert ({e["anahtar"] for e in c["eksenler"]} ==
                {e["anahtar"] for e in girdi["eksenler"]})


def test_mercek_OLCUM_DURUMUNU_DEGISTIRMEZ():
    girdi = sentez({"finansal_saglik": None, "kazanc_kalitesi": 80,
                    "temel_guc": 70, "degerleme": 20, "temettu": None})
    for m in MERCEKLER:
        c = uygula(girdi, m["anahtar"])
        d = {e["anahtar"]: e["durum"] for e in c["eksenler"]}
        assert d["finansal_saglik"] == "olculemedi"
        assert d["temettu"] == "olculemedi"


# ------------------------------------------------------------- siralama
def test_temettu_mercegi_temettuyu_ONE_alir():
    c = uygula(sentez(), "temettu_odakli")
    assert c["eksenler"][0]["anahtar"] == "temettu"
    assert c["eksenler"][0]["one_cikan"] is True


def test_deger_mercegi_degerlemeyi_ONE_alir():
    c = uygula(sentez(), "deger_odakli")
    assert c["eksenler"][0]["anahtar"] == "degerleme"


def test_tarafsiz_mercek_YAYIMLANMA_sirasini_korur():
    c = uygula(sentez(), TARAFSIZ)
    assert [e["anahtar"] for e in c["eksenler"]] == [
        "finansal_saglik", "kazanc_kalitesi", "temel_guc", "degerleme", "temettu"]
    assert all(e["one_cikan"] is False for e in c["eksenler"])


def test_mercekte_ADI_GECMEYEN_eksen_sona_konur_ATILMAZ():
    girdi = sentez()
    girdi["eksenler"].append({"anahtar": "yeni_eksen", "ad": "Yeni", "puan": 10,
                              "durum": "olculdu"})
    c = uygula(girdi, "temettu_odakli")
    assert len(c["eksenler"]) == 6
    assert c["eksenler"][-1]["anahtar"] == "yeni_eksen"


# --------------------------------------------------------- bilinmeyen mercek
def test_bilinmeyen_mercek_SESSIZCE_tarafsiza_dusmez():
    m, uyari = mercek_bul("boyle_bir_mercek_yok")
    assert m["anahtar"] == TARAFSIZ
    assert uyari and "Bilinmeyen mercek" in uyari
    c = uygula(sentez(), "boyle_bir_mercek_yok")
    assert c["mercek"]["uyari"] is not None


def test_bos_mercek_tarafsizdir_ve_UYARI_VERMEZ():
    for deger in (None, "", "   "):
        m, uyari = mercek_bul(deger)
        assert m["anahtar"] == TARAFSIZ and uyari is None


def test_mercek_anahtari_buyuk_kucuk_harf_duyarsiz():
    m, uyari = mercek_bul("TEMETTU_ODAKLI")
    assert m["anahtar"] == "temettu_odakli" and uyari is None


# ------------------------------------------------------------- durustluk
def test_HER_mercek_soyleyemediklerini_YAZAR():
    for m in MERCEKLER:
        assert m["soyleyemedikleri"], f"{m['anahtar']} sinirlarini yazmiyor"
        assert all(isinstance(s, str) and len(s) > 20 for s in m["soyleyemedikleri"])


def test_her_mercek_degismezlik_notunu_tasir():
    for m in MERCEKLER:
        c = uygula(sentez(), m["anahtar"])
        assert "DEĞİŞMEZ" in c["mercek"]["degismezlik_notu"]
        assert "gizlenmez" in c["mercek"]["degismezlik_notu"]


def test_mercek_ciktisi_KARAR_KODU_icermez():
    for m in MERCEKLER:
        c = uygula(sentez(), m["anahtar"])
        metin = " ".join([c["mercek"]["ad"], c["mercek"]["aciklama"],
                          *c["mercek"]["soyleyemedikleri"],
                          *[e.get("mercek_gerekcesi", "") for e in c["eksenler"]]])
        for kod in ("EKLE", "TUT", "BEKLE", "DİKKAT ET", "DIKKAT ET"):
            assert kod not in metin


# ------------------------------------------------------- sozlesme kilitleri
def test_mercek_siralari_GERCEK_eksen_anahtarlarini_kullanir():
    """Mercek siralari sentez.py'deki eksen anahtarlariyla AYRISAMAZ."""
    gecerli = {t["anahtar"] for t in EKSEN_TANIMLARI}
    for m in MERCEKLER:
        assert set(m["sira"]) == gecerli, (
            f"{m['anahtar']} sirasi eksen anahtarlariyla ayrismis: "
            f"{set(m['sira']) ^ gecerli}")
        assert set(m["one_cikan"]) <= gecerli
        assert set(m["gerekce"]) <= gecerli


def test_mercek_anahtarlari_BENZERSIZ():
    anahtarlar = [m["anahtar"] for m in MERCEKLER]
    assert len(anahtarlar) == len(set(anahtarlar))
    assert TARAFSIZ in anahtarlar


def test_her_mercek_TUM_eksenleri_siralar():
    for m in MERCEKLER:
        assert len(m["sira"]) == len(set(m["sira"])) == len(EKSEN_TANIMLARI)


def test_her_mercek_EN_AZ_IKI_sinir_yazar_ve_bunlar_BIRBIRINDEN_FARKLI():
    """MUTASYON M6: bir mercegin sinir listesinden bir madde silmek hicbir
    testi dusurmuyordu, cunku test yalnizca 'liste bos degil' diyordu.

    Bir mercek bir yatirim FELSEFESI oneriyorsa, o felsefenin neyi
    goremedigini de soylemek zorundadir — ve bu, mercekten mercege
    KOPYALANMIS genel bir cumle olamaz."""
    ozel = [m for m in MERCEKLER if m["anahtar"] != TARAFSIZ]
    for m in ozel:
        assert len(m["soyleyemedikleri"]) >= 2, (
            f"{m['anahtar']} yalnizca {len(m['soyleyemedikleri'])} sinir yaziyor")
    # Kopyala-yapistir genel cumle olmamali: her mercegin EN AZ BIR sinir
    # cumlesi yalnizca kendisine ait olmali.
    for m in ozel:
        digerleri = {s for x in MERCEKLER if x is not m for s in x["soyleyemedikleri"]}
        kendine_ozgu = [s for s in m["soyleyemedikleri"] if s not in digerleri]
        assert kendine_ozgu, f"{m['anahtar']} sinirlarinin hepsi baska mercekten kopya"


def test_mercek_aciklamalari_da_BIRBIRINDEN_FARKLI():
    aciklamalar = [m["aciklama"] for m in MERCEKLER]
    assert len(aciklamalar) == len(set(aciklamalar))
