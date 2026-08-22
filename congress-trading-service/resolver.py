"""
ALPHAWISE - Congress Trading Service / kaynak zinciri ve normallestirme (19.08.2026)

Iki kaynakli otomatik yedekleme (fallback). Bugun llmquant_client.py'de kurulan
"birincil basarisiz olursa sessizce yedege dus" mantiginin aynisi:

  1) BIRINCIL : Quiver Quantitative  (api.quiverquant.com, QUIVER_API_KEY)
  2) YEDEK    : Financial Modeling Prep (stable/senate-latest + house-latest)

Gecis kosullari: zaman asimi (varsayilan 5 sn), HTTP 401/403/429/5xx, baglanti
hatasi. Her yanitta hangi kaynagin kullanildigi "source" alaninda bildirilir.

KAYNAK NOTLARI (19.08.2026 canli testle dogrulandi):
- Quiver: eldeki anahtar kimlik dogrulamasindan geciyor (anahtarsiz 401,
  anahtarli 403) ancak abonelik HICBIR veri setini kapsamiyor; test edilen 9
  endpoint'in tamami 403 "Upgrade your subscription plan" donuyor. Yani birincil
  kaynak su an fiilen kapali ve zincir her istekte yedege dusuyor. Plan
  yukseltilirse kod degisikligi gerekmeden devreye girer.
- FMP: /stable/senate-latest ve /stable/house-latest ucretsiz katmanda calisiyor
  (HTTP 200, meclis basina 100 kayit). Sembol/isim filtreli uclar ve sayfalama
  parametreleri ucretli (402), bu yuzden filtreleme SERVIS ICINDE yapilir.
"""
import os
import re
import json
import asyncio

import httpx
import redis

QUIVER_BASE = os.getenv("QUIVER_BASE_URL", "https://api.quiverquant.com")
FMP_BASE = os.getenv("FMP_BASE_URL", "https://financialmodelingprep.com")
BIRINCIL_TIMEOUT = float(os.getenv("PRIMARY_TIMEOUT", "5"))   # kural: 5 saniye
YEDEK_TIMEOUT = float(os.getenv("FALLBACK_TIMEOUT", "30"))
CACHE_PREFIX = "congress:"                                     # kural: congress: on eki

GECIS_KODLARI = {401, 403, 429}

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


def _cache_get(key):
    try:
        v = _get_redis().get(CACHE_PREFIX + key)
        return json.loads(v) if v else None
    except Exception:
        return None


def _cache_set(key, value, ttl_seconds):
    try:
        _get_redis().setex(CACHE_PREFIX + key, ttl_seconds, json.dumps(value))
    except Exception:
        pass


def redis_durumu():
    try:
        _get_redis().ping()
        return {"connected": True}
    except Exception as e:
        return {"connected": False, "detail": str(e)[:200]}


def anahtar_durumu():
    return {
        "QUIVER_API_KEY": bool(os.getenv("QUIVER_API_KEY")),
        "FMP_API_KEY": bool(os.getenv("FMP_API_KEY")),
        "eksik": [k for k in ("QUIVER_API_KEY", "FMP_API_KEY") if not os.getenv(k)],
    }


# --- Tutar araligi ayristirma ------------------------------------------------

def _tutar_ayristir(metin):
    """
    STOCK Act tutar araligini ayristirir.
    '$1,001 - $15,000' -> (1001, 15000, 8000.5)
    '$1,000,001 - $5,000,000' -> (1000001, 5000000, 3000000.5)
    Tek degerli ifadelerde alt=ust olur.
    ONEMLI: binlik ayirici virgul ONCE temizlenir; aksi halde '1,001' iki ayri
    sayi (1 ve 001) olarak okunur ve tutarlar tamamen yanlis cikar.
    """
    if not metin:
        return None, None, None
    temiz = str(metin).replace(",", "").replace("$", "")
    sayilar = [int(g) for g in re.findall(r"\d+", temiz)]
    if not sayilar:
        return None, None, None
    alt = sayilar[0]
    ust = sayilar[1] if len(sayilar) > 1 else sayilar[0]
    if ust < alt:
        alt, ust = ust, alt
    return alt, ust, (alt + ust) / 2


def _normalize_ad(s):
    return " ".join((s or "").lower().split())


# --- Normallestirme: her iki kaynak da ayni semaya cevrilir -------------------

