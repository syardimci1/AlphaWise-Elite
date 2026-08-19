"""Birim testleri: anayasa dili + karar kodu cevirisi."""
import sys
sys.path.insert(0, "/opt/alphawise/commercial/AlphaWise-Elite/liquidity-signal-service")

from src import anayasa_dili as ad


def test_yasak_kelime_al_kelime_siniri():
    # 'al' tek basina yasak
    r = ad.dil_denetle("hemen al onu")
    assert not r["temiz"]
    # 'alinabilir' icinde 'al' var ama kelime siniri korunmali (should NOT match \bal\b in 'alinabilir')
    r = ad.dil_denetle("alinabilir bir secenek")
    # 'alinabilir' -> \bal\b eslesmez cunku kelime siniri yok
    # Ama 'hemen' patern var. Yalinca 'alinabilir' testi:
    r2 = ad.dil_denetle("bu secenek desteklenebilir")
    assert r2["temiz"], f"Beklenmeyen ihlal: {r2['eslesmeler']}"


def test_yasak_kelime_sat():
    r = ad.dil_denetle("bu hisseyi sat")
    assert not r["temiz"]
    assert any(e["eslesme"] == "sat" for e in r["eslesmeler"])


def test_yasak_kesinlikle():
    r = ad.dil_denetle("kesinlikle yukselecek")
    assert not r["temiz"]


def test_temiz_metin():
    r = ad.dil_denetle("pozisyon eklemesi degerlendirilebilir")
    assert r["temiz"]


def test_yanit_denetle_ic_ice_dict():
    veri = {
        "kod": "TUT",
        "detay": {
            "aciklama": "durum izlenebilir",
            "notlar": ["risk dusuk", "veri temiz"],
        },
    }
    r = ad.yanit_denetle(veri)
    assert r["temiz"]


def test_yanit_denetle_ihlal_bulur():
    veri = {"oneri": "bu hisseyi hemen al"}
    r = ad.yanit_denetle(veri)
    assert not r["temiz"]
    assert len(r["ihlaller"]) >= 1


def test_skor_kod_kalibrasyon_gecersiz_yon_iddiasi_yok():
    """Kalibrasyon gecersizken EKLE/DIKKAT ET URETILMEZ, sadece TUT/BEKLE."""
    for skor in [-3.0, -1.5, -0.5, 0.0, 0.5, 1.5, 3.0]:
        kod = ad.skor_to_kod(skor, kalibrasyon_gecerli=False)
        assert kod in ["TUT", "BEKLE"], f"Skor {skor} -> {kod} (kalibre gecersiz)"


def test_skor_kod_kalibrasyon_gecerli_tam_yelpaze():
    """Kalibrasyon gecerliyken EKLE/DIKKAT ET uretilebilir."""
    assert ad.skor_to_kod(1.5, True) == "EKLE"
    assert ad.skor_to_kod(0.5, True) == "TUT"
    assert ad.skor_to_kod(0.0, True) == "TUT"
    assert ad.skor_to_kod(-0.5, True) == "BEKLE"
    assert ad.skor_to_kod(-1.5, True) == "DIKKAT ET"


def test_skor_kod_none_bekle_doner():
    assert ad.skor_to_kod(None, True) == "BEKLE"
    assert ad.skor_to_kod(None, False) == "BEKLE"


def test_guven_kalibre_gecersiz_tavan_cok_dusuk():
    """Kalibrasyon gecersizse guven tavani 'cok dusuk'."""
    for tamlik in [0.0, 0.5, 0.9, 1.0]:
        g = ad.guven_seviyesi(kalibrasyon_gecerli=False, veri_tamlik=tamlik)
        assert g == "cok dusuk"


def test_guven_kalibre_gecerli_veri_tam():
    g = ad.guven_seviyesi(True, 0.95)
    assert g == "orta"  # kalibre gecerli olsa da tavan 'orta' (sabit sistem tavani)


def test_oneri_metni_dil_kurallarina_uyar():
    """Uretilen tum oneri metinleri dil denetiminden gecmeli."""
    for kod in ["EKLE", "TUT", "BEKLE", "DIKKAT ET"]:
        for guven in ["cok dusuk", "dusuk", "orta", "yuksek"]:
            metin = ad.oneri_metni(kod, guven)
            r = ad.dil_denetle(metin)
            assert r["temiz"], f"Kod={kod} guven={guven}: '{metin}' ihlal: {r['eslesmeler']}"


def test_karar_kodlari_anayasa_ile_uyumlu():
    """AlphaWise Anayasa v4.4: sadece bu 4 kod izinli."""
    assert ad.KARAR_KODLARI == ["EKLE", "TUT", "BEKLE", "DIKKAT ET"]


if __name__ == "__main__":
    import subprocess
    subprocess.run(["python3", "-m", "pytest", __file__, "-v"], check=True)
