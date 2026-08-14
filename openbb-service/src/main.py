"""
ALPHAWISE - OpenBB Veri Servisi
OpenBB'nin genis veri platformunu (100+ kaynak) ayri bir mikroservis olarak sunar.
Ayri tutulmasinin nedeni: openbb-core'un fastapi surumunu kendi icinde
sabitlemesi, bizim diger servislerimizle (fastapi==0.139.2) cakisiyordu.
"""
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
