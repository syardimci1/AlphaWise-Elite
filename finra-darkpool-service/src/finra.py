"""
ALPHAWISE - FINRA ATS (Dark Pool) Transparency istemcisi.

Kaynak: https://api.finra.org  (developer.finra.org)
KIMLIK DOGRULAMA: GEREKMIYOR. 18.08.2026'da gercek istekle dogrulandi -
anonim GET/POST istekleri HTTP 200 donuyor. API anahtari YOK.

Veri kumesi: otcMarket / weeklySummary
  Bolum (partition) anahtarlari: weekStartDate, tierIdentifier
  ONEMLI: API, sortFields kullanimina yalnizca TUM bolum anahtarlari EQUAL
  filtresiyle verildiginde izin verir; aksi halde HTTP 400 doner. Bu yuzden
  sorgularda ya sortFields kullanilmaz ya da bolum anahtarlari tam verilir.

summaryTypeCode degerleri:
  ATS_W_SMBL      -> Sembolun TUM ATS (dark pool) haftalik toplami
  ATS_W_SMBL_FIRM -> ATS bazinda kirilim (MPID ile)
  OTC_W_SMBL      -> Sembolun tum tezgahustu (ATS + ATS disi) toplami
  OTC_W_SMBL_FIRM -> ATS disi tezgahustu isleme gore firma kirilimi
"""
import os
import json

import httpx
import redis

FINRA_BASE = os.getenv("FINRA_BASE_URL", "https://api.finra.org")
DATASET_PATH = "/data/group/otcMarket/name/weeklySummary"
PARTITION_PATH = "/partitions/group/otcMarket/name/weeklySummary"
HTTP_TIMEOUT = float(os.getenv("FINRA_TIMEOUT", "45"))
CACHE_PREFIX = "finra:dp:"

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


async def kimlik_dogrulama_testi() -> dict:
    """
    FINRA API'sinin kimlik dogrulama isteyip istemedigini CANLI istekle sinar.
    Hicbir anahtar/başlik gondermez.
    """
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        try:
            resp = await client.get(
                f"{FINRA_BASE}{DATASET_PATH}",
                params={"limit": 1},
                headers={"Accept": "application/json"},
            )
            return {
                "http_status": resp.status_code,
                "kimlik_dogrulama_gerekli": resp.status_code in (401, 403),
                "anonim_erisim_calisiyor": resp.status_code == 200,
                "api_anahtari_gerekli_mi": "HAYIR" if resp.status_code == 200 else "BELIRSIZ",
            }
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}"}


