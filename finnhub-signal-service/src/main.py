"""
ALPHAWISE - Finnhub Sinyal Servisi (10. piyasa sinyali)

NE SUNAR: bir hisse icin sirket TAKVIMI ve HABER YOGUNLUGU baglami —
yaklasan bilanco tarihi, son 7 gunun haber adedi ve secili basliklar,
anlik fiyat gorunumu ve birkac temel metrik.

MEVCUT SERVISLERLE ILISKISI (bilerek dar tutuldu):
  - saa ve news-monitor de /company-news okuyor, ama onlar ARKA PLAN
    boru hatlaridir (FinBERT duygu analizi / izleme). Dashboard'da haber
    ya da bilanco takvimi gosteren HICBIR kart yoktu.
  - Bu servis yon iddiasi URETMEZ, duygu skoru HESAPLAMAZ. Yalnizca
    gozlemlenen olgular tasir.

KALIBRASYON: bu servisin gostergeleri AlphaWise icinde KALIBRE EDILMEDI.
Bu yuzden kalibrasyon_gecerli ve yon_kodu_uretir alanlari DAIMA false'tur
ve cikti karar koduna (EKLE/TUT/BEKLE/DIKKAT ET) BAGLANMAZ.
"""
import logging
import re

from fastapi import FastAPI, HTTPException

from . import finnhub_client
from .dil import yanit_denetle
from .kota import KotaDoldu

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("finnhub-signal")

app = FastAPI(
    title="ALPHAWISE - Finnhub Sinyal Servisi",
    description="Sirket takvimi ve haber yogunlugu baglami. Yon kodu uretmez.",
    version="1.0.0",
)

# Disaridan gelen tek serbest girdi. '/' ve '.' dizilimlerini reddettigi
# icin yol asimi daha ilk kapida engellenir (MAA proxy'siyle ayni desen).
TICKER_DESENI = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,9}$")


@app.get("/health")
def health():
    return {
        "service": "Finnhub Sinyal Servisi",
        "status": "ok",
        "anahtar_havuzu": finnhub_client.anahtar_durumu()["havuz_boyutu"],
    }


@app.get("/kota")
def kota():
    return finnhub_client.sayac().durum()


@app.get("/sirket/{ticker}")
def sirket(ticker: str):
    t = (ticker or "").upper()
    if not TICKER_DESENI.match(t):
        # Sabit metin: kullanici girdisi yansitilmaz.
        raise HTTPException(status_code=400, detail="Gecersiz hisse kodu")

    try:
        fiyat = finnhub_client.anlik_fiyat(t)
        haber = finnhub_client.haberler(t)
        bilanco = finnhub_client.bilanco_takvimi(t)
        metrik = finnhub_client.temel_metrikler(t)
    except KotaDoldu as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        logger.warning("Finnhub cagrisi basarisiz: %s: %s", type(e).__name__, e)
        raise HTTPException(status_code=502,
                            detail="Finnhub verisi su an alinamadi")

    yanit = {
        "ticker": t,
        "anlik_fiyat": fiyat,
        "haber": haber,
        "bilanco_takvimi": bilanco,
        "temel_metrikler": metrik,
        "kota": finnhub_client.sayac().durum(),
        "kaynak": "Finnhub ucretsiz katman (olculen limit: anahtar basina 60 istek/dakika)",
        "kalibrasyon_gecerli": False,
        "yon_kodu_uretir": False,
        "uyari": (
            "Bu kart gozlemlenen olgulari tasir: yaklasan bilanco tarihi, "
            "haber adedi ve ucuncu taraf basliklar. Basliklar Finnhub'dan "
            "geldigi gibi aktarilir; AlphaWise'in degerlendirmesi degildir "
            "ve duygu analizi uygulanmamistir. Bu gostergelerin ongoru gucu "
            "bu sistemde kalibre edilmemistir ve karar koduna baglanmaz."
        ),
    }

    # Kendi urettigimiz metinlerde dil ihlali var mi (ucuncu taraf
    # basliklar bilerek denetim disidir — bkz. src/dil.py).
    denetim = yanit_denetle(yanit)
    if not denetim["temiz"]:
        logger.error("DIL IHLALI: %s", denetim["ihlaller"])
        raise HTTPException(status_code=500, detail="Dil denetimi basarisiz")

    return yanit
