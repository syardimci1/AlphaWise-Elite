"""
FRED -> DBnomics ANAHTARSIZ YEDEK BAGLANTISI TESTLERI (madde 44, 10.09.2026).

Bu dosya AG CAGRISI YAPMAZ - hem FRED hem DBnomics yollari yamalanir.
Onbellek de yamalanir (Redis'e bagimli olmasin).
"""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import dbnomics, fred_client  # noqa: E402


@pytest.fixture(autouse=True)
def _temiz(monkeypatch):
    """Her testte onbellek KAPALI ve yedek kaydi TEMIZ baslasin."""
    monkeypatch.setattr(fred_client, "_cache_get", lambda k: None)
    monkeypatch.setattr(fred_client, "_cache_set", lambda k, v, ttl_seconds=0: None)
    monkeypatch.setattr(fred_client, "YEDEK_ETKIN", True)
    fred_client._yedek_kullanimi.clear()
    yield
    fred_client._yedek_kullanimi.clear()


def _kos(coro):
    return asyncio.run(coro)


FRED_VERISI = [("2026-08-26", 6730912.0), ("2026-09-02", 6737204.0),
               ("2026-09-09", 6740619.0)]
# DBnomics TUM seriyi dondurur (2002'den beri) - suzgec testi icin eski
# tarihler bilerek eklendi.
DBNOMICS_HAM = [("2002-12-18", 719000.0), ("2019-01-02", 4058000.0),
                ("2026-08-26", 6730912.0), ("2026-09-02", 6737204.0)]


# =====================================================================
# 1. NORMAL YOL DEGISMEDI
# =====================================================================
class TestNormalYol:
    def test_FRED_CALISIRKEN_YEDEGE_HIC_DOKUNULMAZ(self, monkeypatch):
        cagrildi = {"dbnomics": 0}

        async def _fred(sid, sd):
            return list(FRED_VERISI)

        async def _dbn(sid):
            cagrildi["dbnomics"] += 1
            return list(DBNOMICS_HAM)

        monkeypatch.setattr(fred_client, "_fred_serisi_cek", _fred)
        monkeypatch.setattr(dbnomics, "seri_getir", _dbn)
        sonuc = _kos(fred_client.fetch_series("WALCL", "2020-01-01"))
        assert sonuc == FRED_VERISI
        assert cagrildi["dbnomics"] == 0, "FRED calisirken DBnomics cagrildi"
        assert fred_client._yedek_kullanimi == {}

    def test_FRED_DUZELINCE_YEDEK_KAYDI_TEMIZLENIR(self, monkeypatch):
        fred_client._yedek_kullanimi["WALCL"] = {"kaynak": "dbnomics"}

        async def _fred(sid, sd):
            return list(FRED_VERISI)

        monkeypatch.setattr(fred_client, "_fred_serisi_cek", _fred)
        _kos(fred_client.fetch_series("WALCL"))
        assert "WALCL" not in fred_client._yedek_kullanimi


# =====================================================================
# 2. YEDEK DEVREYE GIRIYOR MU
# =====================================================================
class TestYedekDevreye:
    def _fred_patlat(self, monkeypatch, hata=RuntimeError("FRED_API_KEY tanimli degil")):
        async def _fred(sid, sd):
            raise hata

        monkeypatch.setattr(fred_client, "_fred_serisi_cek", _fred)

    def test_ANAHTAR_YOKKEN_YEDEK_VERI_DONER(self, monkeypatch):
        self._fred_patlat(monkeypatch)

        async def _dbn(sid):
            return list(DBNOMICS_HAM)

        monkeypatch.setattr(dbnomics, "seri_getir", _dbn)
        sonuc = _kos(fred_client.fetch_series("WALCL", "2020-01-01"))
        assert sonuc, "yedekten veri gelmedi"
        assert fred_client._yedek_kullanimi["WALCL"]["kaynak"] == "dbnomics"

    def test_HTTP_HATASINDA_DA_YEDEK_DEVREYE_GIRER(self, monkeypatch):
        self._fred_patlat(monkeypatch, RuntimeError("FRED HTTP 503"))

        async def _dbn(sid):
            return list(DBNOMICS_HAM)

        monkeypatch.setattr(dbnomics, "seri_getir", _dbn)
        assert _kos(fred_client.fetch_series("WALCL", "2020-01-01"))
        assert "503" in fred_client._yedek_kullanimi["WALCL"]["fred_hatasi"]

    def test_START_DATE_SUZGECI_UYGULANIR(self, monkeypatch):
        """DBnomics TUM seriyi dondurur; FRED observation_start ile suzer.
        Suzmezsek asagi akis, FRED yolunda HIC gormedigi bir pencereyle
        calisirdi."""
        self._fred_patlat(monkeypatch)

        async def _dbn(sid):
            return list(DBNOMICS_HAM)

        monkeypatch.setattr(dbnomics, "seri_getir", _dbn)
        sonuc = _kos(fred_client.fetch_series("WALCL", "2020-01-01"))
        assert all(t >= "2020-01-01" for t, _ in sonuc)
        assert ("2002-12-18", 719000.0) not in sonuc
        assert ("2019-01-02", 4058000.0) not in sonuc
        assert len(sonuc) == 2

    def test_SONUC_TARIHE_GORE_SIRALI(self, monkeypatch):
        self._fred_patlat(monkeypatch)

        async def _dbn(sid):
            return list(reversed(DBNOMICS_HAM))

        monkeypatch.setattr(dbnomics, "seri_getir", _dbn)
        sonuc = _kos(fred_client.fetch_series("WALCL", "2020-01-01"))
        assert [t for t, _ in sonuc] == sorted(t for t, _ in sonuc)


