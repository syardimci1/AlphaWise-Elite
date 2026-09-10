"""Isabet kosucusu testleri — madde 47 (saf kisimlar).

Veritabani dokunmayan fonksiyonlar test edilir: piyasa getirisi hesabi,
tatil gunu geri bakma, ve satir degerlendirmesi. Yazma yolu ayri olarak
canli olarak dogrulanmistir (kuru calisma + yazma).
"""
from datetime import date

import pytest

from isabet_calistir import (_en_yakin_kapanis, piyasa_getirisi,
                             satirlari_degerlendir)
from isabet_olcut import DOGRU, OLCULEMEDI, UYGULANAMAZ, YANLIS

SERI = {
    "2026-07-22": 100.0,
    "2026-07-23": 101.0,
    "2026-08-21": 109.0,
    "2026-08-22": 110.0,
}


# --------------------------------------------------- en yakin kapanis
def test_tam_gun_bulunur():
    k, g = _en_yakin_kapanis(SERI, date(2026, 7, 22))
    assert k == 100.0 and g == "2026-07-22"


def test_tatil_gununde_GERIYE_bakilir():
    """2026-08-23 seride yok; bir gun geriye (08-22) bakilmali."""
    k, g = _en_yakin_kapanis(SERI, date(2026, 8, 23))
    assert k == 110.0 and g == "2026-08-22"


def test_ILERI_bakilmaz():
    """Ileri bakmak, karar aninda bilinmeyen bir fiyati kullanmak olurdu."""
    k, g = _en_yakin_kapanis(SERI, date(2026, 7, 21))
    assert k is None, f"gelecege bakildi: {g}"


def test_cok_geriye_bakilmaz():
    k, _ = _en_yakin_kapanis(SERI, date(2026, 8, 15), geriye=3)
    assert k is None


# ------------------------------------------------------ piyasa getirisi
def test_piyasa_getirisi_hesaplanir():
    g, notu = piyasa_getirisi(SERI, date(2026, 7, 22), date(2026, 8, 22))
    assert g == pytest.approx(0.10)
    assert "2026-07-22" in notu and "2026-08-22" in notu


def test_piyasa_getirisi_okunamayinca_None():
    g, notu = piyasa_getirisi({}, date(2026, 7, 22), date(2026, 8, 22))
    assert g is None and "kapanis yok" in notu


def test_sifir_kapanis_bolme_yapmaz():
    g, notu = piyasa_getirisi({"2026-07-22": 0.0, "2026-08-22": 110.0},
                             date(2026, 7, 22), date(2026, 8, 22))
    assert g is None and "gecersiz" in notu


# --------------------------------------------------- satir degerlendirme
def _satir(id_, karar, getiri, gun=31):
    b = date(2026, 7, 22)
    return {"id": id_, "ticker": "X", "decision": karar, "pct_change": getiri,
            "decided_at": b, "evaluated_at": date.fromordinal(b.toordinal() + gun)}


def test_tut_piyasaya_gore_degerlendirilir():
    # piyasa %10, hisse %12 -> sapma %2 -> dogru
    s = satirlari_degerlendir([_satir(1, "TUT", 0.12)], SERI)[0]
    assert s["sonuc"] == DOGRU and s["piyasa"] == pytest.approx(0.10)


def test_tut_piyasadan_ayrisirsa_yanlis():
    s = satirlari_degerlendir([_satir(1, "TUT", 0.25)], SERI)[0]
    assert s["sonuc"] == YANLIS


def test_bekle_uygulanamaz():
    s = satirlari_degerlendir([_satir(1, "BEKLE", 0.12)], SERI)[0]
    assert s["sonuc"] == UYGULANAMAZ


def test_sifir_gunluk_pencere_olculemedi():
    """OLCULEN HATA: id=2 kaydi ayni gun degerlendirilmis ve dogru sayilmisti."""
    s = satirlari_degerlendir([_satir(2, "TUT", 0.0012, gun=0)], SERI)[0]
    assert s["sonuc"] == OLCULEMEDI and "en az" in s["gerekce"]


def test_piyasa_okunamazsa_TUT_olculemedi_ama_EKLE_olculur():
    satirlar = [_satir(1, "TUT", 0.05), _satir(2, "EKLE", 0.05)]
    sonuc = {s["id"]: s for s in satirlari_degerlendir(satirlar, {})}
    assert sonuc[1]["sonuc"] == OLCULEMEDI
    assert sonuc[2]["sonuc"] == DOGRU, "EKLE piyasa verisi gerektirmemeli"


def test_gerekce_piyasa_penceresini_bildirir():
    s = satirlari_degerlendir([_satir(1, "TUT", 0.12)], SERI)[0]
    assert "SPY" in s["gerekce"]


def test_bos_liste():
    assert satirlari_degerlendir([], SERI) == []


def test_id_korunur():
    ids = [s["id"] for s in satirlari_degerlendir(
        [_satir(7, "EKLE", 0.1), _satir(9, "TUT", 0.1)], SERI)]
    assert ids == [7, 9]
