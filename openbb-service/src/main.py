"""
ALPHAWISE - OpenBB Veri Servisi
OpenBB'nin genis veri platformunu (100+ kaynak) ayri bir mikroservis olarak sunar.
Ayri tutulmasinin nedeni: openbb-core'un fastapi surumunu kendi icinde
sabitlemesi, bizim diger servislerimizle (fastapi==0.139.2) cakisiyordu.
"""
import math
import os
from fastapi import FastAPI
from openbb import obb

app = FastAPI(title="ALPHAWISE - OpenBB Data Service")

# OpenBB kimlik bilgilerini acikca yukle (bazi saglayicilarin anahtar ismi
# _api_key ile bitmiyor, ornegin tiingo_token - otomatik algilanmiyor)
_tiingo = os.getenv("TIINGO_TOKEN")
if _tiingo:
    obb.user.credentials.tiingo_token = _tiingo

_alpha_vantage = os.getenv("ALPHA_VANTAGE_API_KEY")
if _alpha_vantage:
    obb.user.credentials.alpha_vantage_api_key = _alpha_vantage


@app.get("/health")
def health():
    return {
        "service": "OpenBB",
        "status": "ok",
        "tiingo_configured": bool(_tiingo),
        "alpha_vantage_configured": bool(_alpha_vantage),
    }


def _json_guvenli(kayit: dict) -> dict:
    """NaN/Inf -> None; JSON'a cevrilemeyen tipleri metne cevirir."""
    temiz = {}
    for k, v in kayit.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            temiz[str(k)] = None
        elif v is None or isinstance(v, (str, bool, int)):
            temiz[str(k)] = v
        elif isinstance(v, float):
            temiz[str(k)] = v
        else:
            temiz[str(k)] = str(v)
    return temiz


@app.get("/equity/ownership/insider/{ticker}")
def equity_insider(ticker: str, limit: int = 200):
    """SEC Form 4 (sirket ici yonetici islemleri) — saglayici: sec (ucretsiz,
    anahtar gerektirmez). 23.08.2026'da eklendi; insider-trading-service (8250)
    bu ucu okur. SALT OKUNUR, yon kodu uretmez.

    OpenBB'nin kendi uyarisi: "This function is not intended for mass data
    collection." Bu yuzden cagiran taraf (8250) ticker basina >= 6 saat
    onbellek tutmak ZORUNDADIR.
    """
    try:
        output = obb.equity.ownership.insider_trading(
            symbol=ticker.upper(), provider="sec", limit=limit)
        df = output.to_dataframe().reset_index()
        # Form 4 kayitlarinda kritik alan eksikligi olculdu: %5,1. Bu alanlar
        # DataFrame'de NaN gelir ve json.dumps NaN'i kabul etmez
        # ("Out of range float values are not JSON compliant"). NaN/Inf -> null,
        # JSON'a cevrilemeyen tipler (Timestamp vb.) -> str.
        return [_json_guvenli(r) for r in df.to_dict(orient="records")]
    except Exception as e:
        return {"error": str(e), "provider": "sec"}


@app.get("/equity/price/{ticker}")
def equity_price(ticker: str, provider: str = "yfinance", start_date: str = None, end_date: str = None, limit: int = 30):
    """Gecmis fiyat verisi. provider: yfinance, tiingo, alpha_vantage, fmp, polygon"""
    try:
        kwargs = {"provider": provider}
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        output = obb.equity.price.historical(ticker.upper(), **kwargs)
        df = output.to_dataframe()
        result = df.reset_index().to_dict(orient="records")
        if not start_date:
            result = result[-limit:]
        return result
    except Exception as e:
        return {"error": str(e), "provider": provider}
