"""
ALPHAWISE - Liquidity Signal Service / FRED istemcisi.

CONSTITUTION.md'de zaten onaylı, ucretsiz kaynak (fred.stlouisfed.org).
Anahtar mevcut, ek butce gerekmez.

Onbellek anahtari 'lss:' on ekiyle diger servislerden yalıtılır.
"""
import os
import json
import logging
from typing import List, Optional, Tuple

import httpx
import redis

logger = logging.getLogger("liquidity-signal.fred")

FRED_BASE = "https://api.stlouisfed.org/fred"
HTTP_TIMEOUT = float(os.getenv("FRED_TIMEOUT", "30"))
CACHE_PREFIX = "lss:"

# FRED serileri — CONSTITUTION.md ile uyumlu, tumu ucretsiz
FRED_SERIES = {
    "walcl": "WALCL",           # Fed Total Assets — haftalik (Wed)
    "tga": "WTREGEN",           # Treasury General Account — haftalik
    "rrp": "RRPONTSYD",         # Overnight Reverse Repo — gunluk
    "m2": "M2SL",               # M2 Money Supply — aylik
    "nasdaq": "NASDAQCOM",      # Nasdaq Composite — gunluk
    "sp500": "SP500",           # S&P 500 — gunluk (10 yil kap)
    "btc": "CBBTCUSD",          # Coinbase BTC/USD — gunluk
}

_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
    return _redis_client


def _cache_get(key: str):
    try:
        val = _get_redis().get(CACHE_PREFIX + key)
        return json.loads(val) if val else None
    except Exception:
        return None


def _cache_set(key: str, value, ttl_seconds: int):
    try:
        _get_redis().setex(CACHE_PREFIX + key, ttl_seconds, json.dumps(value))
    except Exception:
        pass


def redis_durumu() -> dict:
    try:
        _get_redis().ping()
        return {"connected": True}
    except Exception as e:
        return {"connected": False, "detail": str(e)[:200]}


def _get_api_key() -> Optional[str]:
    return os.getenv("FRED_API_KEY")


def anahtar_durumu() -> dict:
    """Anahtarin varligini bildirir (degeri sizdirmadan)."""
    key = _get_api_key()
    if not key:
        return {"tanimli": False, "uzunluk": 0, "gecerli_format": False}
    return {"tanimli": True, "uzunluk": len(key), "gecerli_format": len(key) == 32}


async def anahtar_dogrula() -> dict:
    """Anahtari canli sorgulayarak dogrula (0-maliyetli, 1 gozlem)."""
    key = _get_api_key()
    if not key:
        return {"gecerli": False, "http_status": None, "detay": "FRED_API_KEY tanimli degil"}
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        try:
            resp = await client.get(
                f"{FRED_BASE}/series/observations",
                params={"series_id": "WALCL", "api_key": key,
                        "file_type": "json", "limit": 1, "sort_order": "desc"},
            )
            if resp.status_code == 200:
                data = resp.json()
                obs = data.get("observations", [])
                logger.info("FRED anahtari gecerli (%d gozlem)", len(obs))
                return {"gecerli": True, "http_status": 200}
            logger.warning("FRED anahtari gecersiz — HTTP %d: %s",
                          resp.status_code, resp.text[:200])
            return {"gecerli": False, "http_status": resp.status_code,
                    "detay": resp.text[:200]}
        except Exception as e:
            logger.warning("FRED dogrulama istisnasi: %s", e)
            return {"gecerli": False, "http_status": None,
                    "detay": f"{type(e).__name__}: {e}"}


async def fetch_series(series_id: str, start_date: str = "2020-01-01") -> List[Tuple[str, float]]:
    """
    Verilen FRED serisini ceker. Sonuc [(YYYY-MM-DD, deger), ...] listesi.
    Sıralı, artan tarih. Eksik degerler ('.') filtrelenmis.
    6 saat onbellekli.
    """
    cache_key = f"series:{series_id}:{start_date}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return [(d, v) for d, v in cached]

    key = _get_api_key()
    if not key:
        raise RuntimeError("FRED_API_KEY tanimli degil")

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(
            f"{FRED_BASE}/series/observations",
            params={
                "series_id": series_id, "api_key": key,
                "file_type": "json", "observation_start": start_date,
            },
        )
        if resp.status_code != 200:
            logger.error("FRED %s cekimi basarisiz: HTTP %d — %s",
                        series_id, resp.status_code, resp.text[:200])
            raise RuntimeError(f"FRED HTTP {resp.status_code}")

        data = resp.json()
        obs = []
        for o in data.get("observations", []):
            v = o.get("value")
            if v in (".", "", None):
                continue
            try:
                obs.append((o["date"], float(v)))
            except (ValueError, KeyError):
                continue

    obs.sort(key=lambda x: x[0])
    _cache_set(cache_key, obs, ttl_seconds=6 * 3600)
    logger.info("FRED %s: %d gozlem cekildi", series_id, len(obs))
    return obs


async def fetch_all_liquidity(start_date: str = "2020-01-01") -> dict:
    """Butun likidite bilesenlerini paralel ceker."""
    import asyncio
    tasks = {
        name: fetch_series(sid, start_date)
        for name, sid in FRED_SERIES.items()
    }
    results = {}
    for name, coro in tasks.items():
        try:
            results[name] = await coro
        except Exception as e:
            logger.warning("FRED %s cekilemedi: %s", name, e)
            results[name] = []
    return results
