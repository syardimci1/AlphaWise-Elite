"""
ALPHAWISE - Congress Trading Service (19.08.2026)

ABD Kongre uyelerinin STOCK Act kapsaminda acikladigi hisse alim-satimlari.
Iki kaynakli otomatik yedekleme: Quiver (birincil) -> FMP (yedek).

MAA kaskadindan TAMAMEN BAGIMSIZDIR (cascade.py / MAA main.py /
llmquant_client.py'ye dokunulmaz); gerektiginde HTTP ile cagrilir.
"""
import os

from fastapi import FastAPI, Query, HTTPException

import resolver

app = FastAPI(
    title="ALPHAWISE - Congress Trading Service",
    description="STOCK Act kongre islemleri; Quiver birincil, FMP yedek",
    version="1.0.0",
)


@app.get("/healthz")
async def healthz():
    """
    LIVENESS: yalnizca "surec ayakta mi" sorusuna cevap verir.

    NEDEN AYRI BIR ENDPOINT (22.08.2026):
    Asagidaki /health, her cagrida Quiver VE FMP'ye GERCEK istek atiyor
    (olculdu: cagri basina 0.8-1.8 sn, onbelleksiz). Docker healthcheck'i
    30 saniyede bir /health'e baglansaydi, gunde ~2880 kez dis API cagrilir
    ve FMP gunluk kotasi servis daha kullanilmadan tuketilirdi.

    Bu yuzden Docker healthcheck bu endpoint'i kullanir: hicbir dis
    bagimliliga dokunmaz, is mantigini calistirmaz. Kaynaklarin gercek
    durumunu gormek icin /health kullanilmaya devam edilir.

    Ayrim CONSTITUTION.md Madde 16.2'deki liveness/readiness tanimiyla
    uyumludur.
    """
    return {"status": "ok", "service": "congress-trading-service"}


@app.get("/health")
async def health():
    """Servis + Redis + her iki kaynagin erisilebilirlik durumu."""
    quiver_kayit, quiver_hata = await resolver.quiver_cek()
    fmp_kayit, fmp_hata = await resolver.fmp_cek()
    return {
        "status": "ok",
        "service": "congress-trading-service",
        "redis": resolver.redis_durumu(),
        "api_anahtarlari": resolver.anahtar_durumu(),
        "kaynaklar": {
            "quiver_birincil": {
                "erisilebilir": quiver_kayit is not None,
                "kayit": len(quiver_kayit) if quiver_kayit else 0,
                "hata": quiver_hata,
            },
            "fmp_yedek": {
                "erisilebilir": fmp_kayit is not None,
                "kayit": len(fmp_kayit) if fmp_kayit else 0,
                "hata": fmp_hata,
            },
        },
        "aktif_kaynak": "quiver" if quiver_kayit is not None else ("fmp" if fmp_kayit is not None else None),
    }


@app.get("/source-status")
async def kaynak_durumu():
    """Her iki kaynagin anlik durumu; kimlik dogrulama gerekip gerekmedigi dahil."""
    quiver_kayit, quiver_hata = await resolver.quiver_cek()
    fmp_kayit, fmp_hata = await resolver.fmp_cek()
    q_kod = (quiver_hata or {}).get("http_status")
    return {
        "birincil": {
            "ad": "Quiver Quantitative",
            "endpoint": f"{resolver.QUIVER_BASE}/beta/live/congresstrading",
            "kimlik_dogrulama_gerekli": True,
            "kimlik_dogrulama_yontemi": "Authorization: Token <QUIVER_API_KEY>",
            "anahtar_tanimli": bool(os.getenv("QUIVER_API_KEY")),
            "calisiyor": quiver_kayit is not None,
            "http_status": q_kod,
            "teshis": (
                "Anahtar kimlik dogrulamasindan geciyor ancak abonelik bu veri setini kapsamiyor "
                "(anahtarsiz 401, anahtarli 403). Plan yukseltilmeli."
                if q_kod == 403 else (quiver_hata or {}).get("neden")
            ),
            "gecis_zaman_asimi_sn": resolver.BIRINCIL_TIMEOUT,
        },
        "yedek": {
            "ad": "Financial Modeling Prep",
            "endpoint": f"{resolver.FMP_BASE}/stable/{{senate,house}}-latest",
            "kimlik_dogrulama_gerekli": True,
            "kimlik_dogrulama_yontemi": "apikey sorgu parametresi (FMP header auth DESTEKLEMIYOR)",
            "anahtar_tanimli": bool(os.getenv("FMP_API_KEY")),
            "calisiyor": fmp_kayit is not None,
            "kayit": len(fmp_kayit) if fmp_kayit else 0,
            "hata": fmp_hata,
            "kapsam_siniri": (
                "Ucretsiz katman: meclis basina en son 100 aciklama. Sayfalama (page/limit) ve "
                "sembol/isim filtreli uclar ucretli (402), bu yuzden filtreleme servis icinde yapilir."
            ),
        },
        "gecis_kurali": "HTTP 401/403/429/5xx veya zaman asimi -> otomatik yedege dusulur",
    }


@app.get("/trades/by-member")
async def uye_islemleri(
    name: str = Query(..., description="Uye adi, orn. Tuberville / Ro Khanna"),
    limit: int = Query(100, ge=1, le=1000),
):
    """Belirli bir Kongre uyesinin tum aciklanmis islemleri."""
    veri = await resolver.kayitlari_getir()
    if not veri["records"]:
        raise HTTPException(status_code=502, detail=veri)
    vurus = resolver.uye_filtrele(veri["records"], name)
    vurus.sort(key=lambda k: (k.get("transaction_date") or ""), reverse=True)
    return {
        "member_query": name,
        "source": veri["source"],
        "source_label": veri["source_label"],
        "fallback_used": veri["fallback_used"],
        "primary_error": veri["primary_error"],
        "found": len(vurus) > 0,
        "ozet": resolver.ozetle(vurus),
        "trades": vurus[:limit],
        "taranan_kayit": len(veri["records"]),
        "cache_hit": veri.get("cache_hit", False),
    }


@app.get("/trades/{ticker}")
async def hisse_islemleri(
    ticker: str,
    limit: int = Query(100, ge=1, le=1000),
):
    """Verilen hisse icin Kongre uyesi islemleri."""
    veri = await resolver.kayitlari_getir()
    if not veri["records"]:
        raise HTTPException(status_code=502, detail=veri)
    vurus = resolver.ticker_filtrele(veri["records"], ticker)
    vurus.sort(key=lambda k: (k.get("transaction_date") or ""), reverse=True)
    return {
        "ticker": ticker.upper(),
        "source": veri["source"],
        "source_label": veri["source_label"],
        "fallback_used": veri["fallback_used"],
        "primary_error": veri["primary_error"],
        "found": len(vurus) > 0,
        "ozet": resolver.ozetle(vurus),
        "trades": vurus[:limit],
        "taranan_kayit": len(veri["records"]),
        "cache_hit": veri.get("cache_hit", False),
    }
