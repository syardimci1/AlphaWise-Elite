"""Kriz stres testi + Monte Carlo dusus dagilimi regresyon agi (Madde 26)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from src.kriz import (maksimum_dusus, donem_getirisi, pencere_olc,
                      tarihsel_stres, KRIZLER, ASGARI_GUN)
from src.montecarlo import (gunluk_getiriler, _yol_dususu, blok_yol, iid_yol,
                            yuzdelik, dusus_dagilimi, ASGARI_GETIRI)
import random


# ------------------------------------------------------------ maksimum dusus
def test_maksimum_dusus_elle_hesaplanan_degeri_verir():
    """100 -> 120 -> 60 -> 90: zirve 120, dip 60 -> (120-60)/120 = 0.50"""
    assert maksimum_dusus([100, 120, 60, 90]) == pytest.approx(0.50)


def test_sadece_yukselen_seride_dusus_SIFIRDIR_ve_bu_GECERLI_bir_olcumdur():
    d = maksimum_dusus([100, 110, 120, 130])
    assert d == 0.0 and d is not None


def test_dusus_ilk_zirveye_gore_degil_O_ANA_KADARKI_zirveye_gore():
    """100 -> 50 -> 200 -> 150: ilk dusus %50, ikinci (200-150)/200 = %25.
    En derin olan %50'dir. Sabit ilk zirve kullanilsaydi ikinci dusus
    yanlislikla (100-150)/100 gibi anlamsiz cikardi."""
    assert maksimum_dusus([100, 50, 200, 150]) == pytest.approx(0.50)


def test_tek_nokta_veya_bos_seride_none():
    assert maksimum_dusus([100]) is None
    assert maksimum_dusus([]) is None


def test_gecersiz_fiyatlar_atilir():
    assert maksimum_dusus([100, None, 50]) == pytest.approx(0.50)
    assert maksimum_dusus([100, 0, 50]) == pytest.approx(0.50)


def test_donem_getirisi_elle():
    assert donem_getirisi([100, 150]) == pytest.approx(0.5)
    assert donem_getirisi([100, 50]) == pytest.approx(-0.5)


# ------------------------------------------------------------------ pencere
def seri_uret(bas_yil, gun_sayisi, baslangic_fiyat=100.0, gunluk=0.0):
    import datetime as dt
    d = dt.date(bas_yil, 1, 1)
    s, f = {}, baslangic_fiyat
    for _ in range(gun_sayisi):
        if d.weekday() < 5:
            s[d.isoformat()] = f
            f *= (1 + gunluk)
        d += dt.timedelta(days=1)
    return s


def test_pencerede_veri_yoksa_OLCULEMEDI_sifir_degil():
    s = seri_uret(2023, 300)          # 2020 penceresine hic veri yok
    o = pencere_olc(s, "2020-02-19", "2020-03-23")
    assert o["durum"] == "olculemedi"
    assert o["getiri"] is None and o["maksimum_dusus"] is None
    assert "sıfır etki değildir" in o["gerekce"]


def test_asgari_gun_alti_kesit_OLCULMUS_sayilmaz():
    s = seri_uret(2020, 400)
    kisa = pencere_olc(s, "2020-02-19", "2020-02-28")   # ~7 islem gunu
    assert kisa["durum"] == "olculemedi" and kisa["islem_gunu"] < ASGARI_GUN


def test_yeterli_veri_varsa_olculur():
    s = seri_uret(2020, 400, gunluk=-0.01)
    o = pencere_olc(s, "2020-02-19", "2020-03-23")
    assert o["durum"] == "olculdu"
    assert o["maksimum_dusus"] > 0 and o["getiri"] < 0


def test_tarihsel_stres_uc_krizi_de_dondurur():
    s = seri_uret(2020, 2000)
    sonuc = tarihsel_stres(s)
    assert len(sonuc) == len(KRIZLER) == 3
    anahtarlar = [x["anahtar"] for x in sonuc]
    assert anahtarlar == ["kuresel_finans_2008", "covid_2020", "ayi_piyasasi_2022"]
    g2008 = next(x for x in sonuc if x["anahtar"] == "kuresel_finans_2008")
    assert g2008["durum"] == "olculemedi", "2020'de baslayan seri 2008'i olcemez"


def test_kriz_pencereleri_takvim_yili_DEGIL_zirve_dip():
    """Takvim yili kullanmak COVID cokusunu toparlanmayla goturur."""
    covid = next(k for k in KRIZLER if k["anahtar"] == "covid_2020")
    assert covid["baslangic"] == "2020-02-19" and covid["bitis"] == "2020-03-23"
    assert covid["baslangic"][:4] == covid["bitis"][:4]
    assert covid["bitis"] < "2020-12-31", "takvim yili sonu OLMAMALI"


# -------------------------------------------------------------- Monte Carlo
def test_gunluk_getiriler_elle():
    assert gunluk_getiriler([100, 110, 99]) == pytest.approx([0.1, -0.1])


def test_yol_dususu_elle():
    """+%20 sonra -%50: deger 1.2 -> 0.6, zirve 1.2 -> dusus 0.5"""
    assert _yol_dususu([0.2, -0.5]) == pytest.approx(0.5)


def test_blok_yol_ARDISIK_getirileri_korur():
    g = list(range(100))
    rng = random.Random(1)
    yol = blok_yol(g, ufuk=20, blok=5, rng=rng)
    # Her 5'li blok icinde ardisik artis olmali (dairesel sarma disinda)
    ardisik = sum(1 for i in range(len(yol) - 1)
                  if yol[i + 1] == (yol[i] + 1) % 100)
    assert ardisik >= 15, f"bloklar ardisikligi korumali, olculen: {ardisik}"


def test_iid_yol_ardisikligi_KORUMAZ():
    g = list(range(100))
    rng = random.Random(1)
    yol = iid_yol(g, ufuk=200, rng=rng)
    ardisik = sum(1 for i in range(len(yol) - 1)
                  if yol[i + 1] == (yol[i] + 1) % 100)
    assert ardisik < 15, "bagimsiz ornekleme ardisikligi korumamali"


def test_yuzdelik_elle():
    s = [0, 10, 20, 30, 40]
    assert yuzdelik(s, 0.0) == 0
    assert yuzdelik(s, 1.0) == 40
    assert yuzdelik(s, 0.5) == 20
    assert yuzdelik(s, 0.25) == 10


def test_ayni_tohum_ayni_sonucu_verir():
    """Tohumsuz bir stres testi iki calistirmada iki sayi verirdi."""
    g = [0.01, -0.02, 0.005, -0.03, 0.02] * 20
    a = dusus_dagilimi(g, yol_sayisi=200, ufuk=60, tohum=42)
    b = dusus_dagilimi(g, yol_sayisi=200, ufuk=60, tohum=42)
    assert a["yuzdelikler"] == b["yuzdelikler"]


def test_farkli_tohum_farkli_sonuc_verir():
    g = [0.01, -0.02, 0.005, -0.03, 0.02] * 20
    a = dusus_dagilimi(g, yol_sayisi=200, ufuk=60, tohum=1)
    b = dusus_dagilimi(g, yol_sayisi=200, ufuk=60, tohum=2)
    assert a["yuzdelikler"] != b["yuzdelikler"]


def test_yetersiz_gecmiste_simulasyon_yapilmaz():
    o = dusus_dagilimi([0.01] * 10)
    assert o["durum"] == "olculemedi" and o["yuzdelikler"] is None


def test_KUMELENMIS_kotu_donemde_blok_DAHA_DERIN_dusus_uretir():
    """Yonun VERIYE BAGLI oldugunu gosteren birinci yarim.

    Kotu gunlerin arka arkaya geldigi ve toparlanmanin OLMADIGI bir seride
    blok ornekleme daha derin dusus uretir; i.i.d. kotu gunleri dagitir."""
    g = [0.001] * 200 + [-0.03] * 40 + [0.001] * 200
    blok = dusus_dagilimi(g, yol_sayisi=400, ufuk=252, blok=20,
                          tohum=7, yontem="blok")
    iid = dusus_dagilimi(g, yol_sayisi=400, ufuk=252, tohum=7, yontem="iid")
    assert blok["yuzdelikler"]["p95"] > iid["yuzdelikler"]["p95"]


def test_TOPARLANMALI_seride_blok_DAHA_SIG_dusus_uretir():
    """Yonun VERIYE BAGLI oldugunu gosteren ikinci yarim — ve ilk surumdeki
    "i.i.d. dususu her zaman kucuk gosterir" iddiasinin CURUTULMESI.

    Gercek MSFT verisinde olculen davranis budur: sert dusus gunlerini sert
    toparlanma gunleri izler; blok ornekleme bu eslesmeyi koruyup dususu
    keser, i.i.d. ise eslesmeyi bozar."""
    g = ([-0.05, 0.05] * 100) + [0.0005] * 100   # dusus HEMEN toparlanir
    blok = dusus_dagilimi(g, yol_sayisi=400, ufuk=252, blok=20,
                          tohum=7, yontem="blok")
    iid = dusus_dagilimi(g, yol_sayisi=400, ufuk=252, tohum=7, yontem="iid")
    assert blok["yuzdelikler"]["p95"] < iid["yuzdelikler"]["p95"], (
        f"blok {blok['yuzdelikler']['p95']:.4f} vs "
        f"iid {iid['yuzdelikler']['p95']:.4f}")


def test_blok_uzunlugu_BIR_ise_iid_ile_AYNI_sonucu_verir():
    """Tutarlilik kontrolu: blok=1, blok bootstrap'in i.i.d.'ye cokmesi
    demektir. Gercek MSFT olcumunde de ikisi birebir ayni cikti."""
    g = [0.01, -0.02, 0.005, -0.03, 0.02] * 20
    blok1 = dusus_dagilimi(g, yol_sayisi=300, ufuk=120, blok=1, tohum=11)
    iid = dusus_dagilimi(g, yol_sayisi=300, ufuk=120, tohum=11, yontem="iid")
    assert blok1["yuzdelikler"] == iid["yuzdelikler"]


def test_yuzdelikler_monoton_artar():
    g = [0.01, -0.02, 0.005, -0.03, 0.02] * 20
    y = dusus_dagilimi(g, yol_sayisi=300, ufuk=120, tohum=3)["yuzdelikler"]
    assert y["medyan"] <= y["p75"] <= y["p95"] <= y["p99"] <= y["en_kotu"]


def test_cikti_TAHMIN_OLMADIGINI_yazar():
    g = [0.01, -0.02] * 40
    o = dusus_dagilimi(g, yol_sayisi=50, ufuk=30)
    assert "tahmin değildir" in o["uyari"]


# ============ MUTASYON BOSLUKLARINI KAPATAN TESTLER ============
def test_VARSAYILAN_blok_uzunlugu_gercekten_blok_etkisi_uretir():
    """MUTASYON M6: VARSAYILAN_BLOK 20 -> 1 mutasyonu hayatta kalmisti,
    cunku blok/iid karsilastirmasi blok=20'yi ACIKCA veriyordu ve varsayilan
    hic sinanmiyordu. Blok uzunlugu 1 olsaydi yontem bagimsiz ornekleme ile
    ayni seye dogru cokerdi."""
    from src.montecarlo import VARSAYILAN_BLOK
    assert VARSAYILAN_BLOK > 1, "blok uzunlugu 1 ise blok bootstrap anlamsizdir"
    g = [0.001] * 200 + [-0.03] * 40 + [0.001] * 200
    varsayilan = dusus_dagilimi(g, yol_sayisi=400, ufuk=252, tohum=7)  # blok VERILMEDI
    iid = dusus_dagilimi(g, yol_sayisi=400, ufuk=252, tohum=7, yontem="iid")
    assert varsayilan["blok_gun"] == VARSAYILAN_BLOK
    assert varsayilan["yuzdelikler"] != iid["yuzdelikler"], (
        "varsayilan blok uzunlugu iid'den FARKLI sonuc uretmeli; ayni cikiyorsa "
        "blok uzunlugu 1'e dusmus demektir")


def test_yuzdelik_ARA_DEGER_hesaplar_tabana_yuvarlamaz():
    """MUTASYON M8: ara deger yerine tabana yuvarlama hayatta kalmisti,
    cunku ornek listede istenen konumlar TAM SAYIYA denk geliyordu.
    [0,10,20,30] icin q=0.5 -> konum 1.5 -> 15 (tabana yuvarlarsa 10)."""
    assert yuzdelik([0, 10, 20, 30], 0.5) == pytest.approx(15.0)
    assert yuzdelik([0, 10, 20, 30], 0.9) == pytest.approx(27.0)
    assert yuzdelik([0, 100], 0.37) == pytest.approx(37.0)


def test_yuzdelik_tek_elemanli_ve_bos_dagilim():
    assert yuzdelik([5], 0.5) == 5.0
    with pytest.raises(ValueError):
        yuzdelik([], 0.5)
