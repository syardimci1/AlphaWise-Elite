"""Duzeltilmis isabet olcutu testleri — madde 47.

Uc sozlesme kilitlenir:
  1. BEKLE puanlanmaz ('uygulanamaz'), cunku 'olcemedik' bir piyasa
     cagrisi degildir.
  2. TUT piyasaya goreli olculur; piyasa getirisi yoksa SIFIR VARSAYILMAZ,
     'olculemedi' donulur.
  3. EKLE ve DIKKAT ET olcutleri DEGISMEZ (eski degerlendirmeyle
     karsilastirilabilirlik korunur).
"""
import pytest

from isabet_olcut import (ANAYASA_KODLARI, DOGRU, OLCULEMEDI, TUT_GORELI_ESIK,
                          UYGULANAMAZ, YANLIS, karar_degerlendir,
                          pencere_gecerli_mi)


# ------------------------------------------------------------- BEKLE
def test_bekle_puanlanmaz():
    r = karar_degerlendir("BEKLE", 0.15, 0.02)
    assert r["sonuc"] == UYGULANAMAZ
    assert "olcemedik" in r["gerekce"]


@pytest.mark.parametrize("getiri", [0.5, -0.5, 0.0, None])
def test_bekle_getiriden_BAGIMSIZ(getiri):
    """Fiyat ne yaparsa yapsin BEKLE puanlanmaz."""
    assert karar_degerlendir("BEKLE", getiri, 0.0)["sonuc"] == UYGULANAMAZ


def test_bekle_uygulanamaz_olculemedi_DEGIL():
    """'Uygulanamaz' ile 'olculemedi' ayni sey degil: ilkinde yarin tekrar
    denemenin anlami yok."""
    assert karar_degerlendir("BEKLE", 0.1, 0.0)["sonuc"] != OLCULEMEDI


# --------------------------------------------- Anayasa disi kodlar
@pytest.mark.parametrize("kod", ["BELIRSIZ", "risk_on", "risk_off", "", "al"])
def test_anayasa_disi_kod_puanlanmaz(kod):
    r = karar_degerlendir(kod, 0.10, 0.0)
    assert r["sonuc"] == UYGULANAMAZ
    assert "Anayasa" in r["gerekce"]


def test_anayasa_kodlari_listesi():
    assert set(ANAYASA_KODLARI) == {"EKLE", "TUT", "BEKLE", "DIKKAT ET"}


# ------------------------------------------------ EKLE / DIKKAT ET
@pytest.mark.parametrize("getiri,beklenen", [
    (0.05, DOGRU), (0.0001, DOGRU), (0.0, YANLIS), (-0.05, YANLIS)])
def test_ekle_olcutu_DEGISMEDI(getiri, beklenen):
    r = karar_degerlendir("EKLE", getiri, 0.30)
    assert r["sonuc"] == beklenen
    assert "DEGISMEDI" in r["gerekce"]


@pytest.mark.parametrize("getiri,beklenen", [
    (-0.05, DOGRU), (-0.0001, DOGRU), (0.0, YANLIS), (0.05, YANLIS)])
def test_dikkat_olcutu_DEGISMEDI(getiri, beklenen):
    assert karar_degerlendir("DIKKAT ET", getiri, -0.30)["sonuc"] == beklenen


def test_ekle_piyasa_getirisi_GEREKTIRMEZ():
    """EKLE mutlak olcut kullanir; piyasa verisi olmasa da olculebilir."""
    assert karar_degerlendir("EKLE", 0.05, None)["sonuc"] == DOGRU
    assert karar_degerlendir("DIKKAT ET", -0.05, None)["sonuc"] == DOGRU


# ------------------------------------------------------ TUT (yeni)
def test_tut_piyasaya_goreli_dogru():
    """Hisse %12, piyasa %10 -> sapma %2 < %10 -> dogru."""
    assert karar_degerlendir("TUT", 0.12, 0.10)["sonuc"] == DOGRU


