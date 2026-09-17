"""Equibles tamamlayici istemci testleri — madde 52 (16.09.2026).

test_baski.py'deki senkron test deseni izlenir (asyncio eklentisi
kurulu degil, sessizce atlanan test riskini onceden ogrenmisiz).
sepet_kaynagi.py zaten SENKRON httpx.Client kullanir, bu yuzden
_Istemci de senkron (with/__enter__) yazildi.
"""
import sys

import pytest

sys.path.insert(0, "/app")

from src import sepet_kaynagi as sk  # noqa: E402


class _Yanit:
    def __init__(self, kod=200, govde=None, kalan=None):
        self.status_code = kod
        self._g = govde
        self.text = str(govde)
        self.headers = {"X-RateLimit-Remaining": str(kalan)} if kalan is not None else {}

    def json(self):
        return self._g


class _Istemci:
    """DIKKAT: yanitlar listesi KOPYALANMAZ - her httpx.Client() cagrisi
    (sayfalamada birden fazla olabilir) AYNI listeyi tuketmeli, aksi
    halde her yeni Client() ornegi listeyi bastan gorur ve ikinci sayfa
    hep ilkini donderir (bu hata testi yazarken YAKALANDI, duzeltildi)."""

    def __init__(self, yanitlar):
        self._yanitlar = yanitlar

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, url, params=None, headers=None):
        return self._yanitlar.pop(0)


class _SahteRedis:
    """Gercek redis-py'nin bu modulun kullandigi kucuk alt kumesi."""

    def __init__(self):
        self._d = {}

    def get(self, k):
        return self._d.get(k)

    def setex(self, k, ttl, v):
        self._d[k] = v

    def pipeline(self):
        return _SahtePipeline(self)


class _SahtePipeline:
    def __init__(self, redis):
        self._r = redis
        self._islemler = []

    def incr(self, k):
        self._islemler.append(("incr", k))
        return self

    def expire(self, k, ttl):
        return self

    def set(self, k, v, ex=None):
        self._islemler.append(("set", k, v))
        return self

    def execute(self):
        for op in self._islemler:
            if op[0] == "incr":
                self._r._d[op[1]] = str(int(self._r._d.get(op[1], 0)) + 1)
            elif op[0] == "set":
                self._r._d[op[1]] = op[2]


def _kur(monkeypatch, yanitlar=None, redis=None, key="test-anahtar"):
    monkeypatch.setenv("EQUIBLES_API_KEY", key)
    if yanitlar is not None:
        monkeypatch.setattr(sk.httpx, "Client", lambda *a, **k: _Istemci(yanitlar))
    r = redis if redis is not None else _SahteRedis()
    monkeypatch.setattr(sk, "_get_redis", lambda: r)
    return r


# ---------------------------------------------------------- kota / anahtar
def test_anahtar_yoksa_istek_ATILMAZ(monkeypatch):
    monkeypatch.delenv("EQUIBLES_API_KEY", raising=False)
    monkeypatch.setattr(sk, "_get_redis", lambda: _SahteRedis())
    veri, hata = sk.cftc_cot_cek()
    assert veri is None
    assert "EQUIBLES_API_KEY" in hata["neden"]


def test_kota_asilinca_istek_ATILMAZ(monkeypatch):
    r = _SahteRedis()
    r._d["equibles:gunluk:" + __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc).strftime("%Y-%m-%d")] = "96"
    _kur(monkeypatch, yanitlar=[], redis=r)   # yanit listesi BOS - cagrilirsa patlar
    veri, hata = sk.cftc_cot_cek()
    assert veri is None
    assert hata["kota_asimi"] is True


def test_basarili_cagri_KOTAYI_artirir(monkeypatch):
    r = _kur(monkeypatch, yanitlar=[_Yanit(200, {"data": []}, kalan=88)])
    sk.cftc_cot_cek()
    gun = __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc).strftime("%Y-%m-%d")
    assert r.get(f"equibles:gunluk:{gun}") == "1"
    assert r.get("equibles:sunucu_kalan") == "88"


# ---------------------------------------------------------- endeks sepeti
def _bilesen(ticker, weight, isLinked=True):
    return {"rank": 1, "ticker": ticker, "name": ticker, "isLinked": isLinked,
            "weight": weight, "fundShares": 1.0, "fundValueUsd": 1.0}


def test_endeks_sepeti_BAGLANAMAYAN_satirlar_CIKARILIR(monkeypatch):
    govde = {"slug": "sp-500", "name": "S&P 500", "asOfDate": "2026-09-15",
            "source": "test", "constituentCount": 3,
            "data": [_bilesen("AAPL", 0.5), _bilesen("XYZ", 0.1, isLinked=False),
                    {"rank": 3, "ticker": "", "isLinked": True}],
            "meta": {"hasMore": False, "count": 3}}
    _kur(monkeypatch, yanitlar=[_Yanit(200, govde, kalan=99)])
    veri, hata = sk.endeks_sepeti_cek("sp-500")
    assert hata is None
    assert veri["sepet"] == ["AAPL"]
    assert veri["kullanilabilir"] == 1
    assert veri["baglanamayan_cikarildi"] == 2
    assert veri["toplam_cekilen"] == 3


