"""Portfoy performans serisi regresyon agi (Madde 30)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from src.seri import pozisyon_gecmisi, seri_uret, ozet


def al(gun, sembol, adet, fiyat, komisyon=0.0):
    return {"zaman": f"{gun}T15:00:00+00:00", "sembol": sembol, "yon": "buy",
            "adet": adet, "fiyat": fiyat, "komisyon": komisyon}


def sat(gun, sembol, adet, fiyat, komisyon=0.0):
    return {**al(gun, sembol, adet, fiyat, komisyon), "yon": "sell"}


# ------------------------------------------------------------ pozisyon gecmisi
def test_alimlar_adet_ve_maliyeti_ELLE_hesaplanan_gibi_birikir():
    """2 x 100 + 3 x 110 = 200 + 330 = 530; komisyon 1+2 = 3 -> 533; adet 5"""
    g = pozisyon_gecmisi([al("2026-01-02", "X", 2, 100, 1),
                          al("2026-01-03", "X", 3, 110, 2)])
    assert g["X"]["2026-01-03"]["adet"] == 5
    assert g["X"]["2026-01-03"]["maliyet"] == pytest.approx(533.0)


def test_satis_ORTALAMA_MALIYETLE_dusulur():
    """5 adet, maliyet 530 (birim 106). 2 adet satilinca maliyet 530-212=318,
    adet 3 kalir. Kalan pozisyonun birim maliyeti DEGISMEZ."""
    g = pozisyon_gecmisi([al("2026-01-02", "X", 5, 106),
                          sat("2026-01-05", "X", 2, 200)])
    son = g["X"]["2026-01-05"]
    assert son["adet"] == 3
    assert son["maliyet"] == pytest.approx(318.0)


def test_elde_olandan_FAZLA_satis_negatif_pozisyon_uretmez():
    g = pozisyon_gecmisi([al("2026-01-02", "X", 2, 100),
                          sat("2026-01-03", "X", 5, 120)])
    assert g["X"]["2026-01-03"]["adet"] == 0


def test_bilinmeyen_yon_atlanir():
    g = pozisyon_gecmisi([al("2026-01-02", "X", 2, 100),
                          {**al("2026-01-03", "X", 9, 100), "yon": "transfer"}])
    assert g["X"]["2026-01-02"]["adet"] == 2
    assert "2026-01-03" not in g["X"]


# ------------------------------------------------------------------ seri uret
FIYAT = {"X": {"2026-01-02": 100.0, "2026-01-05": 120.0, "2026-01-06": 90.0}}


def test_seri_islem_gunlerini_ELLE_hesaplanan_degerlerle_uretir():
    """2 adet x 100 alim, komisyon 0 -> maliyet 200.
       05'te fiyat 120 -> deger 240, K/Z +40 (+%20)
       06'da fiyat 90  -> deger 180, K/Z -20 (-%10)"""
    s = seri_uret([al("2026-01-02", "X", 2, 100)], FIYAT)
    assert [n["gun"] for n in s["noktalar"]] == ["2026-01-02", "2026-01-05", "2026-01-06"]
    assert s["noktalar"][1]["piyasa_degeri"] == pytest.approx(240.0)
    assert s["noktalar"][1]["gerceklesmemis_kz"] == pytest.approx(40.0)
    assert s["noktalar"][1]["gerceklesmemis_kz_yuzde"] == pytest.approx(20.0)
    assert s["noktalar"][2]["gerceklesmemis_kz"] == pytest.approx(-20.0)


def test_islem_olmayan_gunlerde_pozisyon_TASINIR():
    s = seri_uret([al("2026-01-02", "X", 2, 100)], FIYAT)
    assert all(n["maliyet"] == pytest.approx(200.0) for n in s["noktalar"])


def test_HAFTA_SONU_icin_uydurma_nokta_URETILMEZ():
    """Fiyat verisi olmayan gun seriye girmez; ara deger uydurulmaz."""
    s = seri_uret([al("2026-01-02", "X", 2, 100)], FIYAT)
    assert "2026-01-03" not in [n["gun"] for n in s["noktalar"]]
    assert "2026-01-04" not in [n["gun"] for n in s["noktalar"]]


