"""
ALPHAWISE - Senate LDA (Lobbying Disclosure Act) Service (20.09.2026)

Madde 35'in LDA yarisi. congress-trading-service ile AYNI desen:
Redis onbellek+kota, fail-loud (veri alinamayinca HTTPException), MAA
kaskadindan BAGIMSIZ (lambda=0 - bkz. tests/test_lambda_sifir.py).
"""
from fastapi import FastAPI, HTTPException, Query

import resolver

app = FastAPI(
    title="ALPHAWISE - Senate LDA Service",
    description="Lobicilik bildirimleri (LD-1/LD-2) - lda.gov API",
    version="1.0.0",
)


@app.get("/healthz")
async def healthz():
    """LIVENESS - dis bagimliliga dokunmaz (congress-trading-service ile
    ayni gerekce: Docker healthcheck sik cagirir, LDA'ya gercek istek
    atmak dakikalik kotayi bosa tuketirdi)."""
    return {"status": "ok", "service": "senate-lda-service"}


@app.get("/health")
async def health():
    """READINESS - anahtar/redis durumunu gosterir, LDA'ya istek ATMAZ."""
    return {
        "status": "ok",
        "service": "senate-lda-service",
        "anahtar": resolver.anahtar_durumu(),
        "redis": resolver.redis_durumu(),
        "kota": resolver.kota_durumu(),
    }


@app.get("/filings/by-client")
async def musteri_dosyalari(
    name: str = Query(..., description="Musteri (sirket) adi, orn. AMAZON"),
    year: int = Query(None, ge=1996, le=2100, description="Filing yili filtresi"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=25, description="lda.gov azami 25"),
):
    """Bir sirketin lobicilik icin ADINA yaptirdigi bildirimler."""
    sonuc = await resolver.musteri_filings_getir(name, filing_year=year,
                                                 page=page, page_size=page_size)
    if sonuc["error"] is not None:
        kod = 429 if sonuc["error"].get("kota_asimi") else 502
        raise HTTPException(status_code=kod, detail=sonuc["error"])
    return {
        "client_query": name, "filing_year": year,
        "found": len(sonuc["records"]) > 0,
        "filings": sonuc["records"], "meta": sonuc["meta"],
        "cache_hit": sonuc["cache_hit"],
    }


@app.get("/filings/by-registrant")
async def lobici_dosyalari(
    name: str = Query(..., description="Lobicilik firmasi adi"),
    year: int = Query(None, ge=1996, le=2100),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=25),
):
    """Bir lobicilik firmasinin sundugu tum bildirimler."""
    sonuc = await resolver.registrant_filings_getir(name, filing_year=year,
                                                     page=page, page_size=page_size)
    if sonuc["error"] is not None:
        kod = 429 if sonuc["error"].get("kota_asimi") else 502
        raise HTTPException(status_code=kod, detail=sonuc["error"])
    return {
        "registrant_query": name, "filing_year": year,
        "found": len(sonuc["records"]) > 0,
        "filings": sonuc["records"], "meta": sonuc["meta"],
        "cache_hit": sonuc["cache_hit"],
    }
