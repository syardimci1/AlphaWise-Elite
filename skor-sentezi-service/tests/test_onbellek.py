"""Onbellek ve sektor indeksi testleri."""
import os, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from src import onbellek as O


@pytest.fixture
def dizin(tmp_path, monkeypatch):
    monkeypatch.setattr(O, "ONBELLEK_DIZIN", tmp_path / "onbellek")
    return tmp_path / "onbellek"


def test_yazilan_okunur(dizin):
    O.yaz("MSFT", {"ticker": "MSFT", "sektor": "Technology"})
    assert O.oku("MSFT")["sektor"] == "Technology"


def test_suresi_dolan_kayit_okunmaz(dizin):
    O.yaz("MSFT", {"ticker": "MSFT"})
    assert O.oku("MSFT", yasam_sn=3600) is not None
    assert O.oku("MSFT", yasam_sn=-1) is None, "suresi dolan kayit donmemeli"


def test_olmayan_ticker_none_doner(dizin):
    assert O.oku("YOKBOYLE") is None


def test_bozuk_dosya_cokertmez(dizin):
    dizin.mkdir(parents=True, exist_ok=True)
    (dizin / "BOZUK.json").write_text("bu json degil", encoding="utf-8")
    assert O.oku("BOZUK") is None
    assert O.tum_kayitlar() == []


def test_yazma_atomiktir_gecici_dosya_birakmaz(dizin):
    O.yaz("MSFT", {"ticker": "MSFT"})
    kalanlar = [p.name for p in dizin.iterdir()]
    assert kalanlar == ["MSFT.json"], kalanlar


def test_ticker_dosya_adi_sertlestirilir(dizin):
    """Yol asimi tek satirlik bir hata olmamali."""
    O.yaz("../../etc/passwd", {"ticker": "X"})
    olusanlar = [p.name for p in dizin.iterdir()]
    assert all("/" not in a and ".." not in a for a in olusanlar), olusanlar


def test_sektor_indeksi_yalnizca_gercek_kayitlari_iceriyor(dizin):
    O.yaz("MSFT", {"ticker": "MSFT", "sektor": "Technology"})
    O.yaz("NVDA", {"ticker": "NVDA", "sektor": "Technology"})
    O.yaz("KO", {"ticker": "KO", "sektor": "Consumer Defensive"})
    O.yaz("SEKTORSUZ", {"ticker": "SEKTORSUZ"})
    i = O.sektor_indeksi()
    assert i["Technology"] == ["MSFT", "NVDA"]
    assert i["Consumer Defensive"] == ["KO"]
    assert all("SEKTORSUZ" not in v for v in i.values()), \
        "sektoru bilinmeyen sirket indekse UYDURULARAK eklenmemeli"


def test_rakipler_hedefin_kendisini_icermez(dizin):
    O.yaz("MSFT", {"ticker": "MSFT", "sektor": "Technology"})
    O.yaz("NVDA", {"ticker": "NVDA", "sektor": "Technology"})
    r = O.sektordeki_rakipler("MSFT", "Technology")
    assert r == ["NVDA"]


def test_sektor_bilinmiyorsa_rakip_uydurulmaz(dizin):
    O.yaz("NVDA", {"ticker": "NVDA", "sektor": "Technology"})
    assert O.sektordeki_rakipler("MSFT", None) == []


def test_suresi_dolan_rakip_indekse_girmez(dizin):
    O.yaz("NVDA", {"ticker": "NVDA", "sektor": "Technology"})
    assert O.sektordeki_rakipler("MSFT", "Technology", yasam_sn=-1) == []


def test_bos_veya_bozuk_ticker_gecerli_bir_ada_indirgenir(dizin):
    O.yaz("...", {"ticker": "X"})
    O.yaz("", {"ticker": "Y"})
    adlar = sorted(p.name for p in dizin.iterdir())
    assert adlar == ["GECERSIZ.json"], adlar


def test_normal_ozel_bicimli_tickerlar_KORUNUR(dizin):
    """BRK.B / BF-B gibi gecerli semboller sertlestirmede bozulmamali."""
    O.yaz("BRK.B", {"ticker": "BRK.B", "sektor": "Financial Services"})
    O.yaz("BF-B", {"ticker": "BF-B", "sektor": "Consumer Defensive"})
    assert O.oku("BRK.B")["ticker"] == "BRK.B"
    assert O.oku("BF-B")["ticker"] == "BF-B"
    adlar = sorted(p.name for p in dizin.iterdir())
    assert adlar == ["BF-B.json", "BRK.B.json"], adlar
