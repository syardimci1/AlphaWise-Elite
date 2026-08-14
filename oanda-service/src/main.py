"""
ALPHAWISE - OANDA Forex Servisi
oanda/v20-python (resmi kutuphane) ile doviz cifti alim-satimi.
KRITIK: environment HER ZAMAN 'practice' - koda sabit, degistirilemez.
Alpaca'daki ayni guvenlik deseni: onizleme -> admin onayi -> gercek emir.
"""
import os
from typing import Optional
from fastapi import FastAPI, Header, HTTPException, Query
import v20
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ALPHAWISE - OANDA Forex Service (PRACTICE ONLY)")

ADMIN_KEY = os.getenv("ADMIN_KEY")
OANDA_ACCESS_TOKEN = os.getenv("OANDA_ACCESS_TOKEN")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")

# KRITIK: hostname HER ZAMAN practice-api - gercek hesaba asla baglanmaz
OANDA_HOSTNAME = "api-fxpractice.oanda.com"


def get_oanda_client():
    return v20.Context(
        hostname=OANDA_HOSTNAME,
        port=443,
        token=OANDA_ACCESS_TOKEN,
    )


def verify_admin(x_admin_key: Optional[str] = Header(default=None)):
    if not ADMIN_KEY or x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Admin key gerekli ve dogru olmali")
    return True


@app.get("/health")
def health():
    return {"service": "OANDA Forex", "status": "ok", "mode": "PRACTICE_ONLY"}


@app.get("/account")
def account(x_admin_key: Optional[str] = Header(default=None)):
    verify_admin(x_admin_key)
    ctx = get_oanda_client()
    response = ctx.account.get(OANDA_ACCOUNT_ID)
    if response.status != 200:
        raise HTTPException(status_code=502, detail=f"OANDA hatasi: {response.body}")
    acc = response.get("account", "200")
    return {
        "account_id": OANDA_ACCOUNT_ID,
        "balance": str(acc.balance),
        "currency": acc.currency,
        "unrealized_pl": str(acc.unrealizedPL),
        "margin_available": str(acc.marginAvailable),
        "open_position_count": acc.openPositionCount,
        "mode": "PRACTICE",
    }


@app.get("/price/{instrument}")
def price(instrument: str, x_admin_key: Optional[str] = Header(default=None)):
    """Guncel doviz kuru. instrument formati: EUR_USD, USD_TRY gibi."""
    verify_admin(x_admin_key)
    ctx = get_oanda_client()
    response = ctx.pricing.get(OANDA_ACCOUNT_ID, instruments=instrument.upper())
    if response.status != 200:
        raise HTTPException(status_code=502, detail=f"OANDA hatasi: {response.body}")
    prices = response.get("prices", "200")
    if not prices:
        return {"instrument": instrument, "error": "fiyat bulunamadi"}
    p = prices[0]
    return {
        "instrument": instrument.upper(),
        "bid": str(p.bids[0].price) if p.bids else None,
        "ask": str(p.asks[0].price) if p.asks else None,
        "time": str(p.time),
    }


@app.post("/execute/{instrument}")
def execute(
    instrument: str,
    units: int = Query(..., description="Pozitif=al, negatif=sat"),
    confirm: bool = Query(default=False),
    x_admin_key: Optional[str] = Header(default=None),
):
    """
    Doviz emri gonderir. confirm=true olmadan SADECE onizleme yapar, emir gondermez.
    """
    verify_admin(x_admin_key)

    price_info = price(instrument, x_admin_key)

    if not confirm:
        return {
            "instrument": instrument.upper(),
            "units": units,
            "current_price": price_info,
            "action": "PREVIEW_ONLY",
            "note": "Emir GONDERILMEDI. Gerceklestirmek icin confirm=true kullanin.",
            "mode": "PRACTICE",
        }

    ctx = get_oanda_client()
    response = ctx.order.market(
        OANDA_ACCOUNT_ID,
        instrument=instrument.upper(),
        units=units,
    )
    if response.status != 201:
        raise HTTPException(status_code=502, detail=f"OANDA emir hatasi: {response.body}")

    return {
        "instrument": instrument.upper(),
        "units": units,
        "action": "ORDER_SUBMITTED",
        "mode": "PRACTICE",
        "raw_response": str(response.body),
    }
