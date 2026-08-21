"""
ALPHAWISE - Institution Filter Service (18.08.2026)

Belirli bir kurumun (Vanguard, BlackRock vb.) bir hissedeki 13F pozisyonunu bulur.
Kaynak: LLMQuant Data API (/api/filings/13f/*), cift anahtarli yedekleme ile.

MAA kaskadindan TAMAMEN BAGIMSIZDIR; gerektiginde HTTP ile cagrilir.

Iki yollu arama stratejisi:
  Yol A (by-ticker) : Tickeri tutan Top-1000 yonetici icinde ad eslestirme.
  Yol B (by-manager): Yol A bos donerse, cozulen CIK ile yoneticinin kendi
                      portfoyu taranir. VANGUARD GROUP INC gibi o ceyregin
                      Top-1000 kumesinde olmayan dosyalayicilar boyle bulunur.
"""
import asyncio
import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, HTTPException

from . import llmquant, resolver

logger = logging.getLogger("institution-filter")

_son_anahtar_dogrulama: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _son_anahtar_dogrulama
    logger.info("Baslangic: LLMQuant anahtar dogrulamasi yapiliyor...")
    _son_anahtar_dogrulama = await llmquant.anahtar_dogrula()
    for isim, durum in _son_anahtar_dogrulama.items():
        if not durum.get("gecerli"):
            logger.warning(
                "BASLANGIC UYARISI: %s GECERSIZ — yedekleme calismayacak! Detay: %s",
                isim, durum.get("detay", durum.get("http_status")),
            )
    yield


app = FastAPI(
    title="ALPHAWISE - Institution Filter Service",
    description="13F kurumsal pozisyon sorgulama (LLMQuant tabanli)",
    version="1.0.0",
    lifespan=lifespan,
)

BY_MANAGER_TARAMA_SINIRI = 500  # API'nin sert ust siniri


def _pozisyon_kaydi(h: dict, kaynak: str, donem: str, yonetici_adi: str, cik: str, rank=None):
    return {
        "manager_name": yonetici_adi,
        "manager_cik": cik,
        "manager_period_rank": rank,
        "ticker": h.get("ticker"),
        "cusip": h.get("cusip"),
        "title_of_class": h.get("title_of_class"),
        "shares": h.get("shares"),
        "shares_type": h.get("shares_type"),
        "value_usd": h.get("value_usd"),
        "put_call": h.get("put_call"),
        "period_of_report": donem,
        "veri_yolu": kaynak,
    }


@app.get("/health")
async def health(dogrula: bool = Query(False, description="True ise anahtarlari canli dogrular")):
    global _son_anahtar_dogrulama
    if dogrula:
        _son_anahtar_dogrulama = await llmquant.anahtar_dogrula()

    gecersiz = [k for k, v in _son_anahtar_dogrulama.items() if not v.get("gecerli")]
    tum_gecersiz = all(not v.get("gecerli") for v in _son_anahtar_dogrulama.values()) if _son_anahtar_dogrulama else True
    return {
        "status": "degraded" if gecersiz else "ok",
        "uyarilar": [f"{k} gecersiz — yedekleme calismayacak" for k in gecersiz] if gecersiz and not tum_gecersiz else
                    ["KRITIK: Hicbir anahtar gecerli degil!"] if tum_gecersiz and _son_anahtar_dogrulama else [],
        "service": "institution-filter-service",
        "api_anahtarlari": llmquant.anahtar_durumu(),
        "anahtar_dogrulama": _son_anahtar_dogrulama,
        "redis": llmquant.redis_durumu(),
    }


@app.get("/managers")
async def yoneticiler(q: str = Query("", description="Ad/alias icinde aranacak metin")):
    """Kapsanan Top-1000 yonetici kumesi. Kredi harcamaz."""
    veri = await llmquant.kapsanan_yoneticiler()
    if "error" in veri:
        raise HTTPException(status_code=502, detail=veri)
    liste = veri.get("data", {}).get("managers", [])
    adaylar = resolver.adaylari_birlestir(q, liste) if q else []
    return {
        "kapsanan_yonetici_sayisi": len(liste),
        "manager_set_period": veri.get("data", {}).get("manager_set_period"),
        "sorgu": q,
        "cozulen_adaylar": adaylar,
        "cache_hit": veri.get("_cache_hit", False),
    }


