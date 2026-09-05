"""
skor-sentezi-service — bes eksenli temel skor sentezi HTTP servisi.

Bu servis KENDI konteynerinde calisir ve mevcut hicbir servise dokunmaz.
Karar kodu URETMEZ: yalnizca bes ekseni ve gerekcelerini yayinlar; karar
uretimi MAA'nin (korunmus) isidir.
"""
from __future__ import annotations
import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .sentez import sentezle, EKSEN_TANIMLARI, ASGARI_EKSEN
from . import veri

# Anayasa Madde 1.4 geregi her cikti bu uyariyi tasir. Metin, servis
# bagimsizligi icin burada da tutulur; maa/src/constitution.py ile
# AYNI kalmasi tests/test_sozlesme.py tarafindan denetlenir.
YASAL_UYARI = (
    "**YASAL UYARI:** Bu icerik yatirim danismanligi degildir. ALPHAWISE, "
    "hicbir finansal duzenleyici kurum nezdinde kayitli yatirim danismani "
    "degildir. Sistem hicbir pozisyon acma, kapama veya azaltma talimati "
    "vermez. Tum karar kodlari (EKLE/TUT/BEKLE/DIKKAT ET) kantitatif veri "
    "durumunu ifade eder, islem emri degildir. Gecmis performans gelecegin "
    "garantisi degildir. Kararlarinizi vermeden once lisansli bir finansal "
    "danismana danisin."
)

app = FastAPI(title="AlphaWise Skor Sentezi", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "healthy", "servis": "skor-sentezi",
            "eksen_sayisi": len(EKSEN_TANIMLARI), "asgari_eksen": ASGARI_EKSEN}


@app.get("/eksenler")
def eksenler():
    """Eksen tanimlari — hangi eksen hangi yayimlanmis olcute dayaniyor."""
    return {"eksenler": EKSEN_TANIMLARI, "asgari_eksen": ASGARI_EKSEN,
            "yasal_uyari": YASAL_UYARI}


@app.get("/skor/{ticker}")
def skor(ticker: str):
    try:
        import yfinance as yf
    except ImportError:
        return JSONResponse(status_code=503,
                            content={"ticker": ticker.upper(),
                                     "hata": "veri kutuphanesi yuklenemedi"})
    try:
        sirket = veri.sirket_getir(yf, ticker)
    except Exception as e:
        return JSONResponse(status_code=502, content={
            "ticker": ticker.upper(),
            "hata": f"mali tablo alinamadi: {type(e).__name__}",
            "yasal_uyari": YASAL_UYARI})

    if not sirket.donemler:
        return JSONResponse(status_code=404, content={
            "ticker": ticker.upper(),
            "hata": "Bu sembol icin mali tablo bulunamadi",
            "yasal_uyari": YASAL_UYARI})

    rf = veri.risksiz_faiz_getir(yf)
    sonuc = sentezle(sirket, risksiz_faiz=rf)
    sonuc["sirket_adi"] = sirket.piyasa.get("sirket_adi")
    sonuc["sektor"] = sirket.piyasa.get("sektor")
    sonuc["donem_sayisi"] = len(sirket.donemler)
    sonuc["risksiz_faiz"] = rf
    sonuc["veri_kaynagi"] = "yfinance (ucretsiz)"
    sonuc["yasal_uyari"] = YASAL_UYARI
    return sonuc
