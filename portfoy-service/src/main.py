"""portfoy-service — gercek defterden portfoy performans serisi (Madde 30)."""
from __future__ import annotations
import httpx
from fastapi import FastAPI

from .defter import islemleri_oku, karar_ozeti, DEFTER_YOLU
from .fiyat import gunluk_kapanislar
from .seri import seri_uret, ozet, tazelik

YASAL_UYARI = (
    "**YASAL UYARI:** Bu icerik yatirim danismanligi degildir. ALPHAWISE, "
    "hicbir finansal duzenleyici kurum nezdinde kayitli yatirim danismani "
    "degildir. Sistem hicbir pozisyon acma, kapama veya azaltma talimati "
    "vermez. Tum karar kodlari (EKLE/TUT/BEKLE/DIKKAT ET) kantitatif veri "
    "durumunu ifade eder, islem emri degildir. Gecmis performans gelecegin "
    "garantisi degildir. Kararlarinizi vermeden once lisansli bir finansal "
    "danismana danisin."
)

app = FastAPI(title="AlphaWise Portfoy Performansi", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "healthy", "servis": "portfoy", "defter": DEFTER_YOLU}


@app.get("/performans")
def performans(limit: int = 400):
    d = islemleri_oku()
    if d["durum"] != "okundu":
        return {"durum": d["durum"], "gerekce": d["gerekce"], "seri": None,
                "yasal_uyari": YASAL_UYARI}

    islemler = d["islemler"]
    semboller = sorted({i["sembol"] for i in islemler if i.get("sembol")})
    fiyatlar, fiyat_hatalari = {}, {}
    for s in semboller:
        f = gunluk_kapanislar(httpx, s, limit=limit)
        fiyatlar[s] = f["fiyatlar"]
        if f["gerekce"]:
            fiyat_hatalari[s] = f["gerekce"]

    seri = seri_uret(islemler, fiyatlar)
    return {
        "durum": seri["durum"],
        "defter_yolu": DEFTER_YOLU,
        "seri": seri,
        "ozet": ozet(seri, islemler),
        "tazelik": tazelik(seri),
        "karar_baglami": karar_ozeti(),
        "fiyat_hatalari": fiyat_hatalari,
        "not": ("Bu servis deftere HİÇBİR ŞEY YAZMAZ; dosya salt-okunur "
                "bağlanır. Boş nokta 'ölçülemedi' demektir, sıfır değil."),
        "yasal_uyari": YASAL_UYARI,
    }
