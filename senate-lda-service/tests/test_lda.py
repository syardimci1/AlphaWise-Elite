"""
SENATE LDA SERVISI TESTLERI (20.09.2026, madde 35).

congress-trading-service/tests/test_equibles.py ile AYNI desen: httpx
monkeypatch ile yamanir, Redis sahte bellek-ici sozlukle degistirilir,
main.py FastAPI TestClient ile CALISTIRILMAZ (agir bagimlilik, bu
depoda hic kullanilmiyor) - is mantigi resolver seviyesinde test edilir.

GERCEK ORNEK (20.09.2026, kullanicinin KENDI taraycisindan/agindan
cektigi CANLI yanit - bu ortamin araclari lda.gov'a Akamai bot-korumasi
yuzunden ULASAMIYOR, bu yuzden ornegi CANLI CEKEMEDIM, kullanicidan
ALINDI). Ucuncu taraf scraper'larin (Apify/dltHub) iddia ettigi
camelCase alan adlari (filingUuid, incomeUsd) bu ornekte YANLIS cikti -
gercek API snake_case donuyor.
"""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import resolver  # noqa: E402


def _kos(coro):
    return asyncio.run(coro)


class _SahteRedis:
    def __init__(self):
        self.veri = {}

    def get(self, k):
        return self.veri.get(k)

    def setex(self, k, ttl, v):
        self.veri[k] = v

    def incr(self, k):
        self.veri[k] = str(int(self.veri.get(k, 0)) + 1)
        return int(self.veri[k])

    def expire(self, k, ttl):
        pass

    def pipeline(self):
        return _SahtePipeline(self)

    def ping(self):
        return True


class _SahtePipeline:
    def __init__(self, redis):
        self.redis = redis
        self.komutlar = []

    def incr(self, k):
        self.komutlar.append(("incr", k))
        return self

    def expire(self, k, ttl):
        return self

    def execute(self):
        for komut in self.komutlar:
            if komut[0] == "incr":
                self.redis.incr(komut[1])


class _SahteYanit:
    def __init__(self, status_code, govde=None, metin=""):
        self.status_code = status_code
        self._govde = govde
        self.text = metin

    def json(self):
        return self._govde


class _SahteAsyncClient:
    def __init__(self, yanit_uretici, **kw):
        self._yanit_uretici = yanit_uretici

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, params=None, headers=None):
        return self._yanit_uretici(url, params, headers)


@pytest.fixture(autouse=True)
def _temiz_ortam(monkeypatch):
    sahte = _SahteRedis()
    monkeypatch.setattr(resolver, "_redis_client", sahte)
    monkeypatch.setattr(resolver, "_get_redis", lambda: sahte)
    monkeypatch.delenv("LDA_KEY", raising=False)
    yield


# GERCEK canli yanit (20.09.2026, kullanicidan alindi, filing_uuid
# 455edc06-55d1-41ed-878e-70a4040f953c) - TAM ORIJINAL, kirpilmadi.
GERCEK_FILING_ORNEGI = {
    "url": "https://lda.gov/api/v1/filings/455edc06-55d1-41ed-878e-70a4040f953c/?format=json",
    "filing_uuid": "455edc06-55d1-41ed-878e-70a4040f953c",
    "filing_type": "MM",
    "filing_type_display": "Mid-Year Report",
    "filing_year": 1999,
    "filing_period": "mid_year",
    "filing_period_display": "Mid-Year (Jan 1 - Jun 30)",
    "filing_document_url": "https://lda.gov/filings/public/filing/455edc06-55d1-41ed-878e-70a4040f953c/print/",
    "filing_document_content_type": "application/pdf",
    "income": None,
    "expenses": None,
    "expenses_method": None,
    "posted_by_name": None,
    "dt_posted": "1905-06-24T00:00:00-05:00",
    "termination_date": None,
    "registrant": {
        "id": 9181,
        "name": "CHURCHILL GROUP",
        "city": "HUNTSVILLE",
        "state": "AL",
    },
    "client": {
        "id": 113256,
        "name": "AMERICAN FAMILY BUSINESS INST",
        "state": "AL",
        "effective_date": "1996-02-14",
    },
    "lobbying_activities": [
        {
            "general_issue_code": "TAX",
            "general_issue_code_display": "Taxation/Internal Revenue Code",
            "description": None,
            "lobbyists": [{"lobbyist": {"id": 361, "first_name": "WAYNE",
                                        "last_name": "PARKER"},
                          "covered_position": "N/A"}],
            "government_entities": [{"id": 2, "name": "HOUSE OF REPRESENTATIVES"},
                                    {"id": 1, "name": "SENATE"}],
        }
    ],
    "conviction_disclosures": [],
    "foreign_entities": [],
    "affiliated_organizations": [],
}


