"""
LLMQuant Data client - iki API anahtarli otomatik yedekleme (fallback) ile.
Anahtarlardan biri limite/hataya takilirsa otomatik digerine gecer.
"""
import os
import json
import httpx
import redis

_redis_client = None

def _get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True,
        )
    return _redis_client


def _cache_get(key):
    try:
        val = _get_redis().get(key)
        return json.loads(val) if val else None
    except Exception:
        return None


def _cache_set(key, value, ttl_seconds):
    try:
        _get_redis().setex(key, ttl_seconds, json.dumps(value))
    except Exception:
        pass
import asyncio

LLMQUANT_BASE_URL = "https://api.llmquantdata.com"

def _get_api_keys():
    keys = []
    k1 = os.getenv("LLMQUANT_API_KEY_1")
    k2 = os.getenv("LLMQUANT_API_KEY_2")
    if k1:
        keys.append(k1)
    if k2:
        keys.append(k2)
    return keys


async def _llmquant_get(path: str, params: dict):
    """
    Verilen endpoint'e GET istegi atar. Ilk anahtar basarisiz olursa
    (401/402/403/429 gibi kota/yetki hatalari) otomatik ikinci anahtari dener.
    """
    keys = _get_api_keys()
    if not keys:
        return {"error": "LLMQUANT_API_KEY_1/2 tanimli degil"}

    last_error = None
    async with httpx.AsyncClient(timeout=15.0) as client:
        for idx, key in enumerate(keys):
            try:
                resp = await client.get(
                    f"{LLMQUANT_BASE_URL}{path}",
                    headers={"Authorization": f"Bearer {key}"},
                    params=params,
                )
                if resp.status_code == 200:
                    return resp.json()
                # Kota/yetki hatasi ise siradaki anahtara gec
                if resp.status_code in (401, 402, 403, 429):
                    last_error = f"Anahtar #{idx+1} basarisiz (HTTP {resp.status_code}), digeri deneniyor..."
                    continue
                # Baska bir hata (404 vb.) - anahtar sorunu degil, direkt don
                return {"error": f"HTTP {resp.status_code}", "detail": resp.text[:300]}
            except Exception as e:
                last_error = f"Anahtar #{idx+1} istisna: {e}"
                continue

    return {"error": "Tum LLMQuant anahtarlari basarisiz oldu", "last_error": last_error}


async def get_13f_holders(ticker: str, limit: int = 30):
    """Tickeri elinde tutan en buyuk kurumsal yatirimcilar (Top 1000 icinden). 7 gun onbellekli."""
    cache_key = f"llmquant:13f:{ticker}:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        cached["_cache_hit"] = True
        return cached

    result = await _llmquant_get(
        "/api/filings/13f/by-ticker",
        {"ticker": ticker, "limit": limit},
    )
    if "error" not in result:
        _cache_set(cache_key, result, ttl_seconds=7 * 24 * 3600)
    return result


async def get_macro_snapshot(indicator: str):
    """Tek bir makro gostergenin son degeri (ucretsiz endpoint, kredi harcamaz)."""
    return await _llmquant_get(
        "/api/macro/snapshot",
        {"indicator": indicator},
    )


async def get_macro_snapshot_by_series_id(series_id: str):
    """Ham FRED seri ID'siyle sorgu (platform alias yerine)."""
    return await _llmquant_get("/api/macro/snapshot", {"series_id": series_id})


async def get_liquidity_context():
    """
    M2Quant/Net Likidite metodolojisi: Fed Bilancosu (WALCL) - Ters Repo (RRPONTSYD).
    Ham FRED seri ID'leri kullanilir (platform alias'lari yerine, daha guvenilir).
    6 saat onbellekli.
    """
    cache_key = "llmquant:liquidity"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    balance_sheet, rrp = await asyncio.gather(
        get_macro_snapshot_by_series_id("WALCL"),
        get_macro_snapshot_by_series_id("RRPONTSYD"),
    )
    result = {"fed_balance_sheet": balance_sheet, "reverse_repo": rrp}
    _cache_set(cache_key, result, ttl_seconds=6 * 3600)
    return result
