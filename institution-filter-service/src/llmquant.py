"""
ALPHAWISE - Institution Filter Service / LLMQuant istemcisi.

maa/src/llmquant_client.py'deki cift-anahtarli yedekleme (fallback) desenini
referans alir; ancak MAA kaskadindan tamamen BAGIMSIZ bir kopyadir.
Onbellek anahtarlari "ifs:" on ekiyle ayrilmistir; MAA'nin "llmquant:*"
onbellegiyle carpismaz.
"""
import os
import json
import asyncio
import logging

import httpx
import redis

logger = logging.getLogger("institution-filter.llmquant")

LLMQUANT_BASE_URL = os.getenv("LLMQUANT_BASE_URL", "https://api.llmquantdata.com")
HTTP_TIMEOUT = float(os.getenv("LLMQUANT_TIMEOUT", "30"))
CACHE_PREFIX = "ifs:"

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
    """Onbellek baglantisinin canli olup olmadigini bildirir (health icin)."""
    try:
        _get_redis().ping()
        return {"connected": True}
    except Exception as e:
        return {"connected": False, "detail": str(e)[:200]}


def _get_api_keys():
    keys = []
    for isim in ("LLMQUANT_API_KEY_1", "LLMQUANT_API_KEY_2"):
        deger = os.getenv(isim)
        if deger:
            keys.append((isim, deger))
    return keys


def anahtar_durumu() -> dict:
    """Hangi anahtarlarin tanimli oldugunu (degerini sizdirmadan) bildirir."""
    tanimli = [isim for isim, _ in _get_api_keys()]
    return {
        "LLMQUANT_API_KEY_1": "LLMQUANT_API_KEY_1" in tanimli,
        "LLMQUANT_API_KEY_2": "LLMQUANT_API_KEY_2" in tanimli,
        "eksik": [
            isim
            for isim in ("LLMQUANT_API_KEY_1", "LLMQUANT_API_KEY_2")
            if isim not in tanimli
        ],
    }


async def anahtar_dogrula() -> dict:
    """Her anahtari API'ye karsi dogrular (0 kredi, /managers?limit=1)."""
    keys = _get_api_keys()
    sonuclar = {}
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        for isim, key in keys:
            try:
                resp = await client.get(
                    f"{LLMQUANT_BASE_URL}/api/filings/13f/managers",
                    headers={"Authorization": f"Bearer {key}"},
                    params={"limit": 1},
                )
                if resp.status_code == 200:
                    meta = resp.json().get("meta", {}) or {}
                    sonuclar[isim] = {
                        "gecerli": True,
                        "http_status": 200,
                        "kalan_kredi": meta.get("remainingCredits"),
                    }
                    logger.info("%s gecerli (kredi: %s)", isim, meta.get("remainingCredits"))
                else:
                    sonuclar[isim] = {
                        "gecerli": False,
                        "http_status": resp.status_code,
                        "detay": resp.text[:200],
                    }
                    logger.warning(
                        "ANAHTAR GECERSIZ: %s HTTP %d — %s",
                        isim, resp.status_code, resp.text[:200],
                    )
            except Exception as e:
                sonuclar[isim] = {
                    "gecerli": False,
                    "http_status": None,
                    "detay": f"{type(e).__name__}: {e}",
                }
                logger.warning("ANAHTAR DOGRULAMA HATASI: %s — %s", isim, e)

    for isim in ("LLMQUANT_API_KEY_1", "LLMQUANT_API_KEY_2"):
        if isim not in sonuclar:
            sonuclar[isim] = {"gecerli": False, "http_status": None, "detay": "tanimli degil"}

    gecerli_sayisi = sum(1 for v in sonuclar.values() if v.get("gecerli"))
    if gecerli_sayisi == 0:
        logger.error("KRITIK: Hicbir LLMQuant anahtari gecerli degil!")
    elif gecerli_sayisi < len(keys):
        logger.warning(
            "UYARI: %d/%d anahtar gecersiz — yedekleme calismayacak",
            len(keys) - gecerli_sayisi, len(keys),
        )
    return sonuclar


