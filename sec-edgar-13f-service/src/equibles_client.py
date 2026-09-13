"""
ALPHAWISE - SEC EDGAR 13F Service - Equibles tamamlayici istemci (madde 58)

Bu servisin SEC EDGAR'a dayali /position ve /holders uclarina TAMAMLAYICI
iki uc ekler - madde 52'deki (congress-trading-service) desenle AYNI:
hafif HTTP istemcisi, yeni container yok, canli karar yoluna baglanmaz.

NEDEN GEREKLI (14.09.2026 canli olculdu, /opt/alphawise/
EQUIBLES_ENTEGRASYON_DEGERLENDIRMESI.md):
1) /holders/{ticker} yalnizca 44 kurumluk elle-kuratorlenmis haritayi
   tarar ve bunu kendi yanitinda itiraf eder ("TUM 13F sahiplerini
   gostermez"). Equibles /v1/stocks/{ticker}/institutional-holders CANLI
   dogrulandi: NVDA'da meta.totalInstitutions=5956 - kat kat genis bir
   evren. Bu istemci bunu OPT-IN bir sorgu parametresiyle ekler (bkz.
   main.py /holders), VARSAYILAN OLARAK cagirmaz - cunku bu servis artik
   congress-trading-service ile AYNI Equibles hesabini ve GUNLUK 100
   isteklik PAYLASILAN kotayi kullanir (dogrulandi: ikisi de ayni Docker
   agindaki ayni Redis konteynerine, ayni db=0'a baglaniyor - bkz. madde
   58 NOT kaydi). 44 kurumdan genis kapsam HER /holders cagrisinda
   YAPISAL OLARAK eksik kalacagi icin (44 < 5956 hicbir zaman "yeterli"
   hale gelmez), bunu her cagride otomatik tetiklemek paylasilan
   butceyi hizla tuketirdi.
2) Ceyrekten-ceyrege pozisyon degisimi (initiated/increased/reduced/
   exited) bu serviste HIC YOK. Equibles /v1/institutions/{cik}/activity
   CANLI dogrulandi (BlackRock, CIK 2012383) - dokuman prozasindaki alan
   adlariyla BIREBIR ayni JSON geldi (bu kez sema surprizi olmadi). Yeni,
   bagimsiz bir uc olarak eklendi (/institution-activity/{cik}).

KOTA: congress-trading-service/resolver.py ile AYNI Redis anahtari
(equibles:gunluk:<UTC-tarih>) KASITLI olarak paylasilir - iki servis
TEK bir gunluk sayaci gorur, sunucunun X-RateLimit-Remaining degeri de
ayni "equibles:sunucu_kalan" anahtarinda paylasilir.
"""
import datetime
import os

import httpx

EQUIBLES_BASE = os.getenv("EQUIBLES_BASE_URL", "https://api.equibles.com/v1")
EQUIBLES_TIMEOUT = float(os.getenv("EQUIBLES_TIMEOUT", "10"))
EQUIBLES_GUNLUK_LIMIT = int(os.getenv("EQUIBLES_GUNLUK_LIMIT", "100"))
EQUIBLES_GUVENLIK_PAYI = int(os.getenv("EQUIBLES_GUVENLIK_PAYI", "5"))


def _kota_anahtari():
    gun = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    return f"equibles:gunluk:{gun}"


async def kota_durumu(redis_client):
    """congress-trading-service/resolver.py::equibles_kota_durumu ile AYNI
    mantik (sunucu-oncelikli celiski cozumu), async redis'e uyarlanmis.
    Redis erisilemezse (fail-open, sistemdeki mevcut desenle tutarli)
    yerel sayac 0 kabul edilir - koruma yalnizca sunucunun kendi 429'una
    kalir."""
    if redis_client is None:
        return {
            "limit": EQUIBLES_GUNLUK_LIMIT, "guvenlik_payi": EQUIBLES_GUVENLIK_PAYI,
            "yerel_sayac_kullanilan": 0, "sunucu_bildirdigi_kalan": None,
            "yerelden_izinli_mi": True,
        }
    try:
        kullanilan = int(await redis_client.get(_kota_anahtari()) or 0)
        sunucu_kalan_ham = await redis_client.get("equibles:sunucu_kalan")
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


async def _kota_artir(redis_client, sunucu_kalan=None):
    if redis_client is None:
        return
    try:
        anahtar = _kota_anahtari()
        p = redis_client.pipeline()
        p.incr(anahtar)
        p.expire(anahtar, 48 * 3600)
        if sunucu_kalan is not None:
            p.set("equibles:sunucu_kalan", sunucu_kalan, ex=6 * 3600)
        await p.execute()
    except Exception:
        pass


def _holder_normalize(kayit):
    return {
        "kurum_adi": kayit.get("name"),
        "kurum_cik": kayit.get("cik"),
        "hisse_adet": kayit.get("shares"),
        "deger_usd": kayit.get("value"),
        "toplamin_yuzdesi": kayit.get("percentOfTotal"),
        "pozisyon_tipi": kayit.get("positionType"),
    }


