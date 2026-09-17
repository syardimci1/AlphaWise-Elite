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


class KuyrukOlasiligiHatasi(ValueError):
    """Bu modulun kendi girdi dogrulama hatalari (negatif fiyat, yetersiz
    strike). main.py yalnizca BU tipi 422'ye cevirir; oipd/pandas'tan
    gelen diger ValueError'lar (ic detay icerebilir) 502'ye duser."""


def openbb_zincirini_oipd_bicimine_cevir(kontratlar: list[dict], vade: str) -> pd.DataFrame:
    """openbb /derivatives/options/chains formatindan (dex_vanna.py'nin de
    kullandigi alan adlari: strike, option_type, expiration, last_trade_price)
    oipd'nin ProbCurve.from_chain bekledigi tek-vadeli uzun-formata cevirir.

    Yalnizca `vade`ye esit expiration'lu kontratlar alinir (oipd tek vade
    ister, ProbCurve.from_chain coklu vadede ValueError firlatir). Eksik/
    sayisal-olmayan last_trade_price'li kontratlar SESSIZCE atlanir (tek
    likit-olmayan strike TUM istegi dusurmemeli) - strike/option_type ise
    zincirde HER ZAMAN dolu olan zorunlu alanlardir (dex_vanna.py ile ayni
    varsayim)."""
    satirlar = []
    for k in kontratlar:
        if str(k.get("expiration")) != vade:
            continue
        fiyat = k.get("last_trade_price")
        if fiyat is None:
            continue
        try:
            fiyat = float(fiyat)
        except (TypeError, ValueError):
            continue
        satirlar.append({
            "strike": float(k["strike"]),
            "option_type": str(k["option_type"]).lower(),
            "last_price": fiyat,
            "expiry": vade,
        })
    return pd.DataFrame(satirlar, columns=["strike", "option_type", "last_price", "expiry"])


def hesapla(kontratlar: list[dict], spot: float, risksiz_oran: float,
           vade: str, degerleme_tarihi: str) -> dict:
    """Risk-notr olasilik dagilimini hesaplar. Audit #6'daki B4 kirma
    bulgularini (negatif fiyat, yetersiz strike -> KuyrukOlasiligiHatasi)
    DEGISTIRMEDEN disariya tasir - servis (main.py) bunlari HTTPException
    422'ye cevirir; oipd/pandas'tan gelen diger ValueError'lar (KuyrukOlasiligiHatasi
    DEGIL) main.py'de 502'ye duser (ic detay sizdirmamak icin)."""
    chain = openbb_zincirini_oipd_bicimine_cevir(kontratlar, vade)
    if chain["strike"].nunique() < 5:
        raise KuyrukOlasiligiHatasi(
            f"Yetersiz opsiyon verisi: en az 5 strike gerekli, {chain['strike'].nunique()} bulundu")
    if (chain["last_price"] < 0).any():
        raise KuyrukOlasiligiHatasi("Opsiyon zincirinde negatif fiyat var")

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