def test_fiyati_eksik_gunde_deger_NONE_sifir_degil():
    fiyat = {"X": {"2026-01-02": 100.0, "2026-01-05": None}}
    s = seri_uret([al("2026-01-02", "X", 2, 100)], fiyat)
    ikinci = [n for n in s["noktalar"] if n["gun"] == "2026-01-05"][0]
    assert ikinci["piyasa_degeri"] is None, "eksik fiyatta 0 yazilamaz"
    assert ikinci["gerceklesmemis_kz"] is None
    assert ikinci["olculemeyen_sembol"] == ["X"]
    assert ikinci["maliyet"] == pytest.approx(200.0), "maliyet yine de bilinir"


def test_COK_SEMBOLDE_biri_eksikse_TOPLAM_deger_olculemez():
    """Kismi toplam gostermek, eksik parcayi sifir saymak olurdu."""
    islemler = [al("2026-01-02", "X", 2, 100), al("2026-01-02", "Y", 1, 50)]
    fiyat = {"X": {"2026-01-02": 100.0, "2026-01-05": 120.0},
             "Y": {"2026-01-02": 50.0, "2026-01-05": None}}
    s = seri_uret(islemler, fiyat)
    ikinci = [n for n in s["noktalar"] if n["gun"] == "2026-01-05"][0]
    assert ikinci["piyasa_degeri"] is None
    assert ikinci["olculemeyen_sembol"] == ["Y"]
    assert ikinci["acik_sembol"] == 2


def test_pozisyon_kapaninca_gun_seriye_girmez():
    islemler = [al("2026-01-02", "X", 2, 100), sat("2026-01-05", "X", 2, 120)]
    s = seri_uret(islemler, FIYAT)
    gunler = [n["gun"] for n in s["noktalar"]]
    assert "2026-01-06" not in gunler, "acik pozisyon yokken nokta uretilmemeli"


def test_islem_yoksa_durum_ACIKCA_bildirilir():
    s = seri_uret([], FIYAT)
    assert s["durum"] == "islem_yok" and s["noktalar"] == []
    assert "üretilemez" in s["gerekce"]


def test_fiyat_hic_yoksa_durum_ACIKCA_bildirilir():
    s = seri_uret([al("2026-01-02", "X", 2, 100)], {})
    assert s["durum"] == "fiyat_yok"
    assert "ölçüm eksikliğidir" in s["gerekce"]


# ------------------------------------------------------------------------ ozet
def test_ozet_SATIS_YOKKEN_gerceklesmis_kz_HESAPLANAMAZ_der():
    islemler = [al("2026-01-02", "X", 2, 100)]
    o = ozet(seri_uret(islemler, FIYAT), islemler)
    assert o["gerceklesmis_kz_var_mi"] is False
    assert any("HESAPLANAMAZ" in s for s in o["sinirlar"])


def test_ozet_YETERSIZ_ORNEKLEM_uyarisini_HER_ZAMAN_tasir():
    islemler = [al("2026-01-02", "X", 2, 100)]
    o = ozet(seri_uret(islemler, FIYAT), islemler)
    assert any("YETERSİZDİR" in s for s in o["sinirlar"])
    assert any("ölçülemedi" in s for s in o["sinirlar"])


def test_ozet_satis_varken_farkli_konusur():
    islemler = [al("2026-01-02", "X", 2, 100), sat("2026-01-05", "X", 1, 120)]
    o = ozet(seri_uret(islemler, FIYAT), islemler)
    assert o["gerceklesmis_kz_var_mi"] is True
    assert not any("hiç satış yok" in s for s in o["sinirlar"])


def test_ozet_son_olculebilen_noktayi_alir():
    fiyat = {"X": {"2026-01-02": 100.0, "2026-01-05": 120.0, "2026-01-06": None}}
    islemler = [al("2026-01-02", "X", 2, 100)]
    o = ozet(seri_uret(islemler, fiyat), islemler)
    assert o["son_piyasa_degeri"] == pytest.approx(240.0), "son OLCULEBILEN nokta"
    assert o["gun_sayisi"] == 3 and o["olculebilen_gun"] == 2


# ==================== DEFTER OKUYUCU (salt-okunur) ====================
import sqlite3
from src.defter import islemleri_oku, karar_ozeti