@app.get("/position/{ticker}")
async def pozisyon(
    ticker: str,
    institution: str = Query(..., description="Kurum adi, orn. Vanguard / BlackRock"),
    limit: int = Query(1000, ge=1, le=1000, description="by-ticker tarama derinligi"),
    derin_arama: bool = Query(True, description="Yol B (by-manager) devrede mi"),
):
    """Belirli bir kurumun verilen hissedeki 13F pozisyonu."""
    ticker = ticker.upper().strip()

    sahipler_veri, yoneticiler_veri = await asyncio.gather(
        llmquant.hisse_sahipleri(ticker, limit=limit),
        llmquant.kapsanan_yoneticiler(),
    )
    if "error" in sahipler_veri:
        raise HTTPException(status_code=502, detail=sahipler_veri)

    data = sahipler_veri.get("data", {}) or {}
    holders = data.get("holders", []) or []
    by_ticker_donem = data.get("ranking_period")
    kume = (yoneticiler_veri.get("data", {}) or {}).get("managers", []) if "error" not in yoneticiler_veri else []

    adaylar = resolver.adaylari_birlestir(institution, kume)
    aday_cikler = {a["manager_cik"] for a in adaylar}
    q = institution.lower().strip()

    # --- Yol A: by-ticker icinde ad / CIK eslestirme ---
    eslesenler = []
    for h in holders:
        cik = str(h.get("manager_cik"))
        ad = h.get("manager_name", "") or ""
        if cik in aday_cikler or q in ad.lower():
            eslesenler.append(
                _pozisyon_kaydi(
                    h, "by-ticker", h.get("manager_period_of_report") or by_ticker_donem,
                    ad, cik, h.get("manager_period_rank"),
                )
            )
    bulunan_cikler = {e["manager_cik"] for e in eslesenler}

    # --- Yol B: kumede olmayan adaylari kendi portfoyunden tara ---
    notlar = []
    derin_sonuclar = []
    eksik_adaylar = [a for a in adaylar if a["manager_cik"] not in bulunan_cikler]
    if derin_arama and eksik_adaylar:
        istekler = [llmquant.yonetici_portfoyu(a["manager_cik"], limit=BY_MANAGER_TARAMA_SINIRI) for a in eksik_adaylar]
        cevaplar = await asyncio.gather(*istekler, return_exceptions=True)
        for aday, cevap in zip(eksik_adaylar, cevaplar):
            if isinstance(cevap, Exception) or not isinstance(cevap, dict) or "error" in cevap:
                notlar.append(f"{aday['manager_name']}: by-manager sorgusu basarisiz")
                continue
            mdata = cevap.get("data", {}) or {}
            mgr = mdata.get("manager", {}) or {}
            filing = mdata.get("filing", {}) or {}
            hold = mdata.get("holdings", []) or []
            vurus = [x for x in hold if (x.get("ticker") or "").upper() == ticker]
            for x in vurus:
                derin_sonuclar.append(
                    _pozisyon_kaydi(
                        x, "by-manager", filing.get("period_of_report"),
                        mgr.get("manager_name") or aday["manager_name"],
                        str(mgr.get("manager_cik") or aday["manager_cik"]),
                        mgr.get("period_rank"),
                    )
                )
            if not vurus:
                toplam = filing.get("table_entry_total")
                if toplam and toplam > len(hold):
                    notlar.append(
                        f"{mgr.get('manager_name') or aday['manager_name']}: {ticker} en buyuk "
                        f"{len(hold)} pozisyon icinde yok (portfoyde toplam {toplam} kalem; "
                        f"API offset desteklemedigi icin kuyruk taranamiyor)"
                    )
                else:
                    notlar.append(
                        f"{mgr.get('manager_name') or aday['manager_name']}: {ticker} pozisyonu yok "
                        f"({filing.get('period_of_report')} donemi, {len(hold)} kalem tarandi)"
                    )

    tum = eslesenler + derin_sonuclar
    donemler = sorted({e["period_of_report"] for e in tum if e.get("period_of_report")})
    if len(donemler) > 1:
        notlar.append(
            f"DIKKAT: sonuclar farkli ceyreklere ait ({', '.join(donemler)}); "
            "dogrudan karsilastirmadan once donemleri esitleyin."
        )

    return {
        "ticker": ticker,
        "institution_query": institution,
        "found": len(tum) > 0,
        "eslesme_sayisi": len(tum),
        "positions": sorted(tum, key=lambda z: z.get("value_usd") or 0, reverse=True),
        "cozulen_adaylar": adaylar,
        "kapsam": {
            "by_ticker_ranking_period": by_ticker_donem,
            "by_ticker_taranan_sahip": len(holders),
            "by_ticker_toplam_sahip": data.get("total_holders_in_scope"),
            "derin_arama_yapildi": bool(derin_arama and eksik_adaylar),
            "derin_arama_sinirli": BY_MANAGER_TARAMA_SINIRI,
        },
        "notlar": notlar,
        "kalan_kredi": (sahipler_veri.get("meta", {}) or {}).get("remainingCredits"),
        "cache_hit": sahipler_veri.get("_cache_hit", False),
    }


