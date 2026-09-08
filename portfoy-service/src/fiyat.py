"""Fiyat serisi kaynagi: market-data servisi (yerel merkezi CSV deposu)."""
from __future__ import annotations
import os
from typing import Optional

MARKET_DATA_URL = os.environ.get("MARKET_DATA_URL",
                                 "http://alphawise-market-data:8000")


def gunluk_kapanislar(httpx, sembol: str, limit: int = 400,
                      taban: Optional[str] = None) -> dict:
    """{gun: kapanis}. Hata durumunda BOS sozluk + gerekce doner; bos sozluk
    'fiyat sifir' demek DEGILDIR."""
    t = taban or MARKET_DATA_URL
    try:
        y = httpx.get(f"{t}/price/{sembol}", params={"limit": limit}, timeout=20.0)
        if y.status_code != 200:
            return {"fiyatlar": {}, "gerekce": f"HTTP {y.status_code}"}
        d = y.json()
    except Exception as e:
        return {"fiyatlar": {}, "gerekce": f"{type(e).__name__}"}
    if isinstance(d, dict) and d.get("error"):
        return {"fiyatlar": {}, "gerekce": str(d["error"])[:120]}
    cikti = {}
    for satir in (d.get("data") or []):
        gun = str(satir.get("date", ""))[:10]
        try:
            kapanis = float(satir.get("close"))
        except (TypeError, ValueError):
            continue
        if gun and kapanis > 0:
            cikti[gun] = kapanis
    return {"fiyatlar": cikti, "gerekce": "" if cikti else "veri bos"}
