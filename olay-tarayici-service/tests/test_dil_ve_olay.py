"""Dil kurali ve olay tespiti testleri."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src import bildirim, olay  # noqa: E402


def test_bildirim_yon_iddiasi_icermez():
    o = {"tur": "sec_8k", "sirket": "Ornek A.S.",
         "item_aciklamalari": [{"kod": "2.02", "aciklama": "Faaliyet sonuclarinin aciklanmasi"}],
         "kabul_zamani_utc": "2026-08-24T17:30:48.000Z"}
    m = bildirim.mesaj_kur(o)
    assert bildirim.dil_denetle(m) == []
    # KELIME SINIRI ile aranir. Ilk surum duz alt-dize ariyordu ve
    # "dosyalamasi"/"bildirilen" icindeki 'al' hecesine takiliyordu;
    # yani TEST hataliydi, kod degil (dil_denetle zaten \bal\b kullaniyor).
    import re as _re
    for y in ("al", "sat", "tavsiye", "firsat", "hemen", "kacirma"):
        assert not _re.search(rf"\b{y}\b", m, _re.I), y


def test_dil_denetimi_gercekten_yakaliyor():
    """NEGATIF KONTROL: denetimin ise yaradigini gosterir."""
    assert bildirim.dil_denetle("Bu hisseyi hemen al, kacirma") != []


def test_bildirim_varsayilan_kapali():
    """Kazayla mesaj cikmasin diye varsayilan KAPALI olmali."""
    assert bildirim.ETKIN is False


def test_sekiz_k_yalnizca_tanimli_itemlari_alir():
    g = {"name": "Ornek", "cik": 1, "tickers": ["ORN"],
         "filings": {"recent": {
             "form": ["8-K", "8-K", "10-Q"],
             "items": ["2.02,9.01", "99.99", "2.02"],
             "acceptanceDateTime": ["2099-01-01T00:00:00.000Z",
                                    "2099-01-01T00:00:00.000Z",
                                    "2099-01-01T00:00:00.000Z"],
             "filingDate": ["2099-01-01"] * 3,
             "accessionNumber": ["a", "b", "c"]}}}
    r = olay.sekiz_k_olaylari(g, azami_gun=365000)
    assert len(r) == 1                      # tanimsiz item elendi, 10-Q elendi
    assert r[0]["duzenleyici_onem"] == "yuksek"
    assert r[0]["kaynak_turu"] == "birincil_duzenleyici"


def test_eski_dosyalama_pencere_disinda_kalir():
    g = {"name": "Ornek", "cik": 1, "tickers": [],
         "filings": {"recent": {
             "form": ["8-K"], "items": ["2.02"],
             "acceptanceDateTime": ["2001-01-01T00:00:00.000Z"],
             "filingDate": ["2001-01-01"], "accessionNumber": ["a"]}}}
    assert olay.sekiz_k_olaylari(g, azami_gun=3) == []
