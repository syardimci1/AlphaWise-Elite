"""Birim testleri: equibles_client.py (madde 58, sec-edgar-13f-service).

Bu servisin var olan testleriyle (test_sec13f.py) AYNI desen: pytest
fixture'siz, asyncio.run() ile coroutine calistirma, ag/redis'e SAHTE
nesnelerle mudahale (gercek baglanti yok).
"""
import asyncio
import os
import sys

sys.path.insert(0, "/opt/alphawise/commercial/AlphaWise-Elite/sec-edgar-13f-service")

from src import equibles_client as ec


# ==================== sahte nesneler ====================

class _SahtePipeline:
    def __init__(self, mağaza):
        self._mağaza = mağaza
        self._işlemler = []

    def incr(self, anahtar):
        self._işlemler.append(("incr", anahtar))
        return self

    def expire(self, anahtar, saniye):
        self._işlemler.append(("expire", anahtar, saniye))
        return self

    def set(self, anahtar, deger, ex=None):
        self._işlemler.append(("set", anahtar, deger))
        return self

    async def execute(self):
        for işlem in self._işlemler:
            if işlem[0] == "incr":
                self._mağaza[işlem[1]] = int(self._mağaza.get(işlem[1], 0)) + 1
            elif işlem[0] == "set":
                self._mağaza[işlem[1]] = işlem[2]
        return []


class _SahteRedis:
    """decode_responses=False gercek istemciyle AYNI davranis: bayt/str
    karisik saklanabilir, kota fonksiyonlari int()'e guvenir."""

    def __init__(self, başlangıç=None):
        self._mağaza = dict(başlangıç or {})

    async def get(self, anahtar):
        return self._mağaza.get(anahtar)

    def pipeline(self):
        return _SahtePipeline(self._mağaza)


class _SahteYanit:
    def __init__(self, status_code, gövde=None, headers=None, metin=""):
        self.status_code = status_code
        self._gövde = gövde or {}
        self.headers = headers or {}
        self.text = metin

    def json(self):
        return self._gövde


class _SahteAsyncClient:
    """httpx.AsyncClient(...) as c: await c.get(...) sozlesmesini taklit
    eder. SINIF DEGISKENI uzerinden hangi yanitin donecegi/nelerin
    cagirildigi test tarafindan ayarlanir."""
    sıradaki_yanıt = None
    son_url = None
    son_params = None
    son_headers = None
    çağrı_sayısı = 0

    def __init__(self, timeout=None):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, params=None, headers=None):
        type(self).son_url = url
        type(self).son_params = params
        type(self).son_headers = headers
        type(self).çağrı_sayısı += 1
        return type(self).sıradaki_yanıt


def _temizle(monkeypatch_gibi=None):
    os.environ.pop("EQUIBLES_API_KEY", None)
    _SahteAsyncClient.sıradaki_yanıt = None
    _SahteAsyncClient.son_url = None
    _SahteAsyncClient.son_params = None
    _SahteAsyncClient.son_headers = None
    _SahteAsyncClient.çağrı_sayısı = 0


# ==================== normallestirme ====================

def test_holder_normalize_gercek_alan_adlari():
    """14.09.2026 canli cagriyla (NVDA) dogrulanan gercek sema."""
    kayit = {
        "name": "BlackRock, Inc.", "cik": "2012383", "shares": 1941918386,
        "value": 388558449841, "percentOfTotal": 10.991379148898869,
        "listedTicker": None, "positionType": "Common",
    }
    r = ec._holder_normalize(kayit)
    assert r["kurum_adi"] == "BlackRock, Inc."
    assert r["kurum_cik"] == "2012383"
    assert r["hisse_adet"] == 1941918386
    assert r["deger_usd"] == 388558449841
    assert round(r["toplamin_yuzdesi"], 2) == 10.99
    assert r["pozisyon_tipi"] == "Common"


