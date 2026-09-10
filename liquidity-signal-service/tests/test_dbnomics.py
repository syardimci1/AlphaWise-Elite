"""DBnomics anahtarsiz yedek kaynak testleri — madde 44.

Modulun tek kurali test edilir: DOGRULANMAMIS bir eslesme kullanilamaz.
Bu kural olculmus bir gerceklige dayaniyor - "ayni seri adi" ile "ayni
deger" ayni sey degil (M2'de fark -21,4 / -35,7 / -43,2 olarak olculdu).
"""
import asyncio
import sys

import pytest

sys.path.insert(0, "/app")

from src import dbnomics  # noqa: E402
from src.dbnomics import DBnomicsHatasi  # noqa: E402


class _Yanit:
    def __init__(self, kod=200, govde=None, patlat=False):
        self.status_code, self._g, self._p = kod, govde, patlat

    def json(self):
        if self._p:
            raise ValueError("JSON degil")
        return self._g


class _Istemci:
    def __init__(self, yanit=None, hata=None):
        self._y, self._h = yanit, hata

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url):
        if self._h:
            raise self._h
        return self._y


def _kur(monkeypatch, yanit=None, hata=None):
    monkeypatch.setattr(dbnomics.httpx, "AsyncClient",
                        lambda *a, **k: _Istemci(yanit, hata))


def _govde(donemler, degerler):
    return {"series": {"docs": [{"period": donemler, "value": degerler}]}}


# ---------------------------------------------------- dogrulama kurali
def test_dogrulanmamis_kod_TAHMIN_EDILMEZ():
    """Modulun tek kurali. Tahmini eslesme sessizce yanlis makro beslerdi."""
    for kod in ("M2SL", "WTREGEN", "RRPONTSYD", "SP500", "YOKBOYLE"):
        with pytest.raises(DBnomicsHatasi) as e:
            asyncio.run(dbnomics.seri_getir(kod))
        assert "DOGRULANMIS" in str(e.value)


def test_tabloda_yalnizca_kanitli_eslesme_var():
    """Kanit alani ZORUNLU; kanitsiz eslesme eklenmis olmamali."""
    for kod, esl in dbnomics.DOGRULANMIS_ESLESME.items():
        d = esl.get("dogrulama")
        assert d, f"{kod}: dogrulama kaniti yok"
        assert d.get("ortak_gozlem", 0) >= 2, f"{kod}: yetersiz ortak gozlem"
        assert d.get("azami_fark_yuzde") is not None
        assert d["azami_fark_yuzde"] < 0.01, (
            f"{kod}: fark cok buyuk, dogrulanmis sayilamaz")
        assert d.get("yontem"), f"{kod}: dogrulama yontemi yazilmamis"


def test_m2_tabloya_ALINMAMIS():
    """M2 olculdu ve BIREBIR ESLESMEDI (surum farki) - girmemeli."""
    assert "M2SL" not in dbnomics.DOGRULANMIS_ESLESME
    assert "M2" not in dbnomics.DOGRULANMIS_ESLESME


def test_tga_ve_rrp_tabloya_ALINMAMIS():
    """258 seri deger uzerinden tarandi, eslesen bulunamadi."""
    assert "WTREGEN" not in dbnomics.DOGRULANMIS_ESLESME
    assert "RRPONTSYD" not in dbnomics.DOGRULANMIS_ESLESME


def test_walcl_dogrulanmis():
    e = dbnomics.DOGRULANMIS_ESLESME["WALCL"]
    assert e["yol"] == "FED/H41/RESPPA_N.WW"
    assert e["dogrulama"]["azami_fark_yuzde"] == 0.0


# ------------------------------------------------------------- cekme
def test_gozlemler_ayiklanir(monkeypatch):
    _kur(monkeypatch, _Yanit(200, _govde(
        ["2026-08-05", "2026-08-12"], [6748567.0, 6759955.0])))
    s = asyncio.run(dbnomics.seri_getir("WALCL"))
    assert s == [("2026-08-05", 6748567.0), ("2026-08-12", 6759955.0)]


def test_kucuk_harf_kod_kabul_edilir(monkeypatch):
    _kur(monkeypatch, _Yanit(200, _govde(["2026-08-05"], [1.0])))
    assert asyncio.run(dbnomics.seri_getir("walcl")) == [("2026-08-05", 1.0)]


def test_eksik_gozlem_SIFIR_YAPILMAZ(monkeypatch):
    """None'i 0 yapmak zaman serisini sessizce bozardi."""
    _kur(monkeypatch, _Yanit(200, _govde(
        ["2026-08-05", "2026-08-12", "2026-08-19"], [100.0, None, 300.0])))
    s = asyncio.run(dbnomics.seri_getir("WALCL"))
    assert s == [("2026-08-05", 100.0), ("2026-08-19", 300.0)]
    assert all(v != 0.0 for _, v in s)


def test_ag_hatasi_yukselir(monkeypatch):
    _kur(monkeypatch, hata=OSError("ag yok"))
    with pytest.raises(DBnomicsHatasi) as e:
        asyncio.run(dbnomics.seri_getir("WALCL"))
    assert "ulasilamadi" in str(e.value)


def test_http_hatasi_yukselir(monkeypatch):
    _kur(monkeypatch, _Yanit(503))
    with pytest.raises(DBnomicsHatasi) as e:
        asyncio.run(dbnomics.seri_getir("WALCL"))
    assert "503" in str(e.value)


def test_bozuk_json_yukselir(monkeypatch):
    _kur(monkeypatch, _Yanit(200, patlat=True))
    with pytest.raises(DBnomicsHatasi):
        asyncio.run(dbnomics.seri_getir("WALCL"))


def test_bos_sonuc_BOS_LISTE_DEGIL_hata(monkeypatch):
    """Bos liste 'veri yok' ile karisirdi."""
    _kur(monkeypatch, _Yanit(200, {"series": {"docs": []}}))
    with pytest.raises(DBnomicsHatasi) as e:
        asyncio.run(dbnomics.seri_getir("WALCL"))
    assert "bos sonuc" in str(e.value)


def test_sema_degisirse_hata(monkeypatch):
    """period/value uzunluklari uyusmuyorsa sessizce kirpilmaz."""
    _kur(monkeypatch, _Yanit(200, _govde(["a", "b", "c"], [1.0, 2.0])))
    with pytest.raises(DBnomicsHatasi) as e:
        asyncio.run(dbnomics.seri_getir("WALCL"))
    assert "sema degismis" in str(e.value)


def test_eslesme_durumu_kaniti_tasir():
    d = dbnomics.eslesme_durumu()
    assert d["dogrulanmis_seri_sayisi"] == len(dbnomics.DOGRULANMIS_ESLESME)
    assert "ANAHTARI GEREKTIRMEZ" in d["kaynak"]
    assert d["eslesmeler"]["WALCL"]["dogrulama"]["ortak_gozlem"] == 6
