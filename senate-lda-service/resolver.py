"""
ALPHAWISE - Senate LDA (Lobbying Disclosure Act) servisi - kaynak istemcisi (20.09.2026)

NEDEN GEREKLI (madde 35): ABD Kongre uyelerinin STOCK Act islemlerini
congress-trading-service zaten sunuyor. Bu, TAMAMEN AYRI bir kanittir:
hangi lobicilik firmasinin (registrant) hangi musteri (client) adina,
hangi konularda (issue), ne kadar harcayarak lobicilik yaptigi. Ikisi
karistirilmamali - STOCK Act (kisisel hisse islemi) ile LDA (kurumsal
lobicilik harcamasi) FARKLI yasal rejimlerdir.

SEMA KAYNAGI (20.09.2026, DURUSTLUK NOTU): bu ortamin kendi araclari
lda.gov'a Akamai bot-korumasi (403) yuzunden HICBIR ZAMAN ulasamadi -
asagidaki alan adlari CANLI bu ortamdan dogrulanamadi. Kullanicinin
KENDI taraycisindan/agindan cektigi GERCEK bir /filings/{uuid}/ yanitiyla
dogrulandi (20.09.2026) - ucuncu taraf scraper'larin (Apify/dltHub)
iddia ettigi camelCase alan adlari (filingUuid, incomeUsd...) YANLIS
cikti; gercek API snake_case donuyor (filing_uuid, income...) ve
registrant/client isimleri IC ICE nesnelerin .name alaninda. Bu servis
o GERCEK ornege gore yazildi, dokuman prozasina degil.

KOTA: LDA'nin kendi belgelenmis sinirlari GUNLUK degil DAKIKALIK'tir
(kayitli anahtarla 120/dk, anahtarsiz 15/dk - lda.gov/api/redoc/v1/).
Bu yuzden equibles_client.py'deki GUNLUK sayac deseni degil, DAKIKALIK
bir sayac + agresif onbellekleme (lobicilik dosyalari ceyreklik/yillik
degisir, gun ici tazelik gerekmez) kullanilir.

FAIL-LOUD: bu servis congress-trading-service/sec-edgar-13f-service ile
AYNI ilkeyi izler - veri alinamadiginda SESSIZCE bos/varsayilan
DONMEZ, main.py HTTPException ile GERCEK hata kodunu ACIKCA firlatir.

LAMBDA=0: bu servis MAA'nin karar zincirine (maa/src/main.py, cascade.py)
HICBIR YERDEN baglanmaz - salt-okunur, bagimsiz bir gozlem servisidir.
Bu iddia AST/grep ile testte kanitlanir (bkz. tests/test_lambda_sifir.py).
"""
import datetime
import os

import httpx
import redis

LDA_BASE = os.getenv("LDA_BASE_URL", "https://lda.gov/api/v1")
LDA_TIMEOUT = float(os.getenv("LDA_TIMEOUT", "15"))
CACHE_PREFIX = "lda:"

# Belgelenmis sinir 120/dk (kayitli anahtar) - yerel guvenlik payi 20 birakir.
LDA_DAKIKA_LIMIT = int(os.getenv("LDA_DAKIKA_LIMIT", "120"))
LDA_GUVENLIK_PAYI = int(os.getenv("LDA_GUVENLIK_PAYI", "20"))

# Lobicilik dosyalari ceyreklik/yillik yayimlanir - gun ici tazelik
# gerekmez, agresif onbellekleme kotayi büyük olcude korur.
CACHE_TTL_SANIYE = int(os.getenv("LDA_CACHE_TTL_SANIYE", str(6 * 3600)))

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
        import json
        v = _get_redis().get(CACHE_PREFIX + key)
        return json.loads(v) if v else None
    except Exception:
        return None


def _cache_set(key, value, ttl_seconds):
    try:
        import json
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
    return {"LDA_KEY": bool(os.getenv("LDA_KEY"))}


def _dakika_anahtari() -> str:
    dakika = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M")
    return f"lda:dakika:{dakika}"


def kota_durumu() -> dict:
    try:
        kullanilan = int(_get_redis().get(_dakika_anahtari()) or 0)
    except Exception:
        kullanilan = 0
    return {
        "limit": LDA_DAKIKA_LIMIT,
        "guvenlik_payi": LDA_GUVENLIK_PAYI,
        "bu_dakika_kullanilan": kullanilan,
        "yerelden_izinli_mi": kullanilan < (LDA_DAKIKA_LIMIT - LDA_GUVENLIK_PAYI),
    }


def _kota_artir() -> None:
    try:
        r = _get_redis()
        anahtar = _dakika_anahtari()
        p = r.pipeline()
        p.incr(anahtar)
        p.expire(anahtar, 120)   # bir sonraki dakikaya sarksa bile kisa omurlu
        p.execute()
    except Exception:
        pass


def _lobicilik_konulari(kayit: dict) -> list:
    konular = []
    for a in kayit.get("lobbying_activities") or []:
        konular.append({
            "kod": a.get("general_issue_code"),
            "aciklama": a.get("general_issue_code_display"),
            "detay": a.get("description"),
        })
    return konular