def defter_kur(yol, islemler=(), kararlar=()):
    k = sqlite3.connect(yol)
    k.execute("CREATE TABLE islem (id INTEGER PRIMARY KEY, karar_id INTEGER, "
              "zaman TEXT, piyasa TEXT, sembol TEXT, yon TEXT, adet REAL, "
              "fiyat REAL, komisyon REAL, kayma REAL)")
    k.execute("CREATE TABLE karar (id INTEGER PRIMARY KEY, zaman TEXT, "
              "piyasa TEXT, sembol TEXT, godmode_karar_kodu TEXT, "
              "fiyat_konumu TEXT, eylem TEXT, adet REAL, referans_fiyat REAL, "
              "gerekce TEXT, kanit_json TEXT, broker TEXT, broker_emir_id TEXT)")
    for i in islemler:
        k.execute("INSERT INTO islem (zaman,piyasa,sembol,yon,adet,fiyat,komisyon,kayma) "
                  "VALUES (?,?,?,?,?,?,?,?)", i)
    for c in kararlar:
        k.execute("INSERT INTO karar (zaman,piyasa,sembol,eylem) VALUES (?,?,?,?)", c)
    k.commit(); k.close()


def test_defter_okunur_ve_islemler_dogru_cikar(tmp_path):
    y = str(tmp_path / "d.sqlite")
    defter_kur(y, islemler=[("2026-01-02T15:00:00+00:00", "us", "MSFT", "buy",
                             2.0, 100.0, 0.2, 0.1)])
    d = islemleri_oku(y)
    assert d["durum"] == "okundu" and len(d["islemler"]) == 1
    assert d["islemler"][0]["sembol"] == "MSFT"
    assert d["islemler"][0]["komisyon"] == pytest.approx(0.2)


def test_defter_YOKSA_bos_liste_ISLEM_YOK_demek_DEGILDIR(tmp_path):
    d = islemleri_oku(str(tmp_path / "olmayan.sqlite"))
    assert d["durum"] == "defter_yok"
    assert d["islemler"] == []
    assert "GELMEZ" in d["gerekce"]


def test_bozuk_defter_okunamadi_der(tmp_path):
    y = tmp_path / "bozuk.sqlite"
    y.write_text("bu bir sqlite dosyasi degil", encoding="utf-8")
    d = islemleri_oku(str(y))
    assert d["durum"] == "okunamadi"
    assert "GELMEZ" in d["gerekce"]


def test_defter_baglantisi_SALT_OKUNUR(tmp_path):
    """Yanlislikla bile yazilamamali: baglanti mode=ro ile aciliyor."""
    y = str(tmp_path / "d.sqlite")
    defter_kur(y, islemler=[("2026-01-02T15:00:00+00:00", "us", "X", "buy",
                             1.0, 10.0, 0.0, 0.0)])
    k = sqlite3.connect(f"file:{y}?mode=ro", uri=True)
    with pytest.raises(sqlite3.OperationalError):
        k.execute("INSERT INTO islem (zaman,sembol,yon,adet,fiyat) "
                  "VALUES ('2026-01-03','Y','buy',1,1)")
    k.close()


def test_karar_ozeti_dagilimi_verir(tmp_path):
    y = str(tmp_path / "d.sqlite")
    defter_kur(y, kararlar=[("2026-01-02T10:00:00", "us", "X", "BEKLE"),
                            ("2026-01-02T11:00:00", "us", "X", "BEKLE"),
                            ("2026-01-03T10:00:00", "us", "X", "AL")])
    o = karar_ozeti(y)
    assert o["durum"] == "okundu"
    assert o["dagilim"] == {"BEKLE": 2, "AL": 1}


# ==================== FIYAT KAYNAGI ====================
from src.fiyat import gunluk_kapanislar


class SahteHttpx:
    def __init__(self, yanit): self.yanit = yanit
    def get(self, url, params=None, timeout=None):
        if isinstance(self.yanit, Exception): raise self.yanit
        return self.yanit


class SahteYanit:
    def __init__(self, kod, govde): self.status_code, self._g = kod, govde
    def json(self): return self._g


