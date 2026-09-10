"""
ALPHAWISE - FINRA Dark Pool Service (18.08.2026)

FINRA'nin resmi, UCRETSIZ ATS Transparency (otcMarket/weeklySummary) veri
kumesinden dark pool hacim verisi saglar. API ANAHTARI GEREKTIRMEZ -
canli istekle dogrulandi (bkz. /auth-check).

MAA kaskadindan TAMAMEN BAGIMSIZDIR; gerektiginde HTTP ile cagrilir.
"""
import asyncio

from fastapi import FastAPI, Query, HTTPException

from . import baski
from . import dix as _dix
from . import finra
from . import regsho

app = FastAPI(
    title="ALPHAWISE - FINRA Dark Pool Service",
    description="FINRA ATS Transparency tabanli dark pool hacim verisi (kimlik dogrulamasiz)",
    version="1.0.0",
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "finra-darkpool-service",
        "kaynak": "https://api.finra.org (developer.finra.org)",
        "api_anahtari_gerekli": False,
        "redis": finra.redis_durumu(),
    }


@app.get("/auth-check")
async def kimlik_kontrol():
    """FINRA API'sinin kimlik dogrulama isteyip istemedigini canli test eder."""
    return await finra.kimlik_dogrulama_testi()


@app.get("/weeks")
async def haftalar(limit: int = Query(12, ge=1, le=1000)):
    """Yayinlanmis haftalar (en yeniden eskiye)."""
    try:
        veri = await finra.mevcut_haftalar()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{type(e).__name__}: {e}")
    return {
        "en_son_hafta": veri["en_son_hafta"],
        "toplam_hafta": veri["hafta_sayisi"],
        "tierler": veri["tierler"],
        "haftalar": veri["haftalar"][:limit],
        "gecikme_notu": "FINRA ATS verisi gecikmeli yayinlanir: NMS Tier 1 ~2 hafta, Tier 2 ~4 hafta.",
    }


@app.get("/darkpool/{ticker}")
async def darkpool(
    ticker: str,
    week: str = Query(None, description="YYYY-MM-DD (Pazartesi). Bos ise en son yayinlanan hafta."),
    top_venues: int = Query(15, ge=1, le=100),
):
    """Bir sembolun haftalik dark pool (ATS) hacim ozeti + venue kirilimi."""
    try:
        if not week:
            week = (await finra.mevcut_haftalar())["en_son_hafta"]
        kayitlar = await finra.haftalik_kayitlar(ticker, week)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{type(e).__name__}: {e}")

    ozet = finra.ozetle(ticker, week, kayitlar)
    if not ozet["veri_var"]:
        ozet["uyari"] = (
            f"{ticker.upper()} icin {week} haftasinda kayit yok. Sembol yanlis olabilir, "
            "ya da bu hafta ilgili tier icin henuz yayinlanmamis olabilir."
        )
    ozet["venues"] = ozet["venues"][:top_venues]
    ozet["ham_kayit_sayisi"] = len(kayitlar)
    return ozet