def test_endeks_sepeti_SAYFALAMA_hasMore_ile_devam_eder(monkeypatch):
    sayfa1 = {"slug": "sp-500", "name": "S&P 500", "asOfDate": "d",
             "source": "s", "constituentCount": 2,
             "data": [_bilesen("A", 0.6)], "meta": {"hasMore": True, "count": 1}}
    sayfa2 = {"slug": "sp-500", "name": "S&P 500", "asOfDate": "d",
             "source": "s", "constituentCount": 2,
             "data": [_bilesen("B", 0.4)], "meta": {"hasMore": False, "count": 1}}
    _kur(monkeypatch, yanitlar=[_Yanit(200, sayfa1, kalan=99), _Yanit(200, sayfa2, kalan=98)])
    veri, hata = sk.endeks_sepeti_cek("sp-500")
    assert hata is None
    assert sorted(veri["sepet"]) == ["A", "B"]
    assert veri["toplam_cekilen"] == 2


def test_endeks_sepeti_azami_sayfa_TAVANINDA_durur(monkeypatch):
    """Bozuk bir hasMore=True dongusu sonsuz istek uretmemeli."""
    sonsuz_sayfa = {"slug": "x", "name": "x", "asOfDate": "d", "source": "s",
                    "constituentCount": 999,
                    "data": [_bilesen("A", 0.1)], "meta": {"hasMore": True, "count": 1}}
    _kur(monkeypatch, yanitlar=[_Yanit(200, sonsuz_sayfa, kalan=99)] * 2)
    veri, hata = sk.endeks_sepeti_cek("x", azami_sayfa=2)
    assert hata is None    # 2 sayfa harcandi, patlamadi
    assert veri["toplam_cekilen"] == 2


def test_endeks_sepeti_ONBELLEKTEN_okunur_ikinci_cagrida_AG_ISTEGI_YOK(monkeypatch):
    govde = {"slug": "sp-500", "name": "n", "asOfDate": "d", "source": "s",
            "constituentCount": 1, "data": [_bilesen("AAPL", 1.0)],
            "meta": {"hasMore": False, "count": 1}}
    r = _kur(monkeypatch, yanitlar=[_Yanit(200, govde, kalan=99)])
    v1, _ = sk.endeks_sepeti_cek("sp-500")
    # ikinci cagrida yanit listesi BOS - ag'a gidilirse IndexError patlar
    monkeypatch.setattr(sk.httpx, "Client", lambda *a, **k: _Istemci([]))
    v2, hata2 = sk.endeks_sepeti_cek("sp-500")
    assert hata2 is None
    assert v2 == v1


# ---------------------------------------------------------------- cftc cot
def test_cftc_cot_alan_adlari_TURKCELESTIRILIR(monkeypatch):
    govde = {"data": [{"marketCode": "13874A", "marketName": "E-mini S&P 500 (CME)",
                       "category": "EquityIndices", "reportDate": "2026-09-08",
                       "openInterest": 2071836, "commNet": -50017, "nonCommNet": -76036}]}
    _kur(monkeypatch, yanitlar=[_Yanit(200, govde, kalan=90)])
    veri, hata = sk.cftc_cot_cek("EquityIndices")
    assert hata is None
    assert veri["kontrat_sayisi"] == 1
    p = veri["pozisyonlar"][0]
    assert p["piyasa_kodu"] == "13874A"
    assert p["ticari_net"] == -50017
    assert p["ticari_disi_net"] == -76036


def test_cftc_cot_kategori_PARAMETRE_olarak_GIDER(monkeypatch):
    yakalanan = {}

    class _Izleyen(_Istemci):
        def get(self, url, params=None, headers=None):
            yakalanan.update(params or {})
            return super().get(url, params, headers)

    monkeypatch.setenv("EQUIBLES_API_KEY", "k")
    monkeypatch.setattr(sk, "_get_redis", lambda: _SahteRedis())
    monkeypatch.setattr(sk.httpx, "Client",
                        lambda *a, **k: _Izleyen([_Yanit(200, {"data": []}, kalan=90)]))
    sk.cftc_cot_cek("Energy")
    assert yakalanan.get("category") == "Energy"


# ---------------------------------------------------------------- put/call
def test_putcall_GECERSIZ_tip_AG_ISTEGI_ATMADAN_reddedilir(monkeypatch):
    monkeypatch.setenv("EQUIBLES_API_KEY", "k")
    monkeypatch.setattr(sk, "_get_redis", lambda: _SahteRedis())
    monkeypatch.setattr(sk.httpx, "Client", lambda *a, **k: _Istemci([]))  # cagrilirsa patlar
    veri, hata = sk.putcall_orani_cek("GecersizTip")
    assert veri is None
    assert "gecersiz tip" in hata["neden"]


def test_putcall_alan_adlari_TURKCELESTIRILIR(monkeypatch):
    govde = {"data": [{"date": "2026-09-16", "callVolume": 100, "putVolume": 90,
                       "totalVolume": 190, "putCallRatio": 0.9}]}
    _kur(monkeypatch, yanitlar=[_Yanit(200, govde, kalan=90)])
    veri, hata = sk.putcall_orani_cek("Total", 1)
    assert hata is None
    g = veri["gunluk_seri"][0]
    assert g["tarih"] == "2026-09-16"
    assert g["put_call_orani"] == 0.9


# ------------------------------------------------------------- HTTP hatalari
def test_429_kota_asimi_olarak_ISARETLENIR(monkeypatch):
    _kur(monkeypatch, yanitlar=[_Yanit(429, kalan=0)])
    veri, hata = sk.cftc_cot_cek()
    assert veri is None
    assert hata["http_status"] == 429


def test_500_genel_hata_olarak_DONER(monkeypatch):
    _kur(monkeypatch, yanitlar=[_Yanit(500, kalan=90)])
    veri, hata = sk.cftc_cot_cek()
    assert veri is None
    assert hata["http_status"] == 500