# ============================================== 1. NORMALLESTIRME
class TestNormallestirme:
    def test_temel_alanlar_dogru_esleniyor(self):
        n = resolver._normalize_filing(GERCEK_FILING_ORNEGI)
        assert n["filing_uuid"] == "455edc06-55d1-41ed-878e-70a4040f953c"
        assert n["filing_turu"] == "Mid-Year Report"
        assert n["filing_yili"] == 1999
        assert n["donem"] == "Mid-Year (Jan 1 - Jun 30)"

    def test_ic_ice_nesnelerden_isim_cikariliyor(self):
        """registrant/client duz string DEGIL, ic ice nesne - .name'den okunmali."""
        n = resolver._normalize_filing(GERCEK_FILING_ORNEGI)
        assert n["lobici_firma"] == "CHURCHILL GROUP"
        assert n["musteri"] == "AMERICAN FAMILY BUSINESS INST"
        assert n["musteri_eyalet"] == "AL"

    def test_null_gelir_gider_UYDURULMAZ(self):
        """income/expenses gercekte None olabilir - sahte 0 YAZILMAZ."""
        n = resolver._normalize_filing(GERCEK_FILING_ORNEGI)
        assert n["gelir_usd"] is None
        assert n["gider_usd"] is None

    def test_konular_listesi_dogru_cikariliyor(self):
        n = resolver._normalize_filing(GERCEK_FILING_ORNEGI)
        assert len(n["konular"]) == 1
        assert n["konular"][0]["kod"] == "TAX"
        assert n["konular"][0]["aciklama"] == "Taxation/Internal Revenue Code"

    def test_konu_YOKSA_bos_liste_doner_hata_vermez(self):
        kayit = {**GERCEK_FILING_ORNEGI, "lobbying_activities": []}
        n = resolver._normalize_filing(kayit)
        assert n["konular"] == []

    def test_registrant_client_EKSIKSE_PATLAMAZ(self):
        kayit = {"filing_uuid": "x"}
        n = resolver._normalize_filing(kayit)
        assert n["lobici_firma"] is None
        assert n["musteri"] is None


# ============================================== 2. KOTA (DAKIKALIK)
class TestKota:
    def test_anahtar_yoksa_istek_ATILMAZ(self):
        veri, meta, hata = _kos(resolver.filings_cek(client_name="X"))
        assert veri is None
        assert "LDA_KEY" in hata["neden"]

    def test_kota_asilinca_istek_ATILMAZ(self, monkeypatch):
        monkeypatch.setenv("LDA_KEY", "test-key")
        sahte = resolver._get_redis()
        sahte.veri[resolver._dakika_anahtari()] = str(
            resolver.LDA_DAKIKA_LIMIT - resolver.LDA_GUVENLIK_PAYI)
        veri, meta, hata = _kos(resolver.filings_cek(client_name="X"))
        assert veri is None
        assert hata["kota_asimi"] is True

    def test_basarili_cagri_dakika_sayacini_ARTIRIR(self, monkeypatch):
        monkeypatch.setenv("LDA_KEY", "test-key")
        monkeypatch.setattr(resolver.httpx, "AsyncClient",
                            lambda **kw: _SahteAsyncClient(
                                lambda u, p, h: _SahteYanit(200, {"results": [], "count": 0})))
        _kos(resolver.filings_cek(client_name="X"))
        anahtar = resolver._dakika_anahtari()
        assert resolver._get_redis().veri.get(anahtar) == "1"


