"""
ALPHAWISE - Congress Trading Service / kaynak zinciri ve normallestirme (19.08.2026)

UC kaynakli otomatik yedekleme (fallback). Bugun llmquant_client.py'de kurulan
"birincil basarisiz olursa sessizce yedege dus" mantiginin aynisi:

  1) BIRINCIL : Quiver Quantitative  (api.quiverquant.com, QUIVER_API_KEY)
  2) YEDEK    : Financial Modeling Prep (stable/senate-latest + house-latest)
  3) TAMAMLAYICI: Equibles (api.equibles.com/v1, EQUIBLES_API_KEY) - 13.09.2026

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

=======================================================================
EQUIBLES NEDEN "3. KAYNAK" - "1. KAYNAK" DEGIL (13.09.2026)
=======================================================================
Equibles GRUP2 denetiminde degerlendirilen `daniel3303/Equibles` (self-hosted
.NET, GRUP2'de MIMARI-CIKAR kararli) ile AYNI ISIMDE ama TAMAMEN AYRI bir
UNDUR: burada entegre edilen, o ayni urunun BARINDIRILAN (hosted) REST API'si
(api.equibles.com) - self-hosted karari BURADA DEGISMEDI, HICBIR yeni
container KURULMADI.

Equibles TAM ZINCIRE (Quiver/FMP gibi "tum listeyi cek, yerelde filtrele")
GIREMEZ: /v1/congress/trades ucu ticker VEYA memberId'den EN AZ BIRINI
ZORUNLU KILAR - "hepsini ver" modu YOKTUR. Bu yuzden TAMAMLAYICI bir
kaynaktir: yalnizca Quiver+FMP zincirinin O SPESIFIK ticker icin SIFIR
kayit dondurdugu durumda cagrilir (FMP'nin ucretsiz katmani yalnizca
meclis basina EN SON 100 aciklamayla sinirlidir - bkz. asagida OLCULEN
BOSLUK). Boylece gunluk 100 isteklik butce yalnizca GERCEKTEN ihtiyac
duyulan sorgularda harcanir.

OLCULEN BOSLUK (13.09.2026, canli): Quiver 403 (abonelik kapsamiyor);
FMP ucretsiz katman toplam 200 kayit (meclis basina 100) donduruyor VE
sembol/isim filtreli uclari ucretli oldugu icin bu 200 kayit SERVIS
ICINDE filtreleniyor - yani FMP'nin dar penceresinde OLMAYAN bir ticker
icin zincir SESSIZCE bos donuyordu. Equibles /v1/congress/trades
varsayilan olarak GECEN YIL'a kadar giden, ticker'a OZEL bir sorgu
sunuyor - bu, olculen boslugu GERCEKTEN kapatir.

BUTCE ONAY KURALI: Equibles ucretsiz katmani GUNDE 100 istekle SINIRLI
(MCP+REST ORTAK sayac, api.equibles.com/docs/rate-limits ile canli
dogrulandi). Bu SINIR ASILMAZ: _equibles_kota_kontrol() yerel bir
GUVENLIK PAYI birakir (95/100'de yerelden durur) VE her yanittaki
X-RateLimit-Remaining basligini SUNUCUNUN KENDI gercegi olarak okuyup
yerel tahminin ONUNE koyar - iki sayac celisirse sunucuya guvenilir.
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
    anahtarlar = ("QUIVER_API_KEY", "FMP_API_KEY", "EQUIBLES_API_KEY")
    return {
        "QUIVER_API_KEY": bool(os.getenv("QUIVER_API_KEY")),
        "FMP_API_KEY": bool(os.getenv("FMP_API_KEY")),
        "EQUIBLES_API_KEY": bool(os.getenv("EQUIBLES_API_KEY")),
        "eksik": [k for k in anahtarlar if not os.getenv(k)],
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
        "source": "fmp",
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
        "source": "quiver",
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


# --- Kaynak 3: Equibles (TAMAMLAYICI - yalnizca zincir bos donunce) ----------

EQUIBLES_BASE = os.getenv("EQUIBLES_BASE_URL", "https://api.equibles.com/v1")
EQUIBLES_TIMEOUT = float(os.getenv("EQUIBLES_TIMEOUT", "10"))
# Gunluk ucretsiz kota 100'dur (docs/rate-limits, 13.09.2026 canli dogrulandi).
# Yerel guvenlik payi: 95'te DUR - sunucu sayaci ile bizim sayacimiz bir
# istekte bile driftlense, son 5 hak "kaza" yuzunden tukenmesin.
EQUIBLES_GUNLUK_LIMIT = int(os.getenv("EQUIBLES_GUNLUK_LIMIT", "100"))
EQUIBLES_GUVENLIK_PAYI = int(os.getenv("EQUIBLES_GUVENLIK_PAYI", "5"))


def _equibles_normalize(kayit):
    """Equibles /v1/congress/trades semasi (camelCase) -> ortak sema.

    ONEMLI DURUSTLUK NOTU (13.09.2026): dokumantasyondaki (docs/llms-full.txt)
    GetCongressionalTrades ORNEGI, MCP aracinin INSAN-OKUNUR tablo formatidir
    ve alan adlari (member/chamber/asset/amountRange) GERCEK REST JSON'iyla
    AYNI DEGILDIR. Bu fonksiyon ilk yazildiginda o ornege guvenmisti; GERCEK
    anahtarla canli cagri yapilinca (NVDA, 13.09.2026) sema TAMAMEN FARKLI
    cikti ve duzeltildi. Ders: "dokumantasyon ornegi" ile "REST'in gercekte
    donduruduğu JSON" AYNI SEY degildir - canli dogrulanmadan varsayilmaz.

    GERCEK ALAN ADLARI (canli olculdu): transactionDate, filingDate, ticker,
    memberId (uuid), memberName, memberPosition ("Representative"|"Senator" -
    "chamber" DEGIL), transactionType, assetName ("asset" DEGIL), assetType,
    subholding (araci/emeklilik hesabi - "account" kavraminin karsiligi),
    ownerType (bos dize | "Spouse" | "Self" - "owner" DEGIL), amountFrom/
    amountTo (SAYISAL tam sayilar - "amountRange" METIN DEGIL, yani
    _tutar_ayristir() BURADA GEREKMEZ; Quiver/FMP'nin aksine Equibles tutari
    zaten AYRISTIRILMIS veriyor).
    """
    konum = (kayit.get("memberPosition") or "").strip().lower()
    alt = kayit.get("amountFrom")
    ust = kayit.get("amountTo")
    orta = (alt + ust) / 2 if alt is not None and ust is not None else None
    aralik_metni = f"${alt:,}-${ust:,}" if alt is not None and ust is not None else None
    return {
        "source": "equibles",
        "member": kayit.get("memberName"),
        "member_id": kayit.get("memberId"),
        "first_name": None,
        "last_name": None,
        "chamber": "Senate" if konum.startswith("sen") else ("House" if konum else None),
        "district": None,
        "ticker": (kayit.get("ticker") or "").upper() or None,
        "asset_description": kayit.get("assetName"),
        "asset_type": kayit.get("assetType"),
        "transaction_type": kayit.get("transactionType"),
        "transaction_date": kayit.get("transactionDate"),
        "disclosure_date": kayit.get("filingDate"),
        "amount_range": aralik_metni,
        "amount_min_usd": alt,
        "amount_max_usd": ust,
        "amount_mid_usd": orta,
        "owner": kayit.get("ownerType") or None,
        "comment": kayit.get("subholding") or None,
        "source_link": None,
    }


def _equibles_kota_anahtari():
    import datetime

    gun = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    return f"equibles:gunluk:{gun}"


def equibles_kota_durumu():
    """Yerelde tutulan gunluk sayac (sunucunun kendi X-RateLimit-* basligi
    HER YANITTA guncellenir; bu fonksiyon istek ATMADAN once en son bilinen
    durumu okur).

    IKI SAYAC CELISIRSE SUNUCUYA GUVENILIR: 'equibles:sunucu_kalan',
    sunucunun EN SON yanitindaki X-RateLimit-Remaining degeridir - bizim
    yerel sayacimizdan BAGIMSIZ olarak (baska bir surec/servis ayni
    anahtari kullanmis olabilir, ya da bir istek sayilmadan basarisiz
    olmus olabilir) GERCEK durumu yansitir. Ikisi de guvenlik payinin
    ALTINDAYSA istek reddedilir - HANGISI daha kisitlayicıysa o kazanir.
    """
    try:
        r = _get_redis()
        kullanilan = int(r.get(_equibles_kota_anahtari()) or 0)
        sunucu_kalan_ham = r.get("equibles:sunucu_kalan")
        sunucu_kalan = int(sunucu_kalan_ham) if sunucu_kalan_ham is not None else None
    except Exception:
        kullanilan = 0
        sunucu_kalan = None

    yerel_izinli = kullanilan < (EQUIBLES_GUNLUK_LIMIT - EQUIBLES_GUVENLIK_PAYI)
    sunucu_izinli = sunucu_kalan is None or sunucu_kalan > EQUIBLES_GUVENLIK_PAYI
    return {
        "limit": EQUIBLES_GUNLUK_LIMIT,
        "guvenlik_payi": EQUIBLES_GUVENLIK_PAYI,
        "yerel_sayac_kullanilan": kullanilan,
        "sunucu_bildirdigi_kalan": sunucu_kalan,
        "yerelden_izinli_mi": yerel_izinli and sunucu_izinli,
    }


def _equibles_kota_artir(sunucu_kalan=None, sunucu_sifirlanma=None):
    """Yerel sayaci 1 artirir VE sunucunun bildirdigi X-RateLimit-Remaining
    degerini SAKLAR - bir sonraki kontrol sunucu gercegini yerel tahminin
    ONUNE koyabilsin diye."""
    try:
        r = _get_redis()
        anahtar = _equibles_kota_anahtari()
        p = r.pipeline()
        p.incr(anahtar)
        p.expire(anahtar, 48 * 3600)
        if sunucu_kalan is not None:
            p.set("equibles:sunucu_kalan", sunucu_kalan, ex=6 * 3600)
        p.execute()
    except Exception:
        pass


async def equibles_ticker_cek(ticker: str, limit: int = 50, timeout=None):
    """Bir ticker icin Equibles congress trade kayitlarini ceker.

    ARIZA YONU: Quiver/FMP ile AYNI sozlesme - basarili olursa
    (kayitlar, None), olmazsa (None, hata_sozlugu). Kota ASILIRSA
    (yerel guvenlik payi ya da sunucunun 429'u) istek HIC ATILMAZ/
    sessizce None doner - butce onay kurali GEREGI, gunluk 100 hakkin
    UZERINE CIKILMAZ.
    """
    key = os.getenv("EQUIBLES_API_KEY")
    if not key:
        return None, {"kaynak": "equibles", "neden": "EQUIBLES_API_KEY tanimli degil"}

    kota = equibles_kota_durumu()
    if not kota["yerelden_izinli_mi"]:
        return None, {
            "kaynak": "equibles",
            "neden": (f"gunluk guvenlik payi asildi (yerel sayac="
                     f"{kota['yerel_sayac_kullanilan']}/{EQUIBLES_GUNLUK_LIMIT}, "
                     f"pay={EQUIBLES_GUVENLIK_PAYI}) - istek ATILMADI"),
            "kota_asimi": True,
        }

    try:
        async with httpx.AsyncClient(timeout=timeout or EQUIBLES_TIMEOUT) as c:
            r = await c.get(
                f"{EQUIBLES_BASE}/congress/trades",
                params={"ticker": ticker.upper(), "limit": limit},
                headers={"Authorization": f"Bearer {key}"},
            )
        sunucu_kalan = r.headers.get("X-RateLimit-Remaining")
        _equibles_kota_artir(sunucu_kalan=sunucu_kalan)

        if r.status_code == 200:
            govde = r.json()
            satirlar = govde.get("data")
            if not isinstance(satirlar, list):
                return None, {"kaynak": "equibles", "neden": "beklenmeyen govde tipi"}
            return [_equibles_normalize(x) for x in satirlar], None
        if r.status_code == 429:
            return None, {"kaynak": "equibles", "http_status": 429,
                          "neden": "sunucu gunluk limiti asildi (Equibles kendi sayacinda)"}
        return None, {"kaynak": "equibles", "http_status": r.status_code,
                      "neden": r.text[:160]}
    except Exception as e:
        return None, {"kaynak": "equibles", "neden": f"{type(e).__name__}: {str(e)[:120]}"}


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