def test_fiyatlar_metin_alanlardan_dogru_cozulur():
    h = SahteHttpx(SahteYanit(200, {"data": [
        {"date": "2026-01-02", "close": "100.5"},
        {"date": "2026-01-03T00:00:00", "close": "101.25"}]}))
    f = gunluk_kapanislar(h, "X")
    assert f["fiyatlar"] == {"2026-01-02": 100.5, "2026-01-03": 101.25}


def test_fiyat_hatasi_BOS_SOZLUK_ama_GEREKCE_ile_doner():
    f = gunluk_kapanislar(SahteHttpx(SahteYanit(502, {})), "X")
    assert f["fiyatlar"] == {} and f["gerekce"] == "HTTP 502"
    f2 = gunluk_kapanislar(SahteHttpx(RuntimeError("ag yok")), "X")
    assert f2["fiyatlar"] == {} and "RuntimeError" in f2["gerekce"]


def test_govdedeki_error_alani_da_gerekceye_tasinir():
    """qlib/taa'da olculen desen: HTTP 200 + govdede error."""
    h = SahteHttpx(SahteYanit(200, {"error": "X icin veri bulunamadi"}))
    f = gunluk_kapanislar(h, "X")
    assert f["fiyatlar"] == {}
    assert "veri bulunamadi" in f["gerekce"]


def test_bozuk_fiyat_satiri_digerlerini_DUSURMEZ():
    h = SahteHttpx(SahteYanit(200, {"data": [
        {"date": "2026-01-02", "close": "abc"},
        {"date": "2026-01-03", "close": "101"},
        {"date": "", "close": "5"}]}))
    assert gunluk_kapanislar(h, "X")["fiyatlar"] == {"2026-01-03": 101.0}


# ==================== TAZELIK (canli olcumde bulundu) ====================
from src.seri import tazelik, is_gunu_farki


def test_is_gunu_farki_hafta_sonunu_saymaz():
    """2026-09-04 Cuma, 2026-09-07 Pazartesi -> 1 is gunu (3 takvim gunu)."""
    assert is_gunu_farki("2026-09-04", "2026-09-07") == 1
    assert is_gunu_farki("2026-09-07", "2026-09-08") == 1
    assert is_gunu_farki("2026-09-03", "2026-09-08") == 3
    assert is_gunu_farki("2026-09-08", "2026-09-08") == 0


def test_bozuk_tarih_negatif_doner_COKMEZ():
    assert is_gunu_farki("bozuk", "2026-09-08") == -1


def test_seri_BES_GUN_eskiyse_TAZE_DEGIL_der():
    """CANLI: merkezi fiyat deposunun en yeni gunu 09-03'tu, takvim 09-08'di;
    seri sessizce eski bitiyor ve 'guncel deger' gibi okunuyordu."""
    seri = {"noktalar": [{"gun": "2026-09-03", "piyasa_degeri": 100.0}]}
    t = tazelik(seri, bugun="2026-09-08")
    assert t["taze_mi"] is False
    assert t["is_gunu_yasi"] == 3
    assert "GÜNCEL DEĞİLDİR" in t["gerekce"]


def test_dunku_seri_TAZE_sayilir():
    seri = {"noktalar": [{"gun": "2026-09-07", "piyasa_degeri": 100.0}]}
    t = tazelik(seri, bugun="2026-09-08")
    assert t["taze_mi"] is True and t["gerekce"] == ""


def test_CUMA_kapanisi_PAZARTESI_taze_sayilir():
    """Takvim gunu kullanilsaydi 3 gun eski gorunurdu."""
    seri = {"noktalar": [{"gun": "2026-09-04", "piyasa_degeri": 100.0}]}
    assert tazelik(seri, bugun="2026-09-07")["taze_mi"] is True


def test_olculemeyen_son_nokta_TAZELIK_hesabina_girmez():
    seri = {"noktalar": [{"gun": "2026-09-07", "piyasa_degeri": 100.0},
                         {"gun": "2026-09-08", "piyasa_degeri": None}]}
    t = tazelik(seri, bugun="2026-09-08")
    assert t["son_gun"] == "2026-09-07", "olculemeyen nokta son sayilamaz"


def test_hic_olculebilen_nokta_yoksa_tazelik_KARARI_VERILMEZ():
    t = tazelik({"noktalar": []}, bugun="2026-09-08")
    assert t["taze_mi"] is None
    assert "değerlendirilemez" in t["gerekce"]