# =====================================================================
# 3. YEDEK MASKELEMEZ - ORIJINAL FRED HATASI KORUNUR
# =====================================================================
class TestMaskelemez:
    def test_DOGRULANMAMIS_SERIDE_ORIJINAL_FRED_HATASI_FIRLAR(self, monkeypatch):
        """M2SL'in DBnomics eslesmesi DOGRULANMADI (degerler farkli cikti).
        Yedek burada TAHMIN YAPMAMALI; cagiran taraf FRED hatasini
        gormeli - cunku kok neden FRED'dir."""
        ozgun = RuntimeError("FRED HTTP 429")

        async def _fred(sid, sd):
            raise ozgun

        monkeypatch.setattr(fred_client, "_fred_serisi_cek", _fred)
        with pytest.raises(RuntimeError) as e:
            _kos(fred_client.fetch_series("M2SL", "2020-01-01"))
        assert "FRED HTTP 429" in str(e.value)
        assert "M2SL" not in fred_client._yedek_kullanimi

    def test_YEDEK_DE_PATLARSA_FRED_HATASI_FIRLAR(self, monkeypatch):
        ozgun = RuntimeError("FRED HTTP 500")

        async def _fred(sid, sd):
            raise ozgun

        async def _dbn(sid):
            raise dbnomics.DBnomicsHatasi("DBnomics HTTP 502")

        monkeypatch.setattr(fred_client, "_fred_serisi_cek", _fred)
        monkeypatch.setattr(dbnomics, "seri_getir", _dbn)
        with pytest.raises(RuntimeError) as e:
            _kos(fred_client.fetch_series("WALCL", "2020-01-01"))
        assert "FRED HTTP 500" in str(e.value), "yedegin hatasi FRED'inkini maskeledi"

    def test_YEDEK_KAPALIYKEN_FRED_HATASI_AYNEN_FIRLAR(self, monkeypatch):
        monkeypatch.setattr(fred_client, "YEDEK_ETKIN", False)
        cagrildi = {"dbnomics": 0}

        async def _fred(sid, sd):
            raise RuntimeError("FRED HTTP 500")

        async def _dbn(sid):
            cagrildi["dbnomics"] += 1
            return list(DBNOMICS_HAM)

        monkeypatch.setattr(fred_client, "_fred_serisi_cek", _fred)
        monkeypatch.setattr(dbnomics, "seri_getir", _dbn)
        with pytest.raises(RuntimeError):
            _kos(fred_client.fetch_series("WALCL"))
        assert cagrildi["dbnomics"] == 0


# =====================================================================
# 4. GORUNURLUK - YEDEK SESSIZ DEVREYE GIRMEZ
# =====================================================================
class TestGorunurluk:
    def test_YEDEK_DURUMU_SEMASI(self):
        d = fred_client.yedek_durumu()
        assert d["kullanilabilir"] is True
        assert d["dogrulanmis_seriler"] == ["WALCL"]
        assert d["onbellek_saniye"] == fred_client.YEDEK_ONBELLEK_SANIYE
        assert "BIRINCIL" in d["not"]

    def test_YEDEK_ONBELLEGI_FRED_ONBELLEGINDEN_KISA(self):
        """FRED duzelir duzelmez birincil kaynaga donulsun diye yedek
        verisi 6 saat DEGIL, daha kisa sure tutulur."""
        assert fred_client.YEDEK_ONBELLEK_SANIYE < 6 * 3600

    def test_KULLANIM_KAYDI_FRED_HATASINI_TASIR(self, monkeypatch):
        async def _fred(sid, sd):
            raise RuntimeError("FRED_API_KEY tanimli degil")

        async def _dbn(sid):
            return list(DBNOMICS_HAM)

        monkeypatch.setattr(fred_client, "_fred_serisi_cek", _fred)
        monkeypatch.setattr(dbnomics, "seri_getir", _dbn)
        _kos(fred_client.fetch_series("WALCL", "2020-01-01"))
        kayit = fred_client.yedek_durumu()["son_kullanim"]["WALCL"]
        assert "FRED_API_KEY" in kayit["fred_hatasi"]
        assert kayit["gozlem"] == 2


# =====================================================================
# 5. DOGRULANMIS ESLESME TABLOSU KORUNUYOR MU
# =====================================================================
def test_YALNIZCA_DOGRULANMIS_SERI_TABLODA():
    """Kanit alani olmayan bir eslesme tabloya GIRMEMELI."""
    for kod, esl in dbnomics.DOGRULANMIS_ESLESME.items():
        assert "dogrulama" in esl, kod
        assert esl["dogrulama"]["ortak_gozlem"] > 0, kod
        assert esl["dogrulama"]["azami_fark_yuzde"] == 0.0, kod
    assert "M2SL" not in dbnomics.DOGRULANMIS_ESLESME