@app.get("/compare/{ticker}")
async def karsilastir(
    ticker: str,
    institutions: str = Query(..., description="Virgulle ayrilmis kurum listesi"),
    limit: int = Query(1000, ge=1, le=1000),
):
    """Birden fazla kurumun ayni hissedeki pozisyonlarini yan yana getirir."""
    isimler = [x.strip() for x in institutions.split(",") if x.strip()]
    if not isimler:
        raise HTTPException(status_code=400, detail="En az bir kurum adi gerekli")

    sonuclar = await asyncio.gather(
        *[pozisyon(ticker, institution=i, limit=limit, derin_arama=True) for i in isimler],
        return_exceptions=True,
    )
    cikti = []
    for isim, s in zip(isimler, sonuclar):
        if isinstance(s, Exception):
            cikti.append({"institution_query": isim, "found": False, "hata": str(s)[:200]})
            continue
        toplam_hisse = sum(p.get("shares") or 0 for p in s["positions"])
        toplam_usd = sum(p.get("value_usd") or 0 for p in s["positions"])
        cikti.append(
            {
                "institution_query": isim,
                "found": s["found"],
                "toplam_shares": toplam_hisse,
                "toplam_value_usd": toplam_usd,
                "donemler": sorted({p["period_of_report"] for p in s["positions"] if p.get("period_of_report")}),
                "positions": s["positions"],
                "notlar": s["notlar"],
            }
        )
    return {"ticker": ticker.upper(), "kurumlar": cikti}


@app.get("/holders/{ticker}")
async def sahipler(
    ticker: str,
    limit: int = Query(1000, ge=1, le=1000),
    top: int = Query(20, ge=1, le=1000, description="Pozisyon buyuklugune gore ilk N"),
):
    """Tickeri tutan en buyuk kurumsal sahipler (hisse adedine gore sirali)."""
    veri = await llmquant.hisse_sahipleri(ticker.upper(), limit=limit)
    if "error" in veri:
        raise HTTPException(status_code=502, detail=veri)
    data = veri.get("data", {}) or {}
    holders = sorted(data.get("holders", []) or [], key=lambda z: z.get("shares") or 0, reverse=True)
    return {
        "ticker": ticker.upper(),
        "ranking_period": data.get("ranking_period"),
        "total_holders_in_scope": data.get("total_holders_in_scope"),
        "aggregate_value_usd": data.get("aggregate_value_usd"),
        "top_holders": holders[:top],
        "kalan_kredi": (veri.get("meta", {}) or {}).get("remainingCredits"),
        "cache_hit": veri.get("_cache_hit", False),
    }


@app.get("/credits")
async def krediler():
    """Kalan LLMQuant kredisi (canli sorgu, onbelleksiz)."""
    veri = await llmquant.llmquant_get("/api/filings/13f/managers", {"limit": 1})
    if "error" in veri:
        raise HTTPException(status_code=502, detail=veri)
    meta = veri.get("meta", {}) or {}
    return {
        "remainingCredits": meta.get("remainingCredits"),
        "kullanilan_anahtar": veri.get("_kullanilan_anahtar"),
        "api_anahtarlari": llmquant.anahtar_durumu(),
    }