def _normalize_filing(kayit: dict) -> dict:
    """GERCEK 20.09.2026 ornegine gore alan adlari - kayit.py/main.py'de
    tekrar tekrar cikarilmasin diye TEK yerde toplanir."""
    registrant = kayit.get("registrant") or {}
    client = kayit.get("client") or {}
    return {
        "filing_uuid": kayit.get("filing_uuid"),
        "filing_turu": kayit.get("filing_type_display") or kayit.get("filing_type"),
        "filing_yili": kayit.get("filing_year"),
        "donem": kayit.get("filing_period_display") or kayit.get("filing_period"),
        "gelir_usd": kayit.get("income"),
        "gider_usd": kayit.get("expenses"),
        "lobici_firma": registrant.get("name"),
        "musteri": client.get("name"),
        "musteri_eyalet": client.get("state"),
        "konular": _lobicilik_konulari(kayit),
        "yayim_tarihi": kayit.get("dt_posted"),
        "fesih_tarihi": kayit.get("termination_date"),
        "belge_url": kayit.get("filing_document_url"),
    }


async def filings_cek(client_name: str = None, registrant_name: str = None,
                      filing_year: int = None, page: int = 1,
                      page_size: int = 25, timeout=None) -> tuple:
    """/filings/ - basarili -> (normalize_liste, meta, None),
    basarisiz/kota asimi -> (None, None, hata_sozlugu)."""
    key = os.getenv("LDA_KEY")
    if not key:
        return None, None, {"kaynak": "lda", "neden": "LDA_KEY tanimli degil"}

    kota = kota_durumu()
    if not kota["yerelden_izinli_mi"]:
        return None, None, {
            "kaynak": "lda",
            "neden": (f"dakikalik guvenlik payi asildi (bu dakika "
                      f"kullanilan={kota['bu_dakika_kullanilan']}/{LDA_DAKIKA_LIMIT}) "
                      "- istek ATILMADI"),
            "kota_asimi": True,
        }

    params = {"page": page, "page_size": page_size}
    if client_name:
        params["client_name"] = client_name
    if registrant_name:
        params["registrant_name"] = registrant_name
    if filing_year:
        params["filing_year"] = filing_year

    try:
        async with httpx.AsyncClient(timeout=timeout or LDA_TIMEOUT) as c:
            r = await c.get(f"{LDA_BASE}/filings/", params=params,
                            headers={"Authorization": f"Token {key}"})
        _kota_artir()

        if r.status_code == 200:
            govde = r.json()
            satirlar = govde.get("results")
            if not isinstance(satirlar, list):
                return None, None, {"kaynak": "lda", "neden": "beklenmeyen govde tipi"}
            return ([_normalize_filing(x) for x in satirlar],
                    {"toplam": govde.get("count"), "sonraki": govde.get("next"),
                     "onceki": govde.get("previous")}, None)
        if r.status_code == 429:
            return None, None, {"kaynak": "lda", "http_status": 429,
                                "neden": "sunucu dakikalik limiti asildi"}
        return None, None, {"kaynak": "lda", "http_status": r.status_code,
                            "neden": r.text[:200]}
    except Exception as e:
        return None, None, {"kaynak": "lda", "neden": f"{type(e).__name__}: {str(e)[:160]}"}


async def musteri_filings_getir(client_name: str, filing_year: int = None,
                                page: int = 1, page_size: int = 25,
                                onbellek: bool = True) -> dict:
    """Musteri (sirket) adina gore lobicilik dosyalari - onbellekli sarmalayici."""
    anahtar = f"client:{client_name.lower()}:{filing_year}:{page}:{page_size}"
    if onbellek:
        c = _cache_get(anahtar)
        if c is not None:
            c["cache_hit"] = True
            return c

    satirlar, meta, hata = await filings_cek(client_name=client_name,
                                             filing_year=filing_year,
                                             page=page, page_size=page_size)
    if hata:
        return {"records": [], "meta": None, "error": hata, "cache_hit": False}

    sonuc = {"records": satirlar, "meta": meta, "error": None, "cache_hit": False}
    _cache_set(anahtar, sonuc, CACHE_TTL_SANIYE)
    return sonuc


async def registrant_filings_getir(registrant_name: str, filing_year: int = None,
                                   page: int = 1, page_size: int = 25,
                                   onbellek: bool = True) -> dict:
    """Lobici firma adina gore dosyalar - musteri_filings_getir ile AYNI desen."""
    anahtar = f"registrant:{registrant_name.lower()}:{filing_year}:{page}:{page_size}"
    if onbellek:
        c = _cache_get(anahtar)
        if c is not None:
            c["cache_hit"] = True
            return c

    satirlar, meta, hata = await filings_cek(registrant_name=registrant_name,
                                             filing_year=filing_year,
                                             page=page, page_size=page_size)
    if hata:
        return {"records": [], "meta": None, "error": hata, "cache_hit": False}

    sonuc = {"records": satirlar, "meta": meta, "error": None, "cache_hit": False}
    _cache_set(anahtar, sonuc, CACHE_TTL_SANIYE)
    return sonuc
