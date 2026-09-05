"""
Iceriden islem yon ayrimi — istatistiksel yeterlilik testleri (Madde 25).

Beklenen degerler UYGULAMADAN BAGIMSIZ turetildi: Fisher p degerleri
hipergeometrik olasiliklarin ELLE toplanmasiyla dogrulandi.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from math import comb
from src.istatistik import (fisher_kesin_p, hipergeometrik, wilson_araligi,
                            yeterlilik, ASGARI_PENCERE_OLAY)


# --------------------------------------------------------------- hipergeometrik
def test_hipergeometrik_olasiliklari_bire_toplanir():
    a, b, c, d = 4, 0, 0, 4
    ust, alt, sol = a + b, c + d, a + c
    toplam = sum(hipergeometrik(a, b, c, d, k)
                 for k in range(max(0, sol - alt), min(ust, sol) + 1))
    assert toplam == pytest.approx(1.0)


def test_hipergeometrik_elle_hesaplanan_degeri_verir():
    """4/0/0/4 tablosunda P(X=4) = C(4,4)*C(4,0)/C(8,4) = 1/70"""
    assert hipergeometrik(4, 0, 0, 4, 4) == pytest.approx(1 / 70)
    assert hipergeometrik(4, 0, 0, 4, 2) == pytest.approx(36 / 70)


def test_gecersiz_k_sifir_olasilik():
    assert hipergeometrik(4, 0, 0, 4, 9) == 0.0


# ---------------------------------------------------------------------- Fisher
def test_fisher_klasik_cay_denemesi():
    """Fisher'in kendi cay tadim deneyi: 4/0/0/4 -> iki yonlu p = 2/70.
    (k=0 ve k=4 tablolarinin olasiligi esit ve en kucuktur.)"""
    assert fisher_kesin_p(4, 0, 0, 4) == pytest.approx(2 / 70, abs=1e-12)


def test_fisher_tam_dengede_p_bire_esit():
    assert fisher_kesin_p(5, 5, 5, 5) == pytest.approx(1.0)


def test_fisher_simetriktir():
    """Satirlarin yer degistirmesi p degerini degistirmemeli."""
    assert fisher_kesin_p(3, 7, 8, 2) == pytest.approx(fisher_kesin_p(8, 2, 3, 7))


def test_fisher_bos_kenarda_bir_doner():
    assert fisher_kesin_p(0, 0, 5, 5) == 1.0
    assert fisher_kesin_p(5, 0, 5, 0) == 1.0


def test_fisher_negatif_hucre_reddeder():
    with pytest.raises(ValueError):
        fisher_kesin_p(-1, 2, 3, 4)


def test_fisher_buyuk_farkta_kucuk_p():
    kucuk = fisher_kesin_p(20, 0, 0, 20)
    buyuk = fisher_kesin_p(11, 9, 9, 11)
    assert kucuk < 0.001 and buyuk > 0.5


# ---------------------------------------------------------------------- Wilson
def test_wilson_araligi_sifir_bir_disina_TASMAZ():
    """Normal yaklasim burada [0,1] disina tasardi; Wilson tasmamali."""
    alt, ust = wilson_araligi(0, 5)
    assert alt == 0.0 and 0 < ust < 1
    alt, ust = wilson_araligi(5, 5)
    assert ust == 1.0 and 0 < alt < 1


def test_wilson_araligi_orneklem_buyudukce_DARALIR():
    dar = wilson_araligi(50, 100)
    genis = wilson_araligi(5, 10)
    assert (dar[1] - dar[0]) < (genis[1] - genis[0])


def test_wilson_bos_orneklemde_none():
    assert wilson_araligi(0, 0) is None


# ------------------------------------------------------------------ yeterlilik
def test_yetersiz_veride_test_CALISTIRILMAZ():
    y = yeterlilik(2, 1, 10, 10)
    assert y["durum"] == "yetersiz_veri"
    assert y["p_degeri"] is None
    assert "ölçüm eksikliğidir" in y["gerekce"]


def test_gecmis_yetersizse_de_test_calistirilmaz():
    y = yeterlilik(10, 10, 1, 1)
    assert y["durum"] == "yetersiz_veri" and y["p_degeri"] is None


def test_asgari_sinirinda_iki_yonlu_kanit():
    """4 olayda uretmez, 5 olayda uretir — esigin dogru yerde oldugunu gosterir."""
    dort = yeterlilik(2, 2, 10, 10, asgari=5)
    bes = yeterlilik(3, 2, 10, 10, asgari=5)
    assert dort["durum"] == "yetersiz_veri"
    assert bes["durum"] != "yetersiz_veri"


def test_kucuk_fark_AYIRT_EDILEMIYOR_der():
    y = yeterlilik(6, 4, 55, 45)
    assert y["durum"] == "ayirt_edilemiyor"
    assert y["p_degeri"] > 0.05
    assert "şansla açıklanabilir" in y["gerekce"]


def test_buyuk_fark_AYIRT_EDILIYOR_der_ama_gelecek_VAAT_ETMEZ():
    y = yeterlilik(20, 0, 0, 20)
    assert y["durum"] == "ayirt_ediliyor"
    assert y["p_degeri"] <= 0.05
    assert "GELMEZ" in y["gerekce"], "gelecege dair cikarim yapilmadigi yazmali"


def test_yeterlilik_oranlari_ve_araligi_bildirir():
    y = yeterlilik(6, 4, 55, 45)
    assert y["pencere_alim_orani"] == pytest.approx(0.6)
    assert y["gecmis_alim_orani"] == pytest.approx(0.55)
    alt, ust = y["guven_araligi_95"]
    assert alt < 0.6 < ust


def test_yeterlilik_ciktisi_yon_kodu_ICERMEZ():
    """Anayasa: bu katman karar kodu uretmez."""
    y = yeterlilik(20, 0, 0, 20)
    metin = " ".join(str(v) for v in y.values())
    for kod in ("EKLE", "TUT", "BEKLE", "DIKKAT ET"):
        assert kod not in metin


def test_ayni_oran_farkli_orneklem_farkli_sonuc_verir():
    """Maddenin ozu: 3/1 ile 300/100 ayni oran ama ayni sey degil."""
    kucuk = yeterlilik(3, 1, 30, 30, asgari=4)
    buyuk = yeterlilik(300, 100, 30, 30, asgari=4)
    assert kucuk["durum"] == "ayirt_edilemiyor"
    assert buyuk["durum"] == "ayirt_ediliyor"
    assert kucuk["pencere_alim_orani"] == buyuk["pencere_alim_orani"]


# ============ MUTASYON BOSLUKLARINI KAPATAN TESTLER ============
def test_anlamlilik_esigi_GERCEKTEN_0_05(sabit=None):
    """MUTASYON M4: ANLAMLILIK_ESIGI 0.05 -> 0.5 mutasyonu hayatta kalmisti,
    cunku hicbir test p'si 0.05 ile 0.5 ARASINDA olan bir tabloyu
    kullanmiyordu. (8,2,10,10) tablosunun p'si 0.2353'tur: 0.05 esigiyle
    'ayirt edilemiyor', 0.5 esigiyle 'ayirt ediliyor' olurdu."""
    p = fisher_kesin_p(8, 2, 10, 10)
    assert 0.05 < p < 0.5, f"test tablosu gecerli araliktan cikmis: {p}"
    y = yeterlilik(8, 2, 10, 10)
    assert y["durum"] == "ayirt_edilemiyor", (
        "0.05 esiginde bu tablo ayirt edilemez sayilmali")


def test_esik_bir_yanlis_pozitife_izin_vermiyor():
    """p = 0.0485 (< 0.05) ayirt ediliyor, p = 0.2353 (> 0.05) edilmiyor —
    esigin iki yaninda da davranis kanitlanir."""
    assert yeterlilik(9, 1, 10, 10)["durum"] == "ayirt_ediliyor"
    assert yeterlilik(8, 2, 10, 10)["durum"] == "ayirt_edilemiyor"


def test_wilson_MERKEZI_gozlenen_orandan_KAYIKTIR():
    """MUTASYON M6: Wilson merkezini duz orana (p) ceviren mutasyon hayatta
    kalmisti; testler yalnizca sinirlarin [0,1] icinde oldugunu bakiyordu.
    Wilson'in tanimi geregi merkez p'ye DEGIL, (p + z^2/2n)/(1+z^2/n)'e
    esittir. 0/5 icin ust sinir elle: 2*0.38416/1.76832 = 0.43449."""
    alt, ust = wilson_araligi(0, 5)
    assert alt == pytest.approx(0.0, abs=1e-12)
    assert ust == pytest.approx(0.43449, abs=1e-4), (
        "duz normal yaklasim burada 0.2172 verirdi; Wilson 0.4345 verir")


def test_wilson_bir_bir_durumunda_da_kayik():
    alt, ust = wilson_araligi(5, 5)
    assert ust == pytest.approx(1.0)
    assert alt == pytest.approx(1 - 0.43449, abs=1e-4), "simetrik olmali"


def test_yeterlilik_ciktisi_LAMBDA_SIFIR_kisitindan_gecer():
    """Servisin HER yaniti dogrula()'dan gecmek zorunda. Bu testi eklemenin
    nedeni: yeni bir alan adi ('yon_*' gibi) veya bir gerekce metni yasak
    desene takilirsa, bunu CALISMA ANINDA 500 hatasi olarak degil, TESTTE
    gormek gerekir."""
    from src.lambda_sifir import dogrula, LambdaSifirIhlali
    for tablo in [(8, 2, 10, 10), (20, 0, 0, 20), (2, 1, 10, 10), (0, 0, 0, 0)]:
        try:
            y = yeterlilik(*tablo)
        except ValueError:
            continue  # bos tablo zaten uretilmiyor
        dogrula({"kisi_duzeyi": y})


def test_yasak_anahtar_gercekten_yakalaniyor():
    """Yukaridaki testin sessizce her seyi gecirmedigini kanitlar."""
    from src.lambda_sifir import dogrula, LambdaSifirIhlali
    with pytest.raises(LambdaSifirIhlali):
        dogrula({"yon_kodu": "X"})


def test_gecmis_HIC_yoksa_ayri_bir_durum_bildirilir():
    """CANLI OLCUMDE BULUNDU: dort sembolde de gecmis 0A/0S cikti, cunku
    kaynak yalnizca ~3,7 aylik veri veriyor ve 90/180 gunluk pencere tum
    kayitlari yutuyor. 'az islem var' demek kullaniciyi yanlis yere baktirir;
    dogru mesaj 'karsilastirma temeli olusmadi'dir."""
    y = yeterlilik(0, 4, 0, 0)
    assert y["durum"] == "temel_yok"
    assert y["p_degeri"] is None
    assert "temeli oluşmadı" in y["gerekce"]
    assert "daha kısa bir pencere" in y["gerekce"].lower()


def test_gecmis_az_ama_VAR_ise_yetersiz_veri_denir():
    """temel_yok ile yetersiz_veri AYRI durumlardir."""
    y = yeterlilik(0, 4, 0, 2)
    assert y["durum"] == "yetersiz_veri"
    assert "ölçüm eksikliğidir" in y["gerekce"]
