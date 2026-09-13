"""
EQUIBLES TAMAMLAYICI KAYNAK TESTLERI (13.09.2026).

Kaynak: madde 52 - Equibles hosted REST API (api.equibles.com), Quiver+FMP
zincirinin ucuncu (TAMAMLAYICI) katmani. GRUP2 denetiminde MIMARI-CIKAR
kararli daniel3303/Equibles (self-hosted .NET) ile AYNI ISIMDE ama TAMAMEN
AYRI bir urun - o karar burada DEGISMEDI, yeni container KURULMADI.

Bu dosya AG CAGRISI YAPMAZ: httpx.AsyncClient monkeypatch ile yamanir,
Redis de sahte bir bellek-ici sozlukle degistirilir.
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
    """resolver._get_redis()'in yerini alir - gercek Redis'e HIC dokunmaz."""

    def __init__(self):
        self.veri = {}

    def get(self, k):
        return self.veri.get(k)

    def set(self, k, v, ex=None):
        self.veri[k] = str(v)

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

    def incrby(self, k, n):
        self.komutlar.append(("incrby", k, n))
        return self

    def expire(self, k, ttl):
        return self

    def set(self, k, v, ex=None):
        self.komutlar.append(("set", k, v))
        return self

    def execute(self):
        for komut in self.komutlar:
            if komut[0] == "incr":
                self.redis.incr(komut[1])
            elif komut[0] == "incrby":
                self.redis.veri[komut[1]] = str(
                    int(self.redis.veri.get(komut[1], 0)) + komut[2])
            elif komut[0] == "set":
                self.redis.set(komut[1], komut[2])


@pytest.fixture(autouse=True)
def _temiz_ortam(monkeypatch):
    """Her testte: sahte Redis + gercek anahtar/kota sifirlanmis baslar."""
    sahte = _SahteRedis()
    monkeypatch.setattr(resolver, "_redis_client", sahte)
    monkeypatch.setattr(resolver, "_get_redis", lambda: sahte)
    monkeypatch.delenv("EQUIBLES_API_KEY", raising=False)
    yield


# GERCEK canli yanittan (13.09.2026, NVDA sorgusu, anahtar dogrulama sirasinda
# OLCULDU) - dokumantasyon ORNEGINDEKI alan adlarindan (member/chamber/asset/
# amountRange) FARKLI cikti; bkz. resolver._equibles_normalize() basligi.
EQUIBLES_ORNEK_SATIR = {
    "transactionDate": "2026-08-13",
    "filingDate": "2026-09-02",
    "ticker": "NVDA",
    "memberId": "03174cad-6a32-4d40-9e57-a740fe516ed1",
    "memberName": "Sheldon Whitehouse",
    "memberPosition": "Senator",
    "transactionType": "Sale",
    "assetName": "NVIDIA Corporation - Common Stock",
    "assetType": "Stock",
    "subholding": "",
    "ownerType": "Self",
    "amountFrom": 15001,
    "amountTo": 50000,
}


class _SahteYanit:
    def __init__(self, status_code, gövde=None, metin="", headers=None):
        self.status_code = status_code
        self._govde = gövde
        self.text = metin
        self.headers = headers or {}

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


# =====================================================================
# 1. NORMALLESTIRME - Equibles semasi ortak semaya DOGRU cevriliyor mu
# =====================================================================
class TestNormallestirme:
    def test_EQUIBLES_SATIRI_ORTAK_SEMAYA_CEVRILIR(self):
        n = resolver._equibles_normalize(EQUIBLES_ORNEK_SATIR)
        assert n["source"] == "equibles"
        assert n["member"] == "Sheldon Whitehouse"
        assert n["chamber"] == "Senate"
        assert n["ticker"] == "NVDA"
        assert n["transaction_type"] == "Sale"
        assert n["transaction_date"] == "2026-08-13"
        assert n["disclosure_date"] == "2026-09-02"
        assert n["member_id"] == "03174cad-6a32-4d40-9e57-a740fe516ed1"

    def test_TUTAR_ZATEN_SAYISAL_GELIR_METIN_AYRISTIRMA_GEREKMEZ(self):
        """Equibles Quiver/FMP'nin AKSINE tutari amountFrom/amountTo diye
        SAYISAL tam sayi olarak verir - _tutar_ayristir() burada
        CAGRILMAZ (metin ayristirmaya gerek yok)."""
        n = resolver._equibles_normalize(EQUIBLES_ORNEK_SATIR)
        assert n["amount_min_usd"] == 15001
        assert n["amount_max_usd"] == 50000
        assert n["amount_mid_usd"] == pytest.approx(32500.5)
        assert n["amount_range"] == "$15,001-$50,000"

    def test_HOUSE_MECLISI_DOGRU_TANINIR(self):
        """DIKKAT: gercek API 'chamber' DEGIL 'memberPosition' alanini
        kullanir ('Representative'/'Senator') - House/Senate metnine
        BURADA cevrilir."""
        satir = dict(EQUIBLES_ORNEK_SATIR, memberPosition="Representative")
        assert resolver._equibles_normalize(satir)["chamber"] == "House"

    def test_SENATOR_SENATE_YE_CEVRILIR(self):
        assert resolver._equibles_normalize(EQUIBLES_ORNEK_SATIR)["chamber"] == "Senate"

    def test_SUBHOLDING_YORUM_ALANINA_TASINIR(self):
        """subholding (araci/emeklilik hesabi) ortak semadaki 'comment'
        alaninin GERCEK karsiligidir - dokumantasyon 'account' diyordu,
        canlida boyle bir alan YOKTU."""
        satir = dict(EQUIBLES_ORNEK_SATIR, subholding="Merrill Lynch SEP IRA")
        assert resolver._equibles_normalize(satir)["comment"] == "Merrill Lynch SEP IRA"

    def test_BOS_SUBHOLDING_NONE_OLUR(self):
        satir = dict(EQUIBLES_ORNEK_SATIR, subholding="")
        assert resolver._equibles_normalize(satir)["comment"] is None

    def test_OWNERTYPE_OWNER_ALANINA_TASINIR(self):
        assert resolver._equibles_normalize(EQUIBLES_ORNEK_SATIR)["owner"] == "Self"
        bos = dict(EQUIBLES_ORNEK_SATIR, ownerType="")
        assert resolver._equibles_normalize(bos)["owner"] is None

    def test_TICKER_BUYUK_HARFE_CEVRILIR(self):
        satir = dict(EQUIBLES_ORNEK_SATIR, ticker="nvda")
        assert resolver._equibles_normalize(satir)["ticker"] == "NVDA"

    def test_QUIVER_ve_FMP_normalizerlari_DA_source_ALANI_TASIR(self):
        """Uc kaynagi tek listede birlestirince provenance KAYBOLMAMALI."""
        fmp = resolver._fmp_normalize({"firstName": "A", "lastName": "B"}, "Senate")
        assert fmp["source"] == "fmp"
        quiver = resolver._quiver_normalize({"Representative": "C"})
        assert quiver["source"] == "quiver"


# =====================================================================
# 2. ANAHTAR YOKSA - AG CAGRISI HIC YAPILMAZ
# =====================================================================
class TestAnahtarsizDavranis:
    def test_ANAHTAR_TANIMSIZKEN_AG_CAGRISI_YAPILMAZ(self, monkeypatch):
        cagrildi = {"n": 0}

        def patlarsa_yakala(*a, **kw):
            cagrildi["n"] += 1
            raise AssertionError("AG CAGRISI YAPILDI - anahtar yokken YAPILMAMALIYDI")

        monkeypatch.setattr(resolver.httpx, "AsyncClient", patlarsa_yakala)
        kayitlar, hata = _kos(resolver.equibles_ticker_cek("NVDA"))
        assert kayitlar is None
        assert "EQUIBLES_API_KEY" in hata["neden"]
        assert cagrildi["n"] == 0

    def test_anahtar_durumu_UC_ANAHTARI_DA_BILDIRIR(self, monkeypatch):
        monkeypatch.setenv("EQUIBLES_API_KEY", "eq_test")
        d = resolver.anahtar_durumu()
        assert d["EQUIBLES_API_KEY"] is True
        assert "EQUIBLES_API_KEY" not in d["eksik"]


# =====================================================================
# 3. BASARILI CAGRI - GERCEK ISTEK BICIMI DOGRU MU
# =====================================================================
class TestBasariliCagri:
    def test_DOGRU_URL_HEADER_VE_PARAMETRELERLE_CAGRILIR(self, monkeypatch):
        monkeypatch.setenv("EQUIBLES_API_KEY", "eq_test_anahtari")
        yakalanan = {}

        def yanit_uretici(url, params, headers):
            yakalanan["url"] = url
            yakalanan["params"] = params
            yakalanan["headers"] = headers
            return _SahteYanit(200, {"data": [EQUIBLES_ORNEK_SATIR]},
                               headers={"X-RateLimit-Remaining": "97"})

        monkeypatch.setattr(resolver.httpx, "AsyncClient",
                            lambda **kw: _SahteAsyncClient(yanit_uretici, **kw))
        kayitlar, hata = _kos(resolver.equibles_ticker_cek("nvda", limit=25))
        assert hata is None
        assert len(kayitlar) == 1
        assert kayitlar[0]["source"] == "equibles"
        assert yakalanan["url"] == f"{resolver.EQUIBLES_BASE}/congress/trades"
        assert yakalanan["params"] == {"ticker": "NVDA", "limit": 25}
        assert yakalanan["headers"]["Authorization"] == "Bearer eq_test_anahtari"

    def test_BASARILI_CAGRI_YEREL_SAYACI_ARTIRIR(self, monkeypatch):
        monkeypatch.setenv("EQUIBLES_API_KEY", "eq_test")

        def yanit_uretici(url, params, headers):
            return _SahteYanit(200, {"data": []}, headers={"X-RateLimit-Remaining": "99"})

        monkeypatch.setattr(resolver.httpx, "AsyncClient",
                            lambda **kw: _SahteAsyncClient(yanit_uretici, **kw))
        oncesi = resolver.equibles_kota_durumu()["yerel_sayac_kullanilan"]
        _kos(resolver.equibles_ticker_cek("AAPL"))
        sonrasi = resolver.equibles_kota_durumu()["yerel_sayac_kullanilan"]
        assert sonrasi == oncesi + 1


# =====================================================================
# 4. HATA YONETIMI - Quiver/FMP ILE AYNI SOZLESME (fail-open, tuple)
# =====================================================================
class TestHataYonetimi:
    def test_401_DONERSE_HATA_SOZLUGU_DONER_ISTISNA_FIRLAMAZ(self, monkeypatch):
        monkeypatch.setenv("EQUIBLES_API_KEY", "eq_gecersiz")

        def yanit_uretici(url, params, headers):
            return _SahteYanit(401, metin="Unauthorized")

        monkeypatch.setattr(resolver.httpx, "AsyncClient",
                            lambda **kw: _SahteAsyncClient(yanit_uretici, **kw))
        kayitlar, hata = _kos(resolver.equibles_ticker_cek("NVDA"))
        assert kayitlar is None
        assert hata["http_status"] == 401

    def test_429_SUNUCU_LIMITI_HATA_OLARAK_ISARETLENIR(self, monkeypatch):
        monkeypatch.setenv("EQUIBLES_API_KEY", "eq_test")

        def yanit_uretici(url, params, headers):
            return _SahteYanit(429, metin="rate_limited")

        monkeypatch.setattr(resolver.httpx, "AsyncClient",
                            lambda **kw: _SahteAsyncClient(yanit_uretici, **kw))
        kayitlar, hata = _kos(resolver.equibles_ticker_cek("NVDA"))
        assert kayitlar is None
        assert hata["http_status"] == 429

    def test_BAGLANTI_ISTISNASI_YUTULUR_PATLAMAZ(self, monkeypatch):
        monkeypatch.setenv("EQUIBLES_API_KEY", "eq_test")

        def patlayan_client(**kw):
            raise ConnectionError("baglanti reddedildi")

        monkeypatch.setattr(resolver.httpx, "AsyncClient", patlayan_client)
        kayitlar, hata = _kos(resolver.equibles_ticker_cek("NVDA"))
        assert kayitlar is None
        assert "ConnectionError" in hata["neden"]

    def test_BEKLENMEYEN_GOVDE_TIPI_HATA_OLARAK_ISARETLENIR(self, monkeypatch):
        monkeypatch.setenv("EQUIBLES_API_KEY", "eq_test")

        def yanit_uretici(url, params, headers):
            return _SahteYanit(200, {"beklenmeyen": "sema"})

        monkeypatch.setattr(resolver.httpx, "AsyncClient",
                            lambda **kw: _SahteAsyncClient(yanit_uretici, **kw))
        kayitlar, hata = _kos(resolver.equibles_ticker_cek("NVDA"))
        assert kayitlar is None
        assert "govde" in hata["neden"]


# =====================================================================
# 5. BUTCE ONAY KURALI - GUNLUK 100 HAKKIN UZERINE CIKILMAZ
# =====================================================================
class TestButceKurali:
    def test_GUVENLIK_PAYININ_ALTINDA_ISTEGE_IZIN_VERILIR(self, monkeypatch):
        monkeypatch.setenv("EQUIBLES_API_KEY", "eq_test")
        r = resolver._get_redis()
        r.veri[resolver._equibles_kota_anahtari()] = str(
            resolver.EQUIBLES_GUNLUK_LIMIT - resolver.EQUIBLES_GUVENLIK_PAYI - 1)

        def yanit_uretici(url, params, headers):
            return _SahteYanit(200, {"data": []})

        monkeypatch.setattr(resolver.httpx, "AsyncClient",
                            lambda **kw: _SahteAsyncClient(yanit_uretici, **kw))
        kayitlar, hata = _kos(resolver.equibles_ticker_cek("NVDA"))
        assert hata is None

    def test_GUVENLIK_PAYI_ASILINCA_AG_CAGRISI_HIC_YAPILMAZ(self, monkeypatch):
        """BUTCE ONAY KURALI: gunluk 100 hakkin uzerine CIKILMAZ - yerel
        pay dolunca istek AG'A HIC CIKMADAN reddedilir."""
        monkeypatch.setenv("EQUIBLES_API_KEY", "eq_test")
        r = resolver._get_redis()
        r.veri[resolver._equibles_kota_anahtari()] = str(
            resolver.EQUIBLES_GUNLUK_LIMIT - resolver.EQUIBLES_GUVENLIK_PAYI)

        cagrildi = {"n": 0}

        def patlarsa_yakala(**kw):
            cagrildi["n"] += 1
            raise AssertionError("kota doluyken AG CAGRISI yapildi")

        monkeypatch.setattr(resolver.httpx, "AsyncClient", patlarsa_yakala)
        kayitlar, hata = _kos(resolver.equibles_ticker_cek("NVDA"))
        assert kayitlar is None
        assert hata["kota_asimi"] is True
        assert cagrildi["n"] == 0

    def test_equibles_kota_durumu_SEMASI(self, monkeypatch):
        monkeypatch.setenv("EQUIBLES_API_KEY", "eq_test")
        d = resolver.equibles_kota_durumu()
        assert d["limit"] == 100
        assert d["yerelden_izinli_mi"] is True
        assert d["yerel_sayac_kullanilan"] == 0

    def test_SUNUCU_KALAN_DUSUKSE_YEREL_SAYAC_MUSAIT_OLSA_BILE_REDDEDER(self, monkeypatch):
        """IKI SAYAC CELISIRSE SUNUCUYA GUVENILIR: yerel sayac daha yeni
        baslamis (kota BOL) gorunse bile, sunucunun bildirdigi 'kalan' guvenlik
        payinin altindaysa istek YINE DE reddedilmeli."""
        monkeypatch.setenv("EQUIBLES_API_KEY", "eq_test")
        r = resolver._get_redis()
        r.veri["equibles:sunucu_kalan"] = "2"   # sunucu: sadece 2 hak kaldi

        cagrildi = {"n": 0}

        def patlarsa_yakala(**kw):
            cagrildi["n"] += 1
            raise AssertionError("sunucu kalan dusukken AG CAGRISI yapildi")

        monkeypatch.setattr(resolver.httpx, "AsyncClient", patlarsa_yakala)
        kayitlar, hata = _kos(resolver.equibles_ticker_cek("NVDA"))
        assert kayitlar is None
        assert hata["kota_asimi"] is True
        assert cagrildi["n"] == 0

    def test_SUNUCU_KALAN_BILINMIYORSA_SADECE_YEREL_SAYAC_GECERLI(self, monkeypatch):
        """Sunucudan hic yanit alinmamissa (ilk cagri) yerel sayac TEK
        BASINA yeterli olmali - bilinmeyen bir deger REDDE yol acmamali."""
        monkeypatch.setenv("EQUIBLES_API_KEY", "eq_test")
        d = resolver.equibles_kota_durumu()
        assert d["sunucu_bildirdigi_kalan"] is None
        assert d["yerelden_izinli_mi"] is True