def test_aktivite_satiri_gercek_alan_adlari():
    """14.09.2026 canli cagriyla (BlackRock CIK 2012383) dogrulanan sema."""
    kayit = {
        "ticker": "NVDA", "company": "Nvidia Corp",
        "previousShares": 1928629174, "currentShares": 1943474686,
        "deltaShares": 14845512, "deltaValue": 52516921973,
    }
    r = ec._aktivite_satiri(kayit)
    assert r["ticker"] == "NVDA"
    assert r["sirket"] == "Nvidia Corp"
    assert r["onceki_hisse"] == 1928629174
    assert r["guncel_hisse"] == 1943474686
    assert r["hisse_degisimi"] == 14845512
    assert r["deger_degisimi_usd"] == 52516921973


# ==================== paylasimli kota anahtari ====================

def test_kota_anahtari_congress_trading_ile_AYNI_isim_alaninda():
    """KASITLI: congress-trading-service/resolver.py::_equibles_kota_anahtari
    ile BIREBIR ayni format - iki servis TEK bir gunluk sayaci gormeli."""
    anahtar = ec._kota_anahtari()
    assert anahtar.startswith("equibles:gunluk:")
    assert not anahtar.startswith("sec13f:")  # servise ozel ONEK KASITLI kullanilmadi


# ==================== kota mantigi ====================

def test_kota_redis_yoksa_izinli_fail_open():
    kota = asyncio.run(ec.kota_durumu(None))
    assert kota["yerelden_izinli_mi"] is True
    assert kota["yerel_sayac_kullanilan"] == 0


def test_kota_esik_altinda_izinli():
    r = _SahteRedis({ec._kota_anahtari(): 50})
    kota = asyncio.run(ec.kota_durumu(r))
    assert kota["yerelden_izinli_mi"] is True
    assert kota["yerel_sayac_kullanilan"] == 50


def test_kota_guvenlik_payi_asilinca_reddeder():
    r = _SahteRedis({ec._kota_anahtari(): 95})
    kota = asyncio.run(ec.kota_durumu(r))
    assert kota["yerelden_izinli_mi"] is False


def test_kota_sunucu_kalan_dusukse_yerel_musait_olsa_bile_reddeder():
    """Sunucu-oncelikli celiski cozumu: iki servis paylasilan hesabi
    kullandigi icin YEREL sayac dusuk olsa bile SUNUCUNUN bildirdigi
    kalan kisitlayiciysa istek reddedilmeli."""
    r = _SahteRedis({ec._kota_anahtari(): 1, "equibles:sunucu_kalan": 2})
    kota = asyncio.run(ec.kota_durumu(r))
    assert kota["yerelden_izinli_mi"] is False


def test_kota_artir_hem_sayaci_hem_sunucu_degerini_yazar():
    r = _SahteRedis()
    asyncio.run(ec._kota_artir(r, sunucu_kalan="42"))
    assert int(r._mağaza[ec._kota_anahtari()]) == 1
    assert r._mağaza["equibles:sunucu_kalan"] == "42"


# ==================== anahtarsiz davranis ====================

def test_holders_cek_anahtarsiz_ag_cagrisi_yapmaz():
    _temizle()
    veri, hata = asyncio.run(ec.holders_cek(None, "NVDA"))
    assert veri is None
    assert "EQUIBLES_API_KEY" in hata["neden"]
    assert _SahteAsyncClient.çağrı_sayısı == 0


def test_institution_activity_cek_anahtarsiz_ag_cagrisi_yapmaz():
    _temizle()
    veri, hata = asyncio.run(ec.institution_activity_cek(None, "2012383"))
    assert veri is None
    assert "EQUIBLES_API_KEY" in hata["neden"]
    assert _SahteAsyncClient.çağrı_sayısı == 0