async def holders_cek(redis_client, ticker: str, limit: int = 50, timeout=None):
    """/v1/stocks/{ticker}/institutional-holders - GENIS KAPSAMLI (44 ile
    SINIRLI DEGIL) 13F sahip listesi. Basarili -> (payload, None),
    basarisiz -> (None, hata_sozlugu). Kota asilirsa istek HIC ATILMAZ -
    butce onay kurali geregi PAYLASILAN gunluk 100 hakkin uzerine cikilmaz.
    """
    key = os.getenv("EQUIBLES_API_KEY")
    if not key:
        return None, {"kaynak": "equibles", "neden": "EQUIBLES_API_KEY tanimli degil"}

    kota = await kota_durumu(redis_client)
    if not kota["yerelden_izinli_mi"]:
        return None, {
            "kaynak": "equibles",
            "neden": (f"gunluk PAYLASILAN guvenlik payi asildi (yerel sayac="
                      f"{kota['yerel_sayac_kullanilan']}/{EQUIBLES_GUNLUK_LIMIT}) "
                      "- istek ATILMADI"),
            "kota_asimi": True,
        }

    try:
        async with httpx.AsyncClient(timeout=timeout or EQUIBLES_TIMEOUT) as c:
            r = await c.get(
                f"{EQUIBLES_BASE}/stocks/{ticker.upper()}/institutional-holders",
                params={"limit": limit},
                headers={"Authorization": f"Bearer {key}"},
            )
        await _kota_artir(redis_client, sunucu_kalan=r.headers.get("X-RateLimit-Remaining"))

        if r.status_code == 200:
            govde = r.json()
            satirlar = govde.get("data")
            meta = govde.get("meta") or {}
            if not isinstance(satirlar, list):
                return None, {"kaynak": "equibles", "neden": "beklenmeyen govde tipi"}
            return {
                "rapor_tarihi": meta.get("reportDate"),
                "toplam_kurum": meta.get("totalInstitutions"),
                "sayfadaki_kurum": meta.get("count", len(satirlar)),
                "daha_fazla_var": meta.get("hasMore", False),
                "kurumlar": [_holder_normalize(x) for x in satirlar],
                "kaynak": ("Equibles (genis kapsam - 44 kurumluk kuratorlenmis "
                           "haritadan bagimsiz)"),
            }, None
        if r.status_code == 429:
            return None, {"kaynak": "equibles", "http_status": 429,
                          "neden": "sunucu gunluk limiti asildi (Equibles kendi sayacinda)"}
        return None, {"kaynak": "equibles", "http_status": r.status_code,
                      "neden": r.text[:160]}
    except Exception as e:
        return None, {"kaynak": "equibles", "neden": f"{type(e).__name__}: {str(e)[:120]}"}


def _aktivite_satiri(kayit):
    return {
        "ticker": kayit.get("ticker"),
        "sirket": kayit.get("company"),
        "onceki_hisse": kayit.get("previousShares"),
        "guncel_hisse": kayit.get("currentShares"),
        "hisse_degisimi": kayit.get("deltaShares"),
        "deger_degisimi_usd": kayit.get("deltaValue"),
    }


async def institution_activity_cek(redis_client, cik: str, bucket: str = None,
                                    limit: int = 20, timeout=None):
    """/v1/institutions/{cik}/activity - ceyrekten ceyrege initiated/
    increased/reduced/exited siniflandirmasi. Bu servis bu veriyi HICBIR
    sekilde uretemez (SEC tek bir donemin fotografini verir, iki donem
    arasindaki degisim SEC'ten HESAPLANMAZ) - saf tamamlayici, tekrar
    DEGIL."""
    key = os.getenv("EQUIBLES_API_KEY")
    if not key:
        return None, {"kaynak": "equibles", "neden": "EQUIBLES_API_KEY tanimli degil"}

    kota = await kota_durumu(redis_client)
    if not kota["yerelden_izinli_mi"]:
        return None, {
            "kaynak": "equibles",
            "neden": (f"gunluk PAYLASILAN guvenlik payi asildi (yerel sayac="
                      f"{kota['yerel_sayac_kullanilan']}/{EQUIBLES_GUNLUK_LIMIT}) "
                      "- istek ATILMADI"),
            "kota_asimi": True,
        }

    params = {"limit": limit}
    if bucket:
        params["bucket"] = bucket
    try:
        async with httpx.AsyncClient(timeout=timeout or EQUIBLES_TIMEOUT) as c:
            r = await c.get(
                f"{EQUIBLES_BASE}/institutions/{cik}/activity",
                params=params,
                headers={"Authorization": f"Bearer {key}"},
            )
        await _kota_artir(redis_client, sunucu_kalan=r.headers.get("X-RateLimit-Remaining"))

        if r.status_code == 200:
            d = r.json()
            return {
                "kurum_adi": d.get("name"),
                "kurum_cik": d.get("cik"),
                "rapor_tarihi": d.get("reportDate"),
                "onceki_rapor_tarihi": d.get("previousReportDate"),
                "baslatilan": [_aktivite_satiri(x) for x in d.get("initiated", [])],
                "artirilan": [_aktivite_satiri(x) for x in d.get("increased", [])],
                "azaltilan": [_aktivite_satiri(x) for x in d.get("reduced", [])],
                "cikilan": [_aktivite_satiri(x) for x in d.get("exited", [])],
                "baslatilan_toplam": d.get("initiatedTotal"),
                "artirilan_toplam": d.get("increasedTotal"),
                "azaltilan_toplam": d.get("reducedTotal"),
                "cikilan_toplam": d.get("exitedTotal"),
                "kaynak": "Equibles (bu servis bu veriyi kendi basina uretemez)",
            }, None
        if r.status_code == 404:
            return None, {"kaynak": "equibles", "http_status": 404,
                          "neden": f"CIK {cik} icin Equibles'ta kayit bulunamadi"}
        if r.status_code == 429:
            return None, {"kaynak": "equibles", "http_status": 429,
                          "neden": "sunucu gunluk limiti asildi (Equibles kendi sayacinda)"}
        return None, {"kaynak": "equibles", "http_status": r.status_code,
                      "neden": r.text[:160]}
    except Exception as e:
        return None, {"kaynak": "equibles", "neden": f"{type(e).__name__}: {str(e)[:120]}"}
