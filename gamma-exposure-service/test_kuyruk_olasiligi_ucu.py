"""GET /kuyruk-olasiligi/{ticker} uc testleri - FastAPI TestClient,
gercek aga cikmadan (openbb cagrisi monkeypatch'lenir)."""
from fastapi.testclient import TestClient
import main


def test_kuyruk_olasiligi_basarili_cagri(monkeypatch):
    async def sahte_openbb_get(self, url, **kwargs):
        import httpx
        # oipd parity-forward cikarimi ayni strike'ta call VE put ister
        # (bkz. kuyruk_olasiligi.py, test_kuyruk_olasiligi.py::_ornek_kontratlar);
        # asagidaki strike listesi bunu saglar.
        kontratlar = []
        for strike in [730, 740, 750, 760, 770]:
            kontratlar.append({"strike": strike, "option_type": "put",
                "implied_volatility": 0.15, "open_interest": 100,
                "expiration": "2026-10-16",
                "last_trade_price": max(0.5, strike - 765.96),
                "underlying_price": 765.96})
            kontratlar.append({"strike": strike, "option_type": "call",
                "implied_volatility": 0.15, "open_interest": 100,
                "expiration": "2026-10-16",
                "last_trade_price": max(0.5, 765.96 - strike),
                "underlying_price": 765.96})
        return httpx.Response(200, json=kontratlar)
    monkeypatch.setattr("httpx.AsyncClient.get", sahte_openbb_get)
    monkeypatch.setattr(main, "_get_redis", lambda: (_ for _ in ()).throw(Exception("redis yok, test")))

    client = TestClient(main.app)
    r = client.get("/kuyruk-olasiligi/SPY?vade=2026-10-16")
    assert r.status_code == 200
    gov = r.json()
    assert gov["ticker"] == "SPY"
    assert "ortalama" in gov
    assert gov["flashalpha_kotasi_tuketildi"] is False


def test_kuyruk_olasiligi_gecersiz_ticker_400():
    client = TestClient(main.app)
    r = client.get("/kuyruk-olasiligi/../../etc?vade=2026-10-16")
    assert r.status_code in (400, 404)


def test_kuyruk_olasiligi_hata_govdesi_IC_BILGI_SIZDIRMAZ(monkeypatch):
    """alphawise-elite-ff'nin uyardigi desen: detail alaninda anahtar
    adi/kota sayaci gibi ham ic bilgi OLMAMALI."""
    async def coken_openbb_get(self, url, **kwargs):
        raise ConnectionError("baglanti koptu")
    monkeypatch.setattr("httpx.AsyncClient.get", coken_openbb_get)

    client = TestClient(main.app)
    r = client.get("/kuyruk-olasiligi/SPY?vade=2026-10-16")
    assert r.status_code == 502
    detail = r.json()["detail"]
    assert "anahtar" not in detail.lower()
    assert "kullanilan" not in detail.lower()
    assert "FLASHALPHA" not in detail