def test_holders_cek_kota_asiminda_ag_cagrisi_yapmaz():
    _temizle()
    os.environ["EQUIBLES_API_KEY"] = "eq_test_anahtari"
    r = _SahteRedis({ec._kota_anahtari(): 95})
    veri, hata = asyncio.run(ec.holders_cek(r, "NVDA"))
    assert veri is None
    assert hata["kota_asimi"] is True
    assert _SahteAsyncClient.çağrı_sayısı == 0
    _temizle()


# ==================== basarili cagri (sahte httpx) ====================

def test_holders_cek_basarili_gercek_govdeyi_normallestirir(monkeypatch):
    _temizle()
    os.environ["EQUIBLES_API_KEY"] = "eq_test_anahtari"
    monkeypatch.setattr(ec.httpx, "AsyncClient", _SahteAsyncClient)
    _SahteAsyncClient.sıradaki_yanıt = _SahteYanit(
        200,
        gövde={
            "data": [{
                "name": "BlackRock, Inc.", "cik": "2012383", "shares": 1941918386,
                "value": 388558449841, "percentOfTotal": 10.99,
                "listedTicker": None, "positionType": "Common",
            }],
            "meta": {"reportDate": "2026-06-30", "totalInstitutions": 5956,
                     "limit": 500, "offset": 0, "count": 1, "hasMore": True},
        },
        headers={"X-RateLimit-Remaining": "94"},
    )
    r = _SahteRedis()
    veri, hata = asyncio.run(ec.holders_cek(r, "nvda"))
    assert hata is None
    assert veri["toplam_kurum"] == 5956
    assert veri["daha_fazla_var"] is True
    assert veri["kurumlar"][0]["kurum_adi"] == "BlackRock, Inc."
    assert "/stocks/NVDA/institutional-holders" in _SahteAsyncClient.son_url
    # kota gercekten arttirildi VE sunucu kalani saklandi
    assert int(r._mağaza[ec._kota_anahtari()]) == 1
    assert r._mağaza["equibles:sunucu_kalan"] == "94"
    _temizle()


def test_institution_activity_cek_basarili_dort_kovayi_da_normallestirir(monkeypatch):
    _temizle()
    os.environ["EQUIBLES_API_KEY"] = "eq_test_anahtari"
    monkeypatch.setattr(ec.httpx, "AsyncClient", _SahteAsyncClient)
    _SahteAsyncClient.sıradaki_yanıt = _SahteYanit(
        200,
        gövde={
            "name": "BlackRock, Inc.", "cik": "2012383",
            "reportDate": "2026-06-30", "previousReportDate": "2026-03-31",
            "initiated": [{"ticker": "SPCX", "company": "Space Exploration Technologies Corp",
                           "previousShares": 0, "currentShares": 54755537,
                           "deltaShares": 54755537, "deltaValue": 9355531043}],
            "increased": [{"ticker": "NVDA", "company": "Nvidia Corp",
                           "previousShares": 1928629174, "currentShares": 1943474686,
                           "deltaShares": 14845512, "deltaValue": 52516921973}],
            "reduced": [{"ticker": "INTC", "company": "Intel Corp",
                        "previousShares": 447794132, "currentShares": 426478962,
                        "deltaShares": -21315170, "deltaValue": 39788102417}],
            "exited": [],
            "initiatedTotal": 12, "increasedTotal": 340, "reducedTotal": 210, "exitedTotal": 5,
        },
        headers={"X-RateLimit-Remaining": "93"},
    )
    r = _SahteRedis()
    veri, hata = asyncio.run(ec.institution_activity_cek(r, "2012383"))
    assert hata is None
    assert veri["kurum_adi"] == "BlackRock, Inc."
    assert len(veri["baslatilan"]) == 1 and veri["baslatilan"][0]["ticker"] == "SPCX"
    assert len(veri["artirilan"]) == 1 and veri["artirilan"][0]["ticker"] == "NVDA"
    assert len(veri["azaltilan"]) == 1 and veri["azaltilan"][0]["hisse_degisimi"] == -21315170
    assert veri["cikilan"] == []
    assert veri["artirilan_toplam"] == 340
    assert "/institutions/2012383/activity" in _SahteAsyncClient.son_url
    _temizle()