def _fmp_normalize(kayit, meclis):
    ad = kayit.get("office") or " ".join(
        x for x in (kayit.get("firstName"), kayit.get("lastName")) if x
    )
    alt, ust, orta = _tutar_ayristir(kayit.get("amount"))
    return {
        "member": ad,
        "first_name": kayit.get("firstName"),
        "last_name": kayit.get("lastName"),
        "chamber": meclis,
        "district": kayit.get("district"),
        "ticker": (kayit.get("symbol") or "").upper() or None,
        "asset_description": kayit.get("assetDescription"),
        "asset_type": kayit.get("assetType"),
        "transaction_type": kayit.get("type"),
        "transaction_date": kayit.get("transactionDate"),
        "disclosure_date": kayit.get("disclosureDate"),
        "amount_range": kayit.get("amount"),
        "amount_min_usd": alt,
        "amount_max_usd": ust,
        "amount_mid_usd": orta,
        "owner": kayit.get("owner"),
        "comment": kayit.get("comment") or None,
        "source_link": kayit.get("link"),
    }


def _quiver_normalize(kayit):
    """
    Quiver congresstrading semasi. DIKKAT: eldeki abonelik bu veri setini
    kapsamadigi icin (403) bu esleme CANLI VERIYLE DOGRULANAMADI; Quiver'in
    belgelenmis alan adlarina gore yazildi ve plan yukseltildiginde
    dogrulanmalidir.
    """
    ad = kayit.get("Representative") or kayit.get("Name") or kayit.get("Senator")
    ham_tutar = kayit.get("Range") or kayit.get("Amount")
    alt, ust, orta = _tutar_ayristir(ham_tutar)
    meclis = kayit.get("House") or kayit.get("Chamber")
    return {
        "member": ad,
        "first_name": None,
        "last_name": None,
        "chamber": "Senate" if str(meclis).lower().startswith("sen") else ("House" if meclis else None),
        "district": kayit.get("District") or kayit.get("State"),
        "ticker": (kayit.get("Ticker") or "").upper() or None,
        "asset_description": kayit.get("AssetDescription") or kayit.get("Description"),
        "asset_type": kayit.get("AssetType"),
        "transaction_type": kayit.get("Transaction"),
        "transaction_date": kayit.get("TransactionDate") or kayit.get("Date"),
        "disclosure_date": kayit.get("ReportDate") or kayit.get("Disclosure"),
        "amount_range": ham_tutar,
        "amount_min_usd": alt,
        "amount_max_usd": ust,
        "amount_mid_usd": orta,
        "owner": kayit.get("Owner"),
        "comment": None,
        "source_link": kayit.get("Link"),
    }


# --- Kaynak 1: Quiver (BIRINCIL) --------------------------------------------

async def quiver_cek(timeout=None):
    """Basarili olursa (kayitlar, None); olmazsa (None, hata_sozlugu)."""
    key = os.getenv("QUIVER_API_KEY")
    if not key:
        return None, {"kaynak": "quiver", "neden": "QUIVER_API_KEY tanimli degil", "gecis": True}
    try:
        async with httpx.AsyncClient(timeout=timeout or BIRINCIL_TIMEOUT) as c:
            r = await c.get(
                f"{QUIVER_BASE}/beta/live/congresstrading",
                headers={"Authorization": f"Token {key}", "Accept": "application/json"},
            )
        if r.status_code == 200:
            ham = r.json()
            if not isinstance(ham, list):
                return None, {"kaynak": "quiver", "neden": "beklenmeyen govde tipi", "gecis": True}
            return [_quiver_normalize(x) for x in ham], None
        if r.status_code in GECIS_KODLARI or r.status_code >= 500:
            return None, {
                "kaynak": "quiver",
                "http_status": r.status_code,
                "neden": r.text[:160],
                "gecis": True,
            }
        return None, {"kaynak": "quiver", "http_status": r.status_code, "neden": r.text[:160], "gecis": True}
    except asyncio.TimeoutError:
        return None, {"kaynak": "quiver", "neden": f"zaman asimi (>{timeout or BIRINCIL_TIMEOUT}s)", "gecis": True}
    except Exception as e:
        return None, {"kaynak": "quiver", "neden": f"{type(e).__name__}: {str(e)[:120]}", "gecis": True}


# --- Kaynak 2: FMP (YEDEK) ---------------------------------------------------

async def _fmp_al(client, yol, meclis):
    key = os.getenv("FMP_API_KEY")
    r = await client.get(f"{FMP_BASE}{yol}", params={"apikey": key})
    if r.status_code != 200:
        raise RuntimeError(f"FMP {yol} HTTP {r.status_code}: {r.text[:120]}")
    ham = r.json()
    if not isinstance(ham, list):
        raise RuntimeError(f"FMP {yol} beklenmeyen govde")
    return [_fmp_normalize(x, meclis) for x in ham]


