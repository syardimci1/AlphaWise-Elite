"""Sektor-normalize rakip karsilastirmasi (Madde 24) regresyon agi."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from src.karsilastirma import (yuzdelik_sira, medyan, eksen_karsilastir,
                               sektor_karsilastir, ASGARI_RAKIP)


# ------------------------------------------------------------ yuzdelik sira
def test_en_dusuk_deger_sifira_yakin_sira_alir():
    assert yuzdelik_sira(1, [2, 3, 4, 5]) == 0.0


def test_en_yuksek_deger_yuze_yakin_sira_alir():
    assert yuzdelik_sira(9, [2, 3, 4, 5]) == 100.0


def test_ortadaki_deger_elle_hesaplanan_sirayi_alir():
    """[10,20,30,40] icinde 25: dusuk olan 2, esit 0 -> 100*2/4 = 50"""
    assert yuzdelik_sira(25, [10, 20, 30, 40]) == 50.0


def test_esit_degerler_YARIM_sayilir():
    """[10,20,20,30] icinde 20: dusuk 1, esit 2 -> 100*(1+1)/4 = 50.
    Esitleri tam saymak ayni degerdeki herkesi 'en ust' gosterirdi."""
    assert yuzdelik_sira(20, [10, 20, 20, 30]) == 50.0


def test_bos_dagilim_hata_verir():
    with pytest.raises(ValueError):
        yuzdelik_sira(5, [])


def test_medyan_tek_ve_cift_sayida_dogru():
    assert medyan([3, 1, 2]) == 2
    assert medyan([4, 1, 2, 3]) == 2.5
    assert medyan([]) is None


# ------------------------------------------------- EN KRITIK: olculemeyen rakip
def test_olculemeyen_rakip_dagilimdan_CIKARILIR_sifir_sayilmaz():
    """Bes rakibin ikisi olculemedi. Onlar 0 sayilsaydi hedef yapay olarak
    yukari cikardi; dogru davranis dagilimdan cikarmaktir."""
    k = eksen_karsilastir(50.0, [60, 70, None, None, 80], asgari=3)
    assert k["rakip_sayisi"] == 3
    assert k["olculemeyen_rakip"] == 2
    assert k["yuzdelik"] == 0.0, "50, [60,70,80] icinde en alttadir"
    assert k["medyan"] == 70


def test_olculemeyen_rakipler_sifir_sayilsaydi_sonuc_farkli_olurdu():
    """Yanlis davranisin gercekten farkli sonuc verdigini gosterir; yani bu
    test bir seyi GERCEKTEN koruyor."""
    dogru = eksen_karsilastir(50.0, [60, 70, None, None, 80], asgari=3)
    yanlis = eksen_karsilastir(50.0, [60, 70, 0, 0, 80], asgari=3)
    assert dogru["yuzdelik"] != yanlis["yuzdelik"]
    assert yanlis["yuzdelik"] == 40.0 and dogru["yuzdelik"] == 0.0


def test_yetersiz_rakipte_yuzdelik_URETILMEZ():
    k = eksen_karsilastir(50.0, [60, 70, 80], asgari=ASGARI_RAKIP)
    assert k["durum"] == "yetersiz_rakip"
    assert k["yuzdelik"] is None
    assert "en az 5" in k["gerekce"]


def test_asgari_sinirinda_tam_esitlikte_URETILIR():
    """Esik iki yonlu kanit: 4'te uretmez, 5'te uretir."""
    dort = eksen_karsilastir(50.0, [10, 20, 30, 40], asgari=5)
    bes = eksen_karsilastir(50.0, [10, 20, 30, 40, 45], asgari=5)
    assert dort["yuzdelik"] is None
    assert bes["yuzdelik"] == 100.0


def test_hedef_olculemediyse_yuzdelik_URETILMEZ():
    k = eksen_karsilastir(None, [10, 20, 30, 40, 50], asgari=5)
    assert k["durum"] == "hedef_olculemedi" and k["yuzdelik"] is None
    assert k["medyan"] == 30, "rakip medyani yine de bildirilir"


def test_hedef_puani_SIFIR_ise_yine_de_hesaplanir():
    """Olculmus sifir gecerli bir degerdir; olculemedi ile karistirilamaz."""
    k = eksen_karsilastir(0.0, [10, 20, 30, 40, 50], asgari=5)
    assert k["durum"] == "olculdu" and k["yuzdelik"] == 0.0


# -------------------------------------------------------------- tam karsilastirma
def eksen(anahtar, puan, durum="olculdu"):
    return {"anahtar": anahtar, "ad": anahtar, "puan": puan, "durum": durum}


def sirket(t, puanlar):
    adlar = ["finansal_saglik", "kazanc_kalitesi", "temel_guc", "degerleme", "temettu"]
    return {"ticker": t, "sektor": "Technology",
            "eksenler": [eksen(a, p, "olculdu" if p is not None else "olculemedi")
                         for a, p in zip(adlar, puanlar)]}


def test_sektor_karsilastirma_bes_ekseni_de_dondurur():
    hedef = sirket("HEDEF", [50, 50, 50, 50, 50])
    rakipler = [sirket(f"R{i}", [10 * i, 10 * i, 10 * i, 10 * i, 10 * i])
                for i in range(1, 7)]
    s = sektor_karsilastir(hedef, rakipler, asgari=5)
    assert len(s["eksenler"]) == 5
    assert s["rakip_sayisi"] == 6
    assert all(e["durum"] == "olculdu" for e in s["eksenler"])


def test_genel_konum_ucten_az_eksende_URETILMEZ():
    hedef = sirket("HEDEF", [50, None, None, None, 50])
    rakipler = [sirket(f"R{i}", [10 * i, 10 * i, 10 * i, 10 * i, 10 * i])
                for i in range(1, 7)]
    s = sektor_karsilastir(hedef, rakipler, asgari=5)
    assert s["genel_yuzdelik"] is None
    assert "sıfır olarak sayılmaz" in s["genel_gerekce"]


def test_genel_konum_tam_ucte_URETILIR():
    hedef = sirket("HEDEF", [50, 50, 50, None, None])
    rakipler = [sirket(f"R{i}", [10 * i, 10 * i, 10 * i, 10 * i, 10 * i])
                for i in range(1, 7)]
    s = sektor_karsilastir(hedef, rakipler, asgari=5)
    assert s["genel_yuzdelik"] is not None


def test_rakiplerin_eksik_ekseni_o_eksenin_sayimini_dusurur():
    hedef = sirket("HEDEF", [50, 50, 50, 50, 50])
    rakipler = [sirket("R1", [10, None, 10, 10, 10]),
                sirket("R2", [20, None, 20, 20, 20]),
                sirket("R3", [30, None, 30, 30, 30]),
                sirket("R4", [40, 40, 40, 40, 40]),
                sirket("R5", [60, 60, 60, 60, 60])]
    s = sektor_karsilastir(hedef, rakipler, asgari=5)
    saglik = next(e for e in s["eksenler"] if e["anahtar"] == "finansal_saglik")
    kalite = next(e for e in s["eksenler"] if e["anahtar"] == "kazanc_kalitesi")
    assert saglik["rakip_sayisi"] == 5 and saglik["durum"] == "olculdu"
    assert kalite["rakip_sayisi"] == 2 and kalite["durum"] == "yetersiz_rakip"
    assert kalite["olculemeyen_rakip"] == 3


def test_rakip_yoksa_hicbir_eksende_konum_uretilmez():
    s = sektor_karsilastir(sirket("HEDEF", [50, 50, 50, 50, 50]), [], asgari=5)
    assert s["genel_yuzdelik"] is None
    assert all(e["yuzdelik"] is None for e in s["eksenler"])