def test_institution_activity_cek_bucket_parametresini_iletir(monkeypatch):
    _temizle()
    os.environ["EQUIBLES_API_KEY"] = "eq_test_anahtari"
    monkeypatch.setattr(ec.httpx, "AsyncClient", _SahteAsyncClient)
    _SahteAsyncClient.sıradaki_yanıt = _SahteYanit(
        200,
        gövde={"name": "x", "cik": "1", "reportDate": "2026-06-30",
               "previousReportDate": "2026-03-31", "initiated": [], "increased": [],
               "reduced": [], "exited": [], "initiatedTotal": 0, "increasedTotal": 0,
               "reducedTotal": 0, "exitedTotal": 0},
        headers={},
    )
    r = _SahteRedis()
    asyncio.run(ec.institution_activity_cek(r, "1", bucket="increased"))
    assert _SahteAsyncClient.son_params["bucket"] == "increased"
    _temizle()


# ==================== hata yonetimi ====================

def test_holders_cek_404_disi_http_hatasi_yakalanir(monkeypatch):
    _temizle()
    os.environ["EQUIBLES_API_KEY"] = "eq_test_anahtari"
    monkeypatch.setattr(ec.httpx, "AsyncClient", _SahteAsyncClient)
    _SahteAsyncClient.sıradaki_yanıt = _SahteYanit(401, metin="unauthorized")
    veri, hata = asyncio.run(ec.holders_cek(_SahteRedis(), "NVDA"))
    assert veri is None
    assert hata["http_status"] == 401
    _temizle()


def test_institution_activity_cek_404_kurum_bulunamadi(monkeypatch):
    _temizle()
    os.environ["EQUIBLES_API_KEY"] = "eq_test_anahtari"
    monkeypatch.setattr(ec.httpx, "AsyncClient", _SahteAsyncClient)
    _SahteAsyncClient.sıradaki_yanıt = _SahteYanit(404, metin="not found")
    veri, hata = asyncio.run(ec.institution_activity_cek(_SahteRedis(), "999999999"))
    assert veri is None
    assert hata["http_status"] == 404
    _temizle()


def test_holders_cek_429_sunucu_kotasi(monkeypatch):
    _temizle()
    os.environ["EQUIBLES_API_KEY"] = "eq_test_anahtari"
    monkeypatch.setattr(ec.httpx, "AsyncClient", _SahteAsyncClient)
    _SahteAsyncClient.sıradaki_yanıt = _SahteYanit(429)
    veri, hata = asyncio.run(ec.holders_cek(_SahteRedis(), "NVDA"))
    assert veri is None
    assert hata["http_status"] == 429
    _temizle()


def test_holders_cek_beklenmeyen_govde_tipi(monkeypatch):
    _temizle()
    os.environ["EQUIBLES_API_KEY"] = "eq_test_anahtari"
    monkeypatch.setattr(ec.httpx, "AsyncClient", _SahteAsyncClient)
    _SahteAsyncClient.sıradaki_yanıt = _SahteYanit(200, gövde={"data": "liste-degil"})
    veri, hata = asyncio.run(ec.holders_cek(_SahteRedis(), "NVDA"))
    assert veri is None
    assert "beklenmeyen govde" in hata["neden"]
    _temizle()


def test_holders_cek_baglanti_istisnasi_yakalanir(monkeypatch):
    _temizle()
    os.environ["EQUIBLES_API_KEY"] = "eq_test_anahtari"

    class _PatlayanClient(_SahteAsyncClient):
        async def get(self, *a, **k):
            raise ConnectionError("dns cozulemedi")

    monkeypatch.setattr(ec.httpx, "AsyncClient", _PatlayanClient)
    veri, hata = asyncio.run(ec.holders_cek(_SahteRedis(), "NVDA"))
    assert veri is None
    assert "ConnectionError" in hata["neden"]
    _temizle()