async def _sorgula(gövde: dict) -> list:
    """Veri kumesine POST sorgusu atar; her zaman liste doner."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.post(
            f"{FINRA_BASE}{DATASET_PATH}",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            json=gövde,
        )
        # FINRA, eslesen kayit yoksa 204 No Content doner - bu bir hata degildir.
        if resp.status_code == 204:
            return []
        if resp.status_code != 200:
            raise RuntimeError(f"FINRA HTTP {resp.status_code}: {resp.text[:300]}")
        if not resp.content:
            return []
        veri = resp.json()
        return veri if isinstance(veri, list) else []


async def mevcut_haftalar(force: bool = False) -> dict:
    """
    Yayinlanmis (weekStartDate, tierIdentifier) bolumleri.
    FINRA ATS verisi gecikmelidir: T1 ~2 hafta, T2 ~4 hafta.
    6 saat onbellekli.
    """
    cache_key = "partitions"
    if not force:
        cached = _cache_get(cache_key)
        if cached is not None:
            cached["_cache_hit"] = True
            return cached

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(f"{FINRA_BASE}{PARTITION_PATH}", headers={"Accept": "application/json"})
        if resp.status_code != 200:
            raise RuntimeError(f"FINRA partitions HTTP {resp.status_code}: {resp.text[:200]}")
        veri = resp.json()

    ciftler = [p.get("partitions", []) for p in veri.get("availablePartitions", [])]
    haftalar = sorted({p[0] for p in ciftler if len(p) >= 1}, reverse=True)
    tierler = sorted({p[1] for p in ciftler if len(p) >= 2})
    sonuc = {
        "en_son_hafta": haftalar[0] if haftalar else None,
        "hafta_sayisi": len(haftalar),
        "haftalar": haftalar,
        "tierler": tierler,
        "_cache_hit": False,
    }
    _cache_set(cache_key, sonuc, ttl_seconds=6 * 3600)
    return sonuc


async def haftalik_kayitlar(ticker: str, hafta: str) -> list:
    """
    Bir sembolun belirli haftadaki TUM weeklySummary kayitlari
    (ATS toplami, ATS firma kirilimi, OTC toplami, OTC firma kirilimi).
    Tier bilinmedigi icin bolum anahtari olarak yalnizca weekStartDate verilir;
    sortFields KULLANILMAZ (aksi halde API 400 doner).
    7 gun onbellekli - yayinlanmis haftalik veri degismez.
    """
    ticker = ticker.upper().strip()
    cache_key = f"rows:{ticker}:{hafta}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    gövde = {
        "limit": 1000,
        "compareFilters": [
            {"fieldName": "issueSymbolIdentifier", "fieldValue": ticker, "compareType": "EQUAL"},
            {"fieldName": "weekStartDate", "fieldValue": hafta, "compareType": "EQUAL"},
        ],
    }
    kayitlar = await _sorgula(gövde)
    _cache_set(cache_key, kayitlar, ttl_seconds=7 * 24 * 3600)
    return kayitlar


def _sayi(x):
    if x is None:
        return 0
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0


def ozetle(ticker: str, hafta: str, kayitlar: list) -> dict:
    """Ham kayitlari dark pool ozetine cevirir."""
    ats_toplam = next((r for r in kayitlar if r.get("summaryTypeCode") == "ATS_W_SMBL"), None)
    otc_toplam = next((r for r in kayitlar if r.get("summaryTypeCode") == "OTC_W_SMBL"), None)
    ats_firmalar = [r for r in kayitlar if r.get("summaryTypeCode") == "ATS_W_SMBL_FIRM"]
    otc_firmalar = [r for r in kayitlar if r.get("summaryTypeCode") == "OTC_W_SMBL_FIRM"]

    ats_hisse = _sayi(ats_toplam.get("totalWeeklyShareQuantity")) if ats_toplam else 0
    otc_hisse = _sayi(otc_toplam.get("totalWeeklyShareQuantity")) if otc_toplam else 0

    venue_listesi = sorted(
        [
            {
                "mpid": r.get("MPID"),
                "ats_adi": r.get("marketParticipantName"),
                "shares": int(_sayi(r.get("totalWeeklyShareQuantity"))),
                "trades": r.get("totalWeeklyTradeCount"),
                "notional_usd": _sayi(r.get("totalNotionalSum")) or None,
                "ats_ici_pay_yuzde": round(_sayi(r.get("totalWeeklyShareQuantity")) / ats_hisse * 100, 2)
                if ats_hisse
                else None,
            }
            for r in ats_firmalar
        ],
        key=lambda z: z["shares"],
        reverse=True,
    )

    ornek = ats_toplam or otc_toplam or (kayitlar[0] if kayitlar else {})
    return {
        "ticker": ticker.upper(),
        "week_start_date": hafta,
        "veri_var": bool(kayitlar),
        "issue_name": ornek.get("issueName"),
        "tier": ornek.get("tierIdentifier"),
        "tier_aciklama": ornek.get("tierDescription"),
        "son_bildirim_tarihi": ornek.get("lastReportedDate"),
        "ilk_yayin_tarihi": ornek.get("initialPublishedDate"),
        "dark_pool": {
            "ats_toplam_shares": int(ats_hisse),
            "ats_toplam_trades": ats_toplam.get("totalWeeklyTradeCount") if ats_toplam else None,
            "ats_toplam_notional_usd": _sayi(ats_toplam.get("totalNotionalSum")) if ats_toplam else None,
            "ats_ortalama_islem_buyuklugu": round(ats_hisse / ats_toplam["totalWeeklyTradeCount"], 1)
            if ats_toplam and ats_toplam.get("totalWeeklyTradeCount")
            else None,
            "aktif_ats_sayisi": len(ats_firmalar),
        },
        "otc_toplam": {
            "otc_toplam_shares": int(otc_hisse),
            "otc_toplam_trades": otc_toplam.get("totalWeeklyTradeCount") if otc_toplam else None,
            "otc_disi_firma_sayisi": len(otc_firmalar),
        },
        "ats_orani_yuzde": round(ats_hisse / otc_hisse * 100, 2) if otc_hisse else None,
        "venues": venue_listesi,
    }
