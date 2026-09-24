"""Veri tazeligi sozlesmesi — K2-06 (Seeking Alpha rakip denetimi).

Rakip, kantitatif notlarin gunde bir kez ve piyasa acilisindan once
guncellendigini ACIK BIR SOZLESME olarak yayimliyor. Buradaki karsiligi:
kullanici gordugu skorun ne zaman hesaplandigini ve kac saniyelik oldugunu
yanittan okuyabilmeli. Yanitta yalnizca 'onbellekten' (bool) vardi; bu, bir
skorun 10 saniyelik mi yoksa 23 saatlik mi oldugunu SOYLEMIYOR.

Onbellek yasi ile KAYNAK VERI gecikmesi AYRI AYRI bildirilir: mali tablolar
ceyreklik (XBRL) yayimlandigi icin taze bir onbellek bile aylar oncesinin
bilancosuna dayanabilir. Ikisini tek ifadede eritmek, tazeligi gizlemek
olurdu — ayni ayrim: gamma-exposure-service/test_gex_onbellek.py:43
(test_tazelik_metni_toplam_gecikmeyi_gizlemez).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from src import onbellek as O

GUN = 24 * 3600


@pytest.fixture
def dizin(tmp_path, monkeypatch):
    monkeypatch.setattr(O, "ONBELLEK_DIZIN", tmp_path / "onbellek")
    return tmp_path / "onbellek"


def test_taze_yanit_hesaplama_zamanini_doldurur():
    """(1) ve (3): yas 0 iken 'taze' denir, hesaplama_zamani DOLU gelir.

    onbellekten=False olmasi, zamanin bildirilmemesi icin gerekce degildir:
    kullanici taze yanitta da sayinin hangi ana ait oldugunu bilmeli.
    """
    y = O.taze_yanit({"ticker": "MSFT"}, 1700000000.0, GUN)
    assert y["onbellekten"] is False
    assert y["onbellek_yasi_saniye"] == 0
    assert y["hesaplama_zamani"], "hesaplama_zamani DOLU olmali (None/bos degil)"
    assert y["hesaplama_zamani"] == "2023-11-14T22:13:20+00:00"
    assert "taze" in y["veri_tazeligi"]
    assert y["ticker"] == "MSFT", "veri alanlari korunmali"


def test_tazelik_metni_yasin_buyudugunu_yansitir():
    """(2) Yas ttl'e yaklastikca metin DEGISIR; sabit metin donmez."""
    bir_saat = O.tazelik_metni(3600, GUN)
    yirmi_saat = O.tazelik_metni(20 * 3600, GUN)
    assert bir_saat != yirmi_saat, "tazelik metni yasa gore degismeli"
    assert "3600 sn" in bir_saat and "1.0 saat" in bir_saat
    assert "72000 sn" in yirmi_saat and "20.0 saat" in yirmi_saat


def test_tazelik_metni_kaynak_gecikmesini_gizlemez():
    """(4) Onbellek yasi, kaynagin CEYREKLIK gecikmesini ortmez.

    Taze bir onbellek 'her sey guncel' anlamina gelmez; mali tablo ucer ayda
    bir yayimlanir ve bu, onbellek yasindan BAGIMSIZ bir gecikmedir.
    """
    for metin in (O.tazelik_metni(0, GUN), O.tazelik_metni(3600, GUN)):
        assert "ceyreklik" in metin, "kaynak verinin donemi bildirilmeli"
        assert "3 ay" in metin, "kaynak gecikmesinin buyuklugu bildirilmeli"


def test_onbellek_isabetinde_yas_ve_hesaplama_zamani_bildirilir(dizin):
    """Isabet yaniti kac saniye once hesaplandigini SOYLER."""
    O.yaz("MSFT", {"ticker": "MSFT", "sektor": "Technology"})
    kayit = O.oku_kayit("MSFT")
    assert kayit is not None and "zaman" in kayit
    y = O.isabet_yaniti(kayit, kayit["zaman"] + 7200, GUN)
    assert y["onbellekten"] is True
    assert y["onbellek_yasi_saniye"] == 7200
    assert y["hesaplama_zamani"] == O.zaman_metni(kayit["zaman"])
    assert "7200 sn" in y["veri_tazeligi"]
    assert y["sektor"] == "Technology", "onbellekteki veri korunmali"


def test_yas_negatife_dusmez(dizin):
    """Saat kaymasi yasin eksi gorunmesine yol acmamali."""
    O.yaz("MSFT", {"ticker": "MSFT"})
    kayit = O.oku_kayit("MSFT")
    y = O.isabet_yaniti(kayit, kayit["zaman"] - 5, GUN)
    assert y["onbellek_yasi_saniye"] == 0