async def llmquant_get(path: str, params: dict) -> dict:
    """
    Verilen endpoint'e GET atar. Ilk anahtar kota/yetki hatasi verirse
    (401/402/403/429) otomatik olarak ikinci anahtara gecer.
    """
    keys = _get_api_keys()
    if not keys:
        return {"error": "LLMQUANT_API_KEY_1/2 tanimli degil"}

    last_error = None
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        for idx, (isim, key) in enumerate(keys):
            try:
                resp = await client.get(
                    f"{LLMQUANT_BASE_URL}{path}",
                    headers={"Authorization": f"Bearer {key}"},
                    params=params,
                )
                if resp.status_code == 200:
                    veri = resp.json()
                    if isinstance(veri, dict):
                        veri.setdefault("_kullanilan_anahtar", isim)
                    return veri
                if resp.status_code in (401, 402, 403, 429):
                    last_error = (
                        f"{isim} basarisiz (HTTP {resp.status_code}), digeri deneniyor"
                    )
                    logger.warning(
                        "%s %s basarisiz (HTTP %d), fallback deneniyor",
                        isim, path, resp.status_code,
                    )
                    continue
                return {
                    "error": f"HTTP {resp.status_code}",
                    "detail": resp.text[:300],
                }
            except Exception as e:
                last_error = f"{isim} istisna: {type(e).__name__}: {e}"
                logger.warning("%s %s istisna: %s", isim, path, e)
                continue

    logger.error("Tum LLMQuant anahtarlari basarisiz: %s", last_error)
    return {"error": "Tum LLMQuant anahtarlari basarisiz oldu", "last_error": last_error}


# --- Onbellekli sarmalayicilar ---------------------------------------------

async def kapsanan_yoneticiler(limit: int = 1000) -> dict:
    """
    Ilgili ceyregin Top-1000 yonetici kumesi (isim + alias + CIK).
    Bu endpoint KREDI HARCAMAZ (creditsUsed: 0). 24 saat onbellekli.
    """
    cache_key = f"managers:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        cached["_cache_hit"] = True
        return cached

    sonuc = await llmquant_get("/api/filings/13f/managers", {"limit": limit})
    if "error" not in sonuc:
        _cache_set(cache_key, sonuc, ttl_seconds=24 * 3600)
    return sonuc


async def hisse_sahipleri(ticker: str, limit: int = 1000) -> dict:
    """
    maa/src/llmquant_client.py::get_13f_holders ile ayni endpoint:
    /api/filings/13f/by-ticker - tickeri tutan Top-1000 yoneticiler.
    1 kredi harcar. 7 gun onbellekli.
    """
    cache_key = f"13f:by-ticker:{ticker.upper()}:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        cached["_cache_hit"] = True
        return cached

    sonuc = await llmquant_get(
        "/api/filings/13f/by-ticker", {"ticker": ticker.upper(), "limit": limit}
    )
    if "error" not in sonuc:
        _cache_set(cache_key, sonuc, ttl_seconds=7 * 24 * 3600)
    return sonuc


async def yonetici_portfoyu(manager_cik: str, limit: int = 500) -> dict:
    """
    /api/filings/13f/by-manager - tek bir yoneticinin en son 13F portfoyu.
    ONEMLI: API 'offset' parametresini yok sayar ve 'limit' degerini 500'de
    kirpar; yani en buyuk 500 pozisyon gorulebilir (deger sirali).
    1 kredi harcar. 7 gun onbellekli.
    """
    limit = min(limit, 500)
    cache_key = f"13f:by-manager:{manager_cik}:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        cached["_cache_hit"] = True
        return cached

    sonuc = await llmquant_get(
        "/api/filings/13f/by-manager", {"manager_cik": str(manager_cik), "limit": limit}
    )
    if "error" not in sonuc:
        _cache_set(cache_key, sonuc, ttl_seconds=7 * 24 * 3600)
    return sonuc
