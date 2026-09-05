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
from .karsilastirma import sektor_karsilastir, ASGARI_RAKIP
from . import veri, onbellek

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


def _skor_hesapla(ticker: str, onbellek_kullan: bool = True):
    """Tek sirketin bes eksenini uretir. Sonuc onbellege yazilir; onbellek
    ayni zamanda sektor indeksini besler (bkz. onbellek.py)."""
    if onbellek_kullan:
        hazir = onbellek.oku(ticker)
        if hazir is not None:
            return {**hazir, "onbellekten": True}
    try:
        import yfinance as yf
    except ImportError:
        return {"ticker": ticker.upper(), "hata": "veri kutuphanesi yuklenemedi"}
    try:
        sirket = veri.sirket_getir(yf, ticker)
    except Exception as e:
        return {"ticker": ticker.upper(),
                "hata": f"mali tablo alinamadi: {type(e).__name__}"}
    if not sirket.donemler:
        return {"ticker": ticker.upper(),
                "hata": "Bu sembol icin mali tablo bulunamadi"}
    rf = veri.risksiz_faiz_getir(yf)
    sonuc = sentezle(sirket, risksiz_faiz=rf)
    sonuc["sirket_adi"] = sirket.piyasa.get("sirket_adi")
    sonuc["sektor"] = sirket.piyasa.get("sektor")
    sonuc["donem_sayisi"] = len(sirket.donemler)
    sonuc["risksiz_faiz"] = rf
    sonuc["veri_kaynagi"] = "yfinance (ucretsiz)"
    onbellek.yaz(ticker, sonuc)
    return {**sonuc, "onbellekten": False}


@app.get("/eksenler")
def eksenler():
    """Eksen tanimlari — hangi eksen hangi yayimlanmis olcute dayaniyor."""
    return {"eksenler": EKSEN_TANIMLARI, "asgari_eksen": ASGARI_EKSEN,
            "yasal_uyari": YASAL_UYARI}


@app.get("/skor/{ticker}")
def skor(ticker: str, taze: bool = False):
    sonuc = _skor_hesapla(ticker, onbellek_kullan=not taze)
    if "hata" in sonuc:
        kod = 404 if "bulunamadi" in sonuc["hata"] else 502
        return JSONResponse(status_code=kod,
                            content={**sonuc, "yasal_uyari": YASAL_UYARI})
    return {**sonuc, "yasal_uyari": YASAL_UYARI}


@app.get("/sektor-indeksi")
def sektor_indeksi():
    """Onbellekte GERCEKTEN bulunan sirketlerin sektor dagilimi.

    Indeks kendiliginden buyur: her /skor cagrisi bir sirketi ekler. Sistemde
    hazir bir sektor evreni olmadigi icin (olculdu: hicbir serviste sektor
    alani yok) rakip listesi UYDURULMAZ; indekste ne varsa o soylenir.
    """
    i = onbellek.sektor_indeksi()
    return {"sektorler": i,
            "toplam_sirket": sum(len(v) for v in i.values()),
            "asgari_rakip": ASGARI_RAKIP,
            "not": "Indeks yalnizca daha once /skor ile sorulmus sirketleri "
                   "icerir; eksik olmasi bir hata degil, bilinen sinirdir."}


@app.get("/karsilastir/{ticker}")
def karsilastir(ticker: str, rakipler: str = ""):
    """Sektor-normalize rakip karsilastirmasi (Madde 24).

    rakipler verilmezse sektor indeksinden secilir. Yeterli rakip yoksa
    sonuc URETILMEZ; kac rakip bulundugu ve neyin gerektigi soylenir.
    """
    hedef = _skor_hesapla(ticker)
    if "hata" in hedef:
        return JSONResponse(status_code=502,
                            content={**hedef, "yasal_uyari": YASAL_UYARI})

    istenen = [p.strip().upper() for p in rakipler.split(",") if p.strip()]
    kaynak = "acikca verildi"
    if not istenen:
        istenen = onbellek.sektordeki_rakipler(ticker, hedef.get("sektor"))
        kaynak = "sektor indeksi (onbellek)"

    if len(istenen) < ASGARI_RAKIP:
        return {
            "ticker": ticker.upper(), "sektor": hedef.get("sektor"),
            "hedef": hedef, "rakipler": istenen, "rakip_kaynagi": kaynak,
            "karsilastirma": None,
            "gerekce": (f"Yeterli rakip yok: {len(istenen)} sirket bulundu, "
                        f"en az {ASGARI_RAKIP} gerekiyor. Rakipleri acikca "
                        f"vermek icin ?rakipler=AAA,BBB,CCC kullanin."),
            "yasal_uyari": YASAL_UYARI,
        }

    rakip_skorlari = []
    for r in istenen:
        s = _skor_hesapla(r)
        if "hata" not in s:
            rakip_skorlari.append(s)

    k = sektor_karsilastir(hedef, rakip_skorlari)
    return {"ticker": ticker.upper(), "sektor": hedef.get("sektor"),
            "hedef": hedef, "rakip_kaynagi": kaynak,
            "istenen_rakip": len(istenen),
            "skoru_alinabilen_rakip": len(rakip_skorlari),
            "karsilastirma": k, "yasal_uyari": YASAL_UYARI}
