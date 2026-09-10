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

# --- ANAHTARSIZ YEDEK KAYNAK (madde 44, 10.09.2026) ---
# FRED bu servisin BIRINCIL kaynagidir ve DEGISMEDI. dbnomics.py yalnizca
# FRED BASARISIZ oldugunda ve YALNIZCA degerleri birebir dogrulanmis
# seriler icin devreye girer.
#
# CANLI CAPRAZ DOGRULAMA (10.09.2026, bu baglantidan ONCE yeniden yapildi):
#   WALCL, 2026 yilinin 35 ortak gozleminde FRED ile DBnomics BIREBIR ayni
#   (azami mutlak fark 0,0; 35/35 esit).
#
# ONCEKI RAPOR DUZELTILDI: 16f0179 commit'i "DBnomics daha taze" diyordu
# (2026-09-02 vs 2026-08-12). O karsilastirma BAYAT bir FRED ONBELLEK
# dosyasina karsi yapilmisti. CANLI FRED'e karsi olculdugunde FRED DAHA
# TAZE cikiyor (2026-09-09 vs 2026-09-02). Yani DBnomics bir TAZELIK
# yukseltmesi DEGIL, bir ERISILEBILIRLIK yedegidir.
YEDEK_ETKIN = os.getenv("DBNOMICS_YEDEK_ETKIN", "1") not in ("0", "false", "False")

# Yedekten gelen veri DAHA KISA sure onbelleklenir: FRED duzelir duzelmez
# birincil kaynaga donulsun, 6 saat boyunca yedege kilitlenmeyelim.
YEDEK_ONBELLEK_SANIYE = int(os.getenv("DBNOMICS_ONBELLEK_SN", "1800"))

# Yedegin ne zaman/nicin devreye girdigi SESSIZ kalmaz; /health bunu gosterir.
_yedek_kullanimi: dict = {}

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


def yedek_durumu() -> dict:
    """Anahtarsiz yedegin (DBnomics) hali - /health bunu gosterir.

    Yedegin devreye girmesi SESSIZ bir olay OLMAMALIDIR: hangi seride,
    ne zaman, hangi FRED hatasi yuzunden devreye girdigi gorunur olmali.
    """
    try:
        from . import dbnomics
        eslesme = dbnomics.eslesme_durumu()
    except Exception as e:  # noqa: BLE001
        return {"etkin": YEDEK_ETKIN, "kullanilabilir": False,
                "hata": f"{type(e).__name__}: {str(e)[:120]}"}
    return {
        "etkin": YEDEK_ETKIN,
        "kullanilabilir": True,
        "kaynak": eslesme["kaynak"],
        "dogrulanmis_seriler": sorted(eslesme["eslesmeler"]),
        "onbellek_saniye": YEDEK_ONBELLEK_SANIYE,
        "son_kullanim": dict(_yedek_kullanimi),
        "not": ("FRED BIRINCIL kaynaktir. Yedek yalnizca FRED basarisiz "
                "oldugunda VE seri icin degerleri birebir dogrulanmis bir "
                "eslesme varsa devreye girer. Dogrulanmamis seri icin "
                "TAHMIN YAPILMAZ - orijinal FRED hatasi firlatilir."),
    }


async def _fred_serisi_cek(series_id: str, start_date: str) -> List[Tuple[str, float]]:
    """Yalnizca FRED - davranisi DEGISMEDI (eski fetch_series govdesi)."""
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
    logger.info("FRED %s: %d gozlem cekildi", series_id, len(obs))
    return obs


async def fetch_series(series_id: str, start_date: str = "2020-01-01") -> List[Tuple[str, float]]:
    """
    Verilen FRED serisini ceker. Sonuc [(YYYY-MM-DD, deger), ...] listesi.
    Sirali, artan tarih. Eksik degerler ('.') filtrelenmis. Onbellekli.

    ARIZA YONU (madde 44, 10.09.2026): FRED basarisiz olursa - anahtar
    yoksa ya da HTTP/ag hatasi olursa - ANAHTARSIZ yedek (DBnomics)
    denenir. Bu servis ACIKCA tavsiye niteligindedir ("yon karari icin
    girdi olarak KULLANILMAMALIDIR", bkz. /health) ve bu yuzden fail-open
    dogru aria yonudur: veri YOK yerine, degerleri BIREBIR dogrulanmis
    ayni veri.

    Yedek YALNIZCA dogrulanmis seriler icin calisir. Dogrulanmamis bir
    seride DBnomics'e sorulmaz bile - ORIJINAL FRED hatasi firlatilir,
    cunku tahmini bir eslesme sessizce yanlis makro veri beslerdi.
    """
    cache_key = f"series:{series_id}:{start_date}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return [(d, v) for d, v in cached]

    try:
        obs = await _fred_serisi_cek(series_id, start_date)
        _cache_set(cache_key, obs, ttl_seconds=6 * 3600)
        _yedek_kullanimi.pop(series_id, None)   # FRED duzeldi -> kayit temizlenir
        return obs
    except Exception as fred_hatasi:  # noqa: BLE001
        if not YEDEK_ETKIN:
            raise
        try:
            yedek = await _yedekten_cek(series_id, start_date)
        except Exception as yedek_hatasi:  # noqa: BLE001
            # Yedek de olmadi: ORIJINAL FRED hatasini firlat, yedegin
            # hatasi onu MASKELEMESIN (kok neden FRED'dir).
            logger.warning("FRED %s basarisiz (%s); yedek de basarisiz (%s)",
                           series_id, fred_hatasi, yedek_hatasi)
            raise fred_hatasi
        _yedek_kullanimi[series_id] = {
            "kaynak": "dbnomics",
            "fred_hatasi": f"{type(fred_hatasi).__name__}: {str(fred_hatasi)[:150]}",
            "gozlem": len(yedek),
        }
        logger.warning("FRED %s basarisiz (%s) -> ANAHTARSIZ YEDEK (DBnomics) "
                       "kullanildi, %d gozlem", series_id, fred_hatasi, len(yedek))
        # Yedek verisi KISA sureli onbelleklenir - FRED duzelince hemen donulsun.
        _cache_set(cache_key, yedek, ttl_seconds=YEDEK_ONBELLEK_SANIYE)
        return yedek


async def _yedekten_cek(series_id: str, start_date: str) -> List[Tuple[str, float]]:
    """DBnomics'ten cek ve FRED ile AYNI sekle getir.

    start_date SUZGECI SART: FRED 'observation_start' ile suzuyor, DBnomics
    tum seriyi (1238 gozlem, 2002'den beri) donduruyor. Suzmezsek asagi
    akistaki hesaplar FRED yolunda gormedigi bir pencereyle calisirdi.
    """
    from . import dbnomics
    ham = await dbnomics.seri_getir(series_id)
    suzulmus = [(t, v) for t, v in ham if t >= start_date]
    suzulmus.sort(key=lambda x: x[0])
    return suzulmus


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