# ============================================== 3. HTTP ISTEK PARAMETRELERI
class TestIstekParametreleri:
    def test_client_name_dogru_parametre_olarak_GIDER(self, monkeypatch):
        monkeypatch.setenv("LDA_KEY", "k")
        yakalanan = {}

        def yanit_uret(url, params, headers):
            yakalanan.update(params or {})
            yakalanan["headers"] = headers
            return _SahteYanit(200, {"results": [], "count": 0})

        monkeypatch.setattr(resolver.httpx, "AsyncClient",
                            lambda **kw: _SahteAsyncClient(yanit_uret))
        _kos(resolver.filings_cek(client_name="AMAZON", filing_year=2026))
        assert yakalanan["client_name"] == "AMAZON"
        assert yakalanan["filing_year"] == 2026
        assert yakalanan["headers"]["Authorization"] == "Token k"

    def test_registrant_name_dogru_parametre_olarak_GIDER(self, monkeypatch):
        monkeypatch.setenv("LDA_KEY", "k")
        yakalanan = {}

        def yanit_uret(url, params, headers):
            yakalanan.update(params or {})
            return _SahteYanit(200, {"results": [], "count": 0})

        monkeypatch.setattr(resolver.httpx, "AsyncClient",
                            lambda **kw: _SahteAsyncClient(yanit_uret))
        _kos(resolver.filings_cek(registrant_name="CHURCHILL GROUP"))
        assert yakalanan["registrant_name"] == "CHURCHILL GROUP"
        assert "client_name" not in yakalanan


# ============================================== 4. HTTP HATA KODLARI
class TestHataKodlari:
    def test_429_kota_asimi_olarak_ISARETLENIR(self, monkeypatch):
        monkeypatch.setenv("LDA_KEY", "k")
        monkeypatch.setattr(resolver.httpx, "AsyncClient",
                            lambda **kw: _SahteAsyncClient(
                                lambda u, p, h: _SahteYanit(429, metin="Too Many Requests")))
        veri, meta, hata = _kos(resolver.filings_cek(client_name="X"))
        assert veri is None
        assert hata["http_status"] == 429

    def test_403_genel_hata_olarak_DONER(self, monkeypatch):
        monkeypatch.setenv("LDA_KEY", "k")
        monkeypatch.setattr(resolver.httpx, "AsyncClient",
                            lambda **kw: _SahteAsyncClient(
                                lambda u, p, h: _SahteYanit(403, metin="Forbidden")))
        veri, meta, hata = _kos(resolver.filings_cek(client_name="X"))
        assert veri is None
        assert hata["http_status"] == 403


# ============================================== 5. ONBELLEK
class TestOnbellek:
    def test_ikinci_cagrida_AG_ISTEGI_YOK(self, monkeypatch):
        monkeypatch.setenv("LDA_KEY", "k")
        cagri_sayisi = {"n": 0}

        def yanit_uret(url, params, headers):
            cagri_sayisi["n"] += 1
            return _SahteYanit(200, {"results": [GERCEK_FILING_ORNEGI], "count": 1})

        monkeypatch.setattr(resolver.httpx, "AsyncClient",
                            lambda **kw: _SahteAsyncClient(yanit_uret))

        r1 = _kos(resolver.musteri_filings_getir("AMERICAN FAMILY BUSINESS INST"))
        r2 = _kos(resolver.musteri_filings_getir("AMERICAN FAMILY BUSINESS INST"))

        assert cagri_sayisi["n"] == 1
        assert r1["cache_hit"] is False
        assert r2["cache_hit"] is True
        assert r2["records"] == r1["records"]

    def test_hatali_yanit_ONBELLEKLENMEZ(self, monkeypatch):
        """Basarisiz bir cagriyi onbelleklemek, gecici bir hatayi
        saatlerce 'sonuc yok' olarak dondurmek demektir - YAPILMAZ."""
        monkeypatch.setenv("LDA_KEY", "k")
        cagri_sayisi = {"n": 0}

        def yanit_uret(url, params, headers):
            cagri_sayisi["n"] += 1
            return _SahteYanit(500, metin="Internal Server Error")

        monkeypatch.setattr(resolver.httpx, "AsyncClient",
                            lambda **kw: _SahteAsyncClient(yanit_uret))

        _kos(resolver.musteri_filings_getir("X"))
        _kos(resolver.musteri_filings_getir("X"))
        assert cagri_sayisi["n"] == 2


# ============================================== 6. ANAHTAR/REDIS DURUMU
def test_anahtar_durumu_dogru_bildiriyor(monkeypatch):
    monkeypatch.delenv("LDA_KEY", raising=False)
    assert resolver.anahtar_durumu()["LDA_KEY"] is False
    monkeypatch.setenv("LDA_KEY", "k")
    assert resolver.anahtar_durumu()["LDA_KEY"] is True
