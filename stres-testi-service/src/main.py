"""stres-testi-service — kriz stres testi + Monte Carlo dusus dagilimi (Madde 26)."""
from __future__ import annotations
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .kriz import tarihsel_stres, KRIZLER, ASGARI_GUN
from .montecarlo import (gunluk_getiriler, dusus_dagilimi, VARSAYILAN_YOL,
                         VARSAYILAN_UFUK, VARSAYILAN_BLOK)
from . import veri

YASAL_UYARI = (
    "**YASAL UYARI:** Bu icerik yatirim danismanligi degildir. ALPHAWISE, "
    "hicbir finansal duzenleyici kurum nezdinde kayitli yatirim danismani "
    "degildir. Sistem hicbir pozisyon acma, kapama veya azaltma talimati "
    "vermez. Tum karar kodlari (EKLE/TUT/BEKLE/DIKKAT ET) kantitatif veri "
    "durumunu ifade eder, islem emri degildir. Gecmis performans gelecegin "
    "garantisi degildir. Kararlarinizi vermeden once lisansli bir finansal "
    "danismana danisin."
)

app = FastAPI(title="AlphaWise Kriz Stres Testi", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "healthy", "servis": "stres-testi",
            "kriz_sayisi": len(KRIZLER)}


@app.get("/krizler")
def krizler():
    return {"krizler": KRIZLER, "asgari_gun": ASGARI_GUN,
            "not": ("Pencereler takvim yili DEGIL, zirve->dip tarihleridir. "
                    "Takvim yili kullanmak COVID cokusunu onu izleyen "
                    "toparlanmayla goturur ve krizi neredeyse gorunmez kilar."),
            "yasal_uyari": YASAL_UYARI}


@app.get("/stres/{ticker}")
def stres(ticker: str, yol: int = VARSAYILAN_YOL, ufuk: int = VARSAYILAN_UFUK,
          blok: int = VARSAYILAN_BLOK, tohum: int = 20260906):
    if yol < 100 or yol > 20000:
        return JSONResponse(status_code=400,
                            content={"hata": "yol 100 ile 20000 arasinda olmali"})
    if ufuk < 20 or ufuk > 1260:
        return JSONResponse(status_code=400,
                            content={"hata": "ufuk 20 ile 1260 arasinda olmali"})
    try:
        import yfinance as yf
    except ImportError:
        yf = None
    seri, kaynak = veri.seri_getir(ticker, yf)
    if not seri:
        return JSONResponse(status_code=404, content={
            "ticker": ticker.upper(), "hata": "Fiyat serisi bulunamadi",
            "kaynak": kaynak, "yasal_uyari": YASAL_UYARI})

    gunler = sorted(seri)
    getiriler = gunluk_getiriler([seri[g] for g in gunler])

    # IKI YONTEM DE bildirilir: yontem secimi tek basina "dogru sayi"
    # uretmez ve aradaki fark veriye bagli olarak yon degistirir
    # (bkz. montecarlo.py docstring'indeki MSFT olcumu).
    blok_sonuc = dusus_dagilimi(getiriler, yol_sayisi=yol, ufuk=ufuk,
                                blok=blok, tohum=tohum, yontem="blok")
    iid_sonuc = dusus_dagilimi(getiriler, yol_sayisi=yol, ufuk=ufuk,
                               tohum=tohum, yontem="iid")

    return {
        "ticker": ticker.upper(),
        "veri_kaynagi": kaynak,
        "veri_araligi": {"en_eski": gunler[0], "en_yeni": gunler[-1],
                         "islem_gunu": len(gunler)},
        "tarihsel_krizler": tarihsel_stres(seri),
        "monte_carlo": {
            "blok_bootstrap": blok_sonuc,
            "bagimsiz_ornekleme": iid_sonuc,
            "not": ("Iki yontem de bildirilir. Blok ornekleme serideki sirali "
                    "yapiyi korur, bagimsiz ornekleme yok eder; hangisinin "
                    "daha derin dusus urettigi VERIYE BAGLIDIR ve tek bir "
                    "sayiya guvenmemek icin ikisi de gosterilir."),
        },
        "yasal_uyari": YASAL_UYARI,
    }
