"""KUYRUK OLASILIGI (17.09.2026) - Grup 5 denetimi #6 KUR karari.

MEVCUT /gex ve /dix-like ve /dex-vanna UCLARINA DOKUNULMADI.

oipd (options-implied-probability) ile gozlenen vol gulumsemesinden
risk-notr olasilik dagilimi cikarir - duz-vol Black-Scholes'in (dex_vanna.py)
YAPISAL olarak veremedigi bir bilgi (audit: ayni SPY zincirinde 5,9 puanlik
olculmus fark). FlashAlpha kotasi TUKETMEZ, openbb-service (yfinance,
ucretsiz) kullanilir - /dex-vanna ile AYNI ilke.

Girdi dogrulama audit'te (#6, K3/K5) OLCULEN davranisi KORUR: negatif fiyat
ve yetersiz strike sayisi SESSIZCE yutulmaz, ValueError firlatilir.
"""
from datetime import date, datetime

import pandas as pd
from oipd import ProbCurve, MarketInputs


def openbb_zincirini_oipd_bicimine_cevir(kontratlar: list[dict], vade: str) -> pd.DataFrame:
    """openbb /derivatives/options/chains formatindan (dex_vanna.py'nin de
    kullandigi alan adlari: strike, option_type, expiration, last_trade_price)
    oipd'nin ProbCurve.from_chain bekledigi tek-vadeli uzun-formata cevirir.

    Yalnizca `vade`ye esit expiration'lu kontratlar alinir (oipd tek vade
    ister, ProbCurve.from_chain coklu vadede ValueError firlatir)."""
    satirlar = []
    for k in kontratlar:
        if str(k.get("expiration")) != vade:
            continue
        satirlar.append({
            "strike": float(k["strike"]),
            "option_type": str(k["option_type"]).lower(),
            "last_price": float(k["last_trade_price"]),
            "expiry": vade,
        })
    return pd.DataFrame(satirlar)


def hesapla(kontratlar: list[dict], spot: float, risksiz_oran: float,
           vade: str, degerleme_tarihi: str) -> dict:
    """Risk-notr olasilik dagilimini hesaplar. Audit #6'daki B4 kirma
    bulgularini (negatif fiyat, yetersiz strike -> ValueError) DEGISTIRMEDEN
    disariya tasir - servis (main.py) bunlari HTTPException 400/422'ye cevirir."""
    chain = openbb_zincirini_oipd_bicimine_cevir(kontratlar, vade)
    if (chain["last_price"] < 0).any():
        raise ValueError("Opsiyon zincirinde negatif fiyat var")
    if len(chain) < 5:
        raise ValueError(f"Yetersiz opsiyon verisi: en az 5 strike gerekli, {len(chain)} bulundu")

    market = MarketInputs(
        risk_free_rate=risksiz_oran,
        valuation_date=datetime.strptime(degerleme_tarihi, "%Y-%m-%d").date(),
        underlying_price=spot,
    )
    pc = ProbCurve.from_chain(chain, market)
    return {
        "ortalama": float(pc.mean()),
        "varyans": float(pc.variance()),
        "carpiklik": float(pc.skew()),
        "basiklik": float(pc.kurtosis()),
        "spot_alti_olasilik": float(pc.prob_below(spot)),
        "spot_ustu_5pct_olasilik": float(pc.prob_above(spot * 1.05)),
        "yuzdelikler": {
            "p05": float(pc.quantile(0.05)),
            "p50": float(pc.quantile(0.50)),
            "p95": float(pc.quantile(0.95)),
        },
        "vade": vade,
    }