# =====================================================================
# 6. TAMAMLAYICILIK - YALNIZCA ZINCIR BOSSA CAGRILIR
#    (main.py'nin /trades/{ticker} mantigini DOGRUDAN test eder)
# =====================================================================
class TestTamamlayicilikMantigi:
    """main.py'yi FastAPI TestClient ile CALISTIRMAZ (bu servisin ilk test
    dosyasi - agir bir bagimliliktan kacinmak icin is mantigi resolver
    seviyesinde, cagri SIRASI da burada AYRI test edilir)."""

    def test_ZINCIR_KAYIT_BULURSA_EQUIBLES_HIC_CAGRILMAZ(self, monkeypatch):
        """OLCULEN BUTCE DISIPLINI: Quiver/FMP zaten kayit donduruyorsa
        Equibles'a DOKUNULMAMALI - gunluk 100 istek yalnizca GERCEKTEN
        bos donen sorgularda harcanir."""
        monkeypatch.setenv("EQUIBLES_API_KEY", "eq_test")
        cagrildi = {"n": 0}

        async def sahte_equibles(ticker, limit=50, timeout=None):
            cagrildi["n"] += 1
            return None, None

        monkeypatch.setattr(resolver, "equibles_ticker_cek", sahte_equibles)

        # main.py'nin hisse_islemleri() govdesindeki AYNI mantik:
        kayitlar = [resolver._fmp_normalize(
            {"symbol": "NVDA", "firstName": "A", "lastName": "B"}, "Senate")]
        vurus = resolver.ticker_filtrele(kayitlar, "NVDA")
        assert vurus  # zincir zaten kayit buldu
        if not vurus:
            _kos(resolver.equibles_ticker_cek("NVDA"))
        assert cagrildi["n"] == 0

    def test_ZINCIR_BOSSA_EQUIBLES_CAGRILIR(self, monkeypatch):
        cagrildi = {"n": 0}

        async def sahte_equibles(ticker, limit=50, timeout=None):
            cagrildi["n"] += 1
            return [resolver._equibles_normalize(EQUIBLES_ORNEK_SATIR)], None

        monkeypatch.setattr(resolver, "equibles_ticker_cek", sahte_equibles)

        kayitlar = [resolver._fmp_normalize(
            {"symbol": "AAPL", "firstName": "A", "lastName": "B"}, "Senate")]
        vurus = resolver.ticker_filtrele(kayitlar, "NVDA")   # NVDA yok -> bos
        assert not vurus
        if not vurus:
            ek, hata = _kos(resolver.equibles_ticker_cek("NVDA"))
            if ek:
                vurus = ek
        assert cagrildi["n"] == 1
        assert vurus and vurus[0]["source"] == "equibles"