def _fmp_kota_artir(adet: int) -> None:
    """
    Paylasilan FMP gunluk sayacini artirir (qlib toplu cekme betigiyle
    ORTAK anahtar: "fmp:gunluk:<UTC tarih>").

    Sessizce basarisiz olur: sayac tutulamazsa bu servisin asil isi
    (kullaniciya veri dondurmek) etkilenmemeli.
    """
    try:
        import datetime

        gun = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        r = _get_redis()
        p = r.pipeline()
        p.incrby(f"fmp:gunluk:{gun}", adet)
        p.expire(f"fmp:gunluk:{gun}", 48 * 3600)
        p.execute()
    except Exception:
        pass


async def fmp_cek(timeout=None):
    key = os.getenv("FMP_API_KEY")
    if not key:
        return None, {"kaynak": "fmp", "neden": "FMP_API_KEY tanimli degil"}
    try:
        async with httpx.AsyncClient(timeout=timeout or YEDEK_TIMEOUT) as c:
            senato, temsilciler = await asyncio.gather(
                _fmp_al(c, "/stable/senate-latest", "Senate"),
                _fmp_al(c, "/stable/house-latest", "House"),
            )
        # Bu iki cagriyi ORTAK gunluk sayaca yaz. Ayni FMP anahtarini
        # qlib-service'in toplu cekme betigi de kullaniyor; o betik
        # sayaca bakip kullanici-yuzu servise ayrilan payi korumak icin
        # kendini durduruyor. Sayac tutulmazsa bekci korlemesine
        # varsayim yapmak zorunda kalirdi.
        _fmp_kota_artir(2)
        return senato + temsilciler, None
    except Exception as e:
        return None, {"kaynak": "fmp", "neden": f"{type(e).__name__}: {str(e)[:160]}"}


# --- Zincir ------------------------------------------------------------------

async def kayitlari_getir(onbellek=True):
    """
    Birincil -> yedek zinciri. Doner:
      {"source": "quiver"|"fmp", "records": [...], "fallback_used": bool,
       "primary_error": {...}|None, "cache_hit": bool}
    """
    if onbellek:
        c = _cache_get("records:v1")
        if c is not None:
            c["cache_hit"] = True
            return c

    kayitlar, hata = await quiver_cek()
    if kayitlar is not None:
        sonuc = {
            "source": "quiver",
            "source_label": "Quiver Quantitative (birincil)",
            "records": kayitlar,
            "fallback_used": False,
            "primary_error": None,
            "cache_hit": False,
        }
        _cache_set("records:v1", sonuc, ttl_seconds=3600)
        return sonuc

    kayitlar2, hata2 = await fmp_cek()
    if kayitlar2 is not None:
        sonuc = {
            "source": "fmp",
            "source_label": "Financial Modeling Prep (yedek)",
            "records": kayitlar2,
            "fallback_used": True,
            "primary_error": hata,
            "cache_hit": False,
        }
        _cache_set("records:v1", sonuc, ttl_seconds=3600)
        return sonuc

    return {
        "source": None,
        "source_label": None,
        "records": [],
        "fallback_used": True,
        "primary_error": hata,
        "fallback_error": hata2,
        "cache_hit": False,
    }


# --- Filtreler (FMP ucretsiz katmanda sunucu tarafi filtre yok) --------------

def ticker_filtrele(kayitlar, ticker):
    t = (ticker or "").upper().strip()
    return [k for k in kayitlar if (k.get("ticker") or "") == t]


def uye_filtrele(kayitlar, isim):
    q = _normalize_ad(isim)
    if not q:
        return []
    vurus = []
    for k in kayitlar:
        havuz = " ".join(
            _normalize_ad(x) for x in (k.get("member"), k.get("first_name"), k.get("last_name")) if x
        )
        if q in havuz:
            vurus.append(k)
    return vurus


def ozetle(kayitlar):
    alis = [k for k in kayitlar if (k.get("transaction_type") or "").lower().startswith("purchase")]
    satis = [k for k in kayitlar if (k.get("transaction_type") or "").lower().startswith("sale")]
    def top(xs):
        return sum(k.get("amount_mid_usd") or 0 for k in xs)
    return {
        "islem_sayisi": len(kayitlar),
        "alis_sayisi": len(alis),
        "satis_sayisi": len(satis),
        "tahmini_alis_usd_orta": top(alis),
        "tahmini_satis_usd_orta": top(satis),
        "net_usd_orta": top(alis) - top(satis),
        "farkli_uye": len({k.get("member") for k in kayitlar if k.get("member")}),
        "farkli_ticker": len({k.get("ticker") for k in kayitlar if k.get("ticker")}),
    }
