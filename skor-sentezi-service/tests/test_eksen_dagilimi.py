"""
Eksen dagilimi ve en dusuk eksen bildirimi (K2-07).

NEDEN BU TEST VAR
=================
Canli olcum sorunu gosterdi: AAPL genel_puan 74,6 ama degerleme ekseni 9,0.
Duz ortalama tek bir cokmus ekseni ortaliyor ve genel puana bakan kullanici
bunu goremiyor.

BU DEGISIKLIK SALT-BILDIRIMDIR
==============================
Rakibin sabit esikli VETO kapisi BILINCLI OLARAK alinmadi: gercek bir veto
kalibre edilmemis bir esik gerektirir ve sentez.py'deki "uydurulmus agirlik
sahte kesinlik yaratirdi" gerekcesiyle dogrudan celisirdi. Bu yuzden
genel_puan formulune DOKUNULMAZ; yalnizca yeni BILDIRIM alanlari eklenir.
Asagidaki ilk test bunu birebir sayiyla kilitler.

"OLCULEMEDI != NOTR" BURADA DA GECERLI
======================================
Olculemedi/uygulanamaz durumundaki eksenler en dusuk eksen hesabina GIRMEZ.
Girselerdi, puani None olan bir eksen fiilen "en dusuk" sayilir ve eksik veri
sessizce sifir muamelesi gorurdu — depoda 232d1a0 ile kapatilan hatanin ta
kendisi.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from src import sentez
from src.skorlar import Donem, Sirket
from src.olcum import Olcum, olculdu, olculemedi, uygulanamaz

# Eksen anahtari -> (skorlar'daki olcum fonksiyonu, normalizasyon'daki puan fn)
EKSEN_FONKSIYONLARI = {
    "finansal_saglik": ("altman_z", "altman_puan"),
    "kazanc_kalitesi": ("beneish_m", "beneish_puan"),
    "temel_guc": ("piotroski_f", "piotroski_puan"),
    "degerleme": ("dcf_icsel_fiyat_orani", "dcf_puan"),
    "temettu": ("temettu_dayanikligi", "temettu_puan"),
}

# Karttaki CANLI AAPL olcumu: GET :8330/skor/AAPL -> bes eksen ve genel 74,6.
CANLI_AAPL = {
    "finansal_saglik": 100.0,
    "kazanc_kalitesi": 80.2,
    "temel_guc": 88.9,
    "degerleme": 9.0,      # cokmus eksen
    "temettu": 95.0,
}


def sahte_sentez(monkeypatch, puanlar: dict) -> dict:
    """Her ekseni verilen olcume sabitleyip sentezle() cagirir.

    Gercek mali tablo fixture'i kurmak yerine olcum katmani sabitlenir: bu
    test eksen PUANLARININ nasil ozetlendigini olcer, puanlarin nasil
    hesaplandigini degil (onu test_skorlar.py olcuyor). Normalizasyon
    fonksiyonlari birim fonksiyona indirgenir, boylece verilen sayi dogrudan
    eksen puani olur ve beklenen degerler elle dogrulanabilir kalir.
    """
    for anahtar, (skor_fn, puan_fn) in EKSEN_FONKSIYONLARI.items():
        girdi = puanlar[anahtar]
        olcum = girdi if isinstance(girdi, Olcum) else olculdu(girdi)
        monkeypatch.setattr(sentez.skorlar, skor_fn, lambda *a, _o=olcum: _o)
        monkeypatch.setattr(sentez.normalizasyon, puan_fn, lambda d: d)
    return sentez.sentezle(Sirket("SAHTE", [Donem("2026")], piyasa={}))


def test_en_dusuk_eksen_bildirilir_ve_genel_puan_DEGISMEZ(monkeypatch):
    """(1) Cokmus eksen adiyla bildirilir; genel puan duz ortalama KALIR.

    74,6 sayisi karttaki canli olcumden birebir alindi. Biri genel_puan'a
    bir veto/tavan uygularsa bu sayi degisir ve test duser — formule
    dokunulmadiginin kaniti budur.
    """
    s = sahte_sentez(monkeypatch, CANLI_AAPL)

    assert s["en_dusuk_eksen"]["anahtar"] == "degerleme"
    assert s["en_dusuk_eksen"]["puan"] == pytest.approx(9.0)

    # Duz ortalama: (100,0 + 80,2 + 88,9 + 9,0 + 95,0) / 5 = 74,62 -> 74,6
    assert s["genel_puan"] == pytest.approx(74.6)
    assert s["olculebilen_eksen"] == 5

    assert s["eksen_dagilimi"]["min"] == pytest.approx(9.0)
    assert s["eksen_dagilimi"]["maks"] == pytest.approx(100.0)
    assert s["eksen_dagilimi"]["yayilim"] == pytest.approx(91.0)


def test_OLCULEMEDI_eksen_en_dusuk_eksen_hesabina_GIRMEZ(monkeypatch):
    """(2) Olculemeyen eksen "en dusuk" sayilamaz: veri yok, sifir degil."""
    puanlar = dict(CANLI_AAPL)
    puanlar["degerleme"] = olculemedi("risksiz faiz alinamadi", eksik=("risksiz_faiz",))
    s = sahte_sentez(monkeypatch, puanlar)

    assert s["en_dusuk_eksen"]["anahtar"] != "degerleme", \
        "olculemeyen eksen en dusuk sayildi -> 'olculemedi = 0' hatasi geri geldi"
    # Geriye kalan dort olculen eksenin en dusugu kazanc_kalitesi 80,2.
    assert s["en_dusuk_eksen"]["anahtar"] == "kazanc_kalitesi"
    assert s["en_dusuk_eksen"]["puan"] == pytest.approx(80.2)
    assert s["eksen_dagilimi"]["min"] == pytest.approx(80.2)
    assert s["olculebilen_eksen"] == 4


def test_UYGULANAMAZ_eksen_en_dusuk_eksen_hesabina_GIRMEZ(monkeypatch):
    """(3) Uygulanamaz eksen de girmez: olcut o sirkete yapisal olarak uymuyor."""
    puanlar = dict(CANLI_AAPL)
    puanlar["degerleme"] = uygulanamaz("bu sirket turune DCF uygulanmaz")
    s = sahte_sentez(monkeypatch, puanlar)

    assert s["en_dusuk_eksen"]["anahtar"] != "degerleme", \
        "uygulanamaz eksen en dusuk sayildi"
    assert s["en_dusuk_eksen"]["anahtar"] == "kazanc_kalitesi"
    assert s["en_dusuk_eksen"]["puan"] == pytest.approx(80.2)
    assert s["olculebilen_eksen"] == 4


def test_ucten_az_eksende_en_dusuk_eksen_de_None(monkeypatch):
    """(4) Genel puan uretilmeyen yerde en dusuk eksen de uretilmez.

    Iki eksenlik bir "en dusuk" bildirimi, genel puanin bilincli olarak
    reddettigi kesinligi arka kapidan geri getirirdi.
    """
    puanlar = dict(CANLI_AAPL)
    puanlar["temel_guc"] = olculemedi("yeterli donem yok")
    puanlar["degerleme"] = olculemedi("risksiz faiz alinamadi")
    puanlar["temettu"] = uygulanamaz("temettu odemiyor")
    s = sahte_sentez(monkeypatch, puanlar)

    assert s["olculebilen_eksen"] == 2 < sentez.ASGARI_EKSEN
    assert s["genel_puan"] is None
    assert s["en_dusuk_eksen"] is None
    assert s["eksen_dagilimi"] is None
    # Alanlarin NEDEN bos oldugu sessiz kalmaz.
    assert "sıfır olarak sayılmaz" in s["genel_gerekce"]