@app.get("/darkpool/{ticker}/history")
async def gecmis(
    ticker: str,
    weeks: int = Query(8, ge=1, le=52, description="Kac hafta geriye gidilecek"),
):
    """Dark pool hacminin haftalik seyri (trend analizi icin)."""
    try:
        p = await finra.mevcut_haftalar()
        hedef = p["haftalar"][:weeks]
        kayit_listesi = await asyncio.gather(
            *[finra.haftalik_kayitlar(ticker, h) for h in hedef], return_exceptions=True
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{type(e).__name__}: {e}")

    seri = []
    for hafta, kayitlar in zip(hedef, kayit_listesi):
        if isinstance(kayitlar, Exception) or not kayitlar:
            continue
        o = finra.ozetle(ticker, hafta, kayitlar)
        seri.append(
            {
                "week_start_date": hafta,
                "ats_shares": o["dark_pool"]["ats_toplam_shares"],
                "ats_trades": o["dark_pool"]["ats_toplam_trades"],
                "otc_shares": o["otc_toplam"]["otc_toplam_shares"],
                "ats_orani_yuzde": o["ats_orani_yuzde"],
                "aktif_ats_sayisi": o["dark_pool"]["aktif_ats_sayisi"],
            }
        )

    degerler = [s["ats_shares"] for s in seri if s["ats_shares"]]
    ortalama = sum(degerler) / len(degerler) if degerler else None
    son = seri[0]["ats_shares"] if seri else None
    return {
        "ticker": ticker.upper(),
        "istenen_hafta": weeks,
        "donen_hafta": len(seri),
        "seri": seri,
        "ortalama_ats_shares": round(ortalama) if ortalama else None,
        "son_hafta_ortalamaya_orani": round(son / ortalama, 3) if ortalama and son else None,
    }


@app.get("/venues/{ticker}")
async def venues(
    ticker: str,
    week: str = Query(None),
    top: int = Query(25, ge=1, le=100),
):
    """Sembol icin ATS (dark pool) venue kirilimi - hangi havuzda ne kadar islem."""
    try:
        if not week:
            week = (await finra.mevcut_haftalar())["en_son_hafta"]
        kayitlar = await finra.haftalik_kayitlar(ticker, week)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{type(e).__name__}: {e}")

    ozet = finra.ozetle(ticker, week, kayitlar)
    return {
        "ticker": ticker.upper(),
        "week_start_date": week,
        "ats_toplam_shares": ozet["dark_pool"]["ats_toplam_shares"],
        "aktif_ats_sayisi": ozet["dark_pool"]["aktif_ats_sayisi"],
        "venues": ozet["venues"][:top],
    }


# ===== GUNLUK Reg SHO KISA HACIM (23.08.2026, Faz 2/C1) =====
# Mevcut HAFTALIK ATS uclarina DOKUNULMADI; bunlar onlarin yanina eklendi.


@app.get("/regsho/{ticker}")
async def regsho_gunluk(
    ticker: str,
    gun: int = Query(10, ge=1, le=60, description="Kac yayimlanmis is gunu"),
):
    """FINRA Reg SHO GUNLUK kisa hacim orani (T+1). Yon iddiasi tasimaz."""
    t = ticker.upper().strip()
    if not t.isalnum() or len(t) > 6:
        raise HTTPException(status_code=400, detail="gecersiz ticker bicimi")
    try:
        return await regsho.son_gunler(t, gun=gun, geriye_bak=gun * 3 + 10)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{type(e).__name__}: {e}")


@app.get("/baski/{ticker}")
async def borsa_disi_baski(
    ticker: str,
    gun: int = Query(10, ge=1, le=60, description="Kac yayimlanmis is gunu"),
):
    """Borsa disi (dark pool) hacmin KONSOLIDE hacme orani — gunluk.

    /regsho'dan farki paydadir: orada payda borsa disi hacmin kendisidir,
    burada toplam piyasa hacmidir. "Karanlik havuz aktivitesi artti mi"
    sorusu ancak bu oranla yanitlanabilir.

    Yon iddiasi tasimaz; kalibre EDILMEMISTIR.
    """
    t = ticker.upper().strip()
    if not t.isalnum() or len(t) > 6:
        raise HTTPException(status_code=400, detail="gecersiz ticker bicimi")
    try:
        return await baski.borsa_disi_pay(t, gun=gun, geriye_bak=gun * 3 + 10)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{type(e).__name__}: {e}")


@app.get("/dix")
async def dix_endeksi(
    semboller: str = Query(..., description="Virgulle ayrilmis sepet, orn. AAPL,MSFT,NVDA"),
    gun_geriye: int = Query(1, ge=1, le=10,
                            description="Kac is gunu geriye bakilsin (T+1 yayim)"),
):
    """DIX metodolojisi — borsa disi kisa hacim orani, sepet agirlikli.

    RESMI DIX DEGILDIR; kapsam, sepet ve agirlik farklari yanitin icinde
    acikca verilir. Sepette olup dosyada bulunmayan sembol SIFIR SAYILMAZ,
    kapsam disi olarak raporlanir.
    """
    sepet = [s.strip().upper() for s in (semboller or "").split(",") if s.strip()]
    if not sepet:
        raise HTTPException(status_code=400, detail="sepet bos")
    if len(sepet) > 600:
        raise HTTPException(status_code=400, detail="sepet en fazla 600 sembol")

    from datetime import date, timedelta
    g = date.today()
    bakilan = 0
    veri = None
    while bakilan < gun_geriye * 3 + 5:
        bakilan += 1
        g -= timedelta(days=1)
        if g.weekday() >= 5:
            continue
        veri = await regsho._gun_dosyasi(g)
        if veri:
            gun_geriye -= 1
            if gun_geriye <= 0:
                break
            veri = None
    if not veri:
        raise HTTPException(
            status_code=503,
            detail="Istenen gun icin FINRA gunluk dosyasi yayimlanmamis")
    sonuc = _dix.dix_hesapla(veri, sepet)
    sonuc["tarih"] = g.isoformat()
    return sonuc


@app.get("/regsho-durum")
async def regsho_durum():
    """Gunluk dosyalarin yayim durumu (teshis)."""
    try:
        return await regsho.kaynak_durumu()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{type(e).__name__}: {e}")