def test_tut_piyasadan_sapinca_yanlis():
    """Hisse %25, piyasa %10 -> sapma %15 > %10 -> yanlis."""
    assert karar_degerlendir("TUT", 0.25, 0.10)["sonuc"] == YANLIS


def test_tut_DUZ_PIYASADA_kendiliginden_odullenmez():
    """Mutlak olcutun zayifligi: tum piyasa %20 duserken TUT makul olabilir.

    Mutlak +-%15 ile bu 'yanlis' cikardi; goreli olcutte hisse piyasayla
    birlikte dustugu icin DOGRU cikar.
    """
    r = karar_degerlendir("TUT", -0.20, -0.18)
    assert r["sonuc"] == DOGRU, "goreli olcut piyasa dususunu cezalandirdi"


def test_tut_piyasadan_ayrisirsa_yanlis_kalir():
    """Piyasa duz ama hisse %20 firladi: TUT karari kaciran bir karardi."""
    assert karar_degerlendir("TUT", 0.20, 0.0)["sonuc"] == YANLIS


def test_tut_piyasa_getirisi_yoksa_SIFIR_VARSAYILMAZ():
    """Sifir varsaymak, duz bir piyasa varsaymak olurdu."""
    r = karar_degerlendir("TUT", 0.02, None)
    assert r["sonuc"] == OLCULEMEDI
    assert "Sifir varsaymak" in r["gerekce"]


def test_tut_sinir_esikte():
    assert karar_degerlendir("TUT", 0.10, 0.0)["sonuc"] == YANLIS   # tam esik
    assert karar_degerlendir("TUT", 0.0999, 0.0)["sonuc"] == DOGRU


def test_tut_esigi_degistirilebilir():
    assert karar_degerlendir("TUT", 0.12, 0.0, esik=0.15)["sonuc"] == DOGRU
    assert karar_degerlendir("TUT", 0.12, 0.0, esik=0.05)["sonuc"] == YANLIS


@pytest.mark.parametrize("esik", [0, -0.1])
def test_gecersiz_esik_olculemedi(esik):
    assert karar_degerlendir("TUT", 0.01, 0.0, esik=esik)["sonuc"] == OLCULEMEDI


def test_varsayilan_esik_yuzde_on():
    assert TUT_GORELI_ESIK == 0.10


# ------------------------------------------------------ gecersiz girdi
def test_getiri_yoksa_olculemedi():
    for kod in ("EKLE", "TUT", "DIKKAT ET"):
        assert karar_degerlendir(kod, None, 0.0)["sonuc"] == OLCULEMEDI


@pytest.mark.parametrize("cop", ["abc", [], {}])
def test_sayi_olmayan_getiri_olculemedi(cop):
    assert karar_degerlendir("EKLE", cop, 0.0)["sonuc"] == OLCULEMEDI


def test_sayi_olmayan_piyasa_getirisi_olculemedi():
    assert karar_degerlendir("TUT", 0.01, "abc")["sonuc"] == OLCULEMEDI


def test_metin_sayi_kabul_edilir():
    """Veritabani numeric alanlari metin olarak gelebilir."""
    assert karar_degerlendir("EKLE", "0.05", None)["sonuc"] == DOGRU
    assert karar_degerlendir("TUT", "0.02", "0.01")["sonuc"] == DOGRU


# ------------------------------------------------------- pencere
def test_sifir_gunluk_pencere_reddedilir():
    """OLCULEN HATA: decision_log id=2 kaydi ayni gun degerlendirilmis ve
    'dogru' isaretlenmisti."""
    r = pencere_gecerli_mi(0)
    assert r["sonuc"] == OLCULEMEDI and "en az" in r["gerekce"]


@pytest.mark.parametrize("gun,gecerli", [(0, False), (5, False), (19, False),
                                         (20, True), (30, True), (31, True)])
def test_pencere_esigi(gun, gecerli):
    r = pencere_gecerli_mi(gun)
    assert (r["sonuc"] == DOGRU) is gecerli


def test_pencere_bilinmiyorsa_olculemedi():
    assert pencere_gecerli_mi(None)["sonuc"] == OLCULEMEDI
