"""
ALPHAWISE - Olay Tarayici (izole servis)

AMAC: kamuya ACIK ve RESMI kaynaklardan gelen olaylari erken fark etmek.
HENUZ ACIKLANMAMIS ya da GIZLI hicbir bilgiye erisim YOKTUR ve olamaz:
tum ag cikislari beyaz_liste.url_dogrula()'dan gecer, liste yalnizca
resmi duzenleyici ve kamu kurumu adreslerini icerir.

BU SERVIS YON IDDIASI URETMEZ. Cikti "olay tespit edildi, kaynagi su"
bicimindedir; karar kullaniciya aittir.
"""
import logging
import os

from fastapi import FastAPI, HTTPException, Query

from . import bildirim, kaynaklar, olay
from .beyaz_liste import KaynakReddedildi, liste_ozeti

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("olay-tarayici")

app = FastAPI(
    title="ALPHAWISE - Olay Tarayici",
    description="Resmi/kamuya acik kaynaklardan olay tespiti. Yon kodu uretmez.",
    version="1.0.0",
)

# Izlenen sirketler: CIK -> ad. Ortam degiskeniyle genisletilebilir.
VARSAYILAN_IZLEME = {
    320193: "Apple", 1045810: "NVIDIA", 789019: "Microsoft",
    1318605: "Tesla", 104169: "Walmart", 1090727: "UPS",
}


def _izleme() -> dict:
    ham = os.getenv("IZLENEN_CIKLER", "").strip()
    if not ham:
        return VARSAYILAN_IZLEME
    d = {}
    for p in ham.split(","):
        if ":" in p:
            c, a = p.split(":", 1)
            try:
                d[int(c.strip())] = a.strip()
            except ValueError:
                continue
    return d or VARSAYILAN_IZLEME


@app.get("/health")
def health():
    return {"service": "Olay Tarayici", "status": "ok",
            "izlenen_sirket": len(_izleme()),
            "bildirim_etkin": bildirim.ETKIN}


@app.get("/kaynaklar")
def kaynaklar_ucu():
    """Yasal sinirin seffaf dokumu — hangi adreslere cikilabilir."""
    return {
        "izinli_kaynaklar": liste_ozeti(),
        "kural": ("Iki katman: (1) host+yol beyaz listede olmali, "
                  "(2) kaynak kendi icerigini yayinlamali. Listede olmayan "
                  "bir adrese AG CAGRISI YAPILMADAN red donulur."),
        "disarida_birakilanlar": {
            "PR Newswire": "ToS: kisisel/ticari olmayan kullanim; robot ile erisim yasak",
            "Reuters": "halka acik RSS kapali (HTTP 401)",
            "AP": "HTTP 404",
            "Bloomberg": "ticari kullanim sartlari dogrulanamadi",
            "GlobeNewswire": "ToS sayfasi bulunamadi (404) — dogrulanmamis",
            "Nasdaq RSS": "icerigi kendi degil (ucuncu taraf sendikasyonu)",
            "sosyal medya / forum / dedikodu": "hicbir kosulda eklenemez",
        },
    }


@app.get("/olaylar")
def olaylar(gun: int = Query(3, ge=1, le=14)):
    """Izlenen sirketlerin son 8-K olaylari + kamu kurumu yayinlari."""
    bulunan, hatalar = [], []

    for cik, ad in _izleme().items():
        try:
            g = kaynaklar.sec_sirket_dosyalamalari(cik)
            bulunan.extend(olay.sekiz_k_olaylari(g, azami_gun=gun))
        except KaynakReddedildi as e:
            raise HTTPException(status_code=500, detail=f"Beyaz liste reddi: {e}")
        except Exception as e:
            hatalar.append({"sirket": ad, "hata": type(e).__name__})

    for kimlik, kurum in (("fed_basin", "Federal Reserve"),
                          ("bls_yayin", "Bureau of Labor Statistics"),
                          ("bea_yayin", "Bureau of Economic Analysis")):
        try:
            bulunan.extend(olay.akis_olaylari(kaynaklar.kurum_akisi(kimlik),
                                              kimlik, kurum, azami=3))
        except Exception as e:
            hatalar.append({"akis": kimlik, "hata": type(e).__name__})

    sekiz_k = [o for o in bulunan if o["tur"] == "sec_8k"]
    sekiz_k.sort(key=lambda o: (olay.ONEM_SIRASI[o["duzenleyici_onem"]],
                                -o["yas_saat"]), reverse=True)
    return {
        "pencere_gun": gun,
        "sec_8k_olaylari": sekiz_k,
        "kurum_yayinlari": [o for o in bulunan if o["tur"] == "kurum_yayini"],
        "hatalar": hatalar,
        "yon_kodu_uretir": False,
        "uyari": ("Bu servis yalnizca RESMI ve kamuya acik kaynaklardan "
                  "gozlem tasir. Yon tahmini, tavsiye ya da emir URETMEZ; "
                  "degerlendirme kullaniciya aittir."),
    }


@app.post("/bildir")
def bildir(gun: int = Query(1, ge=1, le=7), yalnizca_yuksek: bool = True):
    """
    Tespit edilen olaylar icin bildirim uretir.

    BILDIRIM_ETKIN=0 iken GERCEK MESAJ GONDERILMEZ; yalnizca onizleme
    dondurulur. Bu, kazayla disariya mesaj cikmasini engelleyen
    varsayilan-kapali tercihidir.
    """
    veri = olaylar(gun=gun)
    secili = veri["sec_8k_olaylari"]
    if yalnizca_yuksek:
        secili = [o for o in secili if o["duzenleyici_onem"] == "yuksek"]
    return {
        "aday_olay": len(secili),
        "sonuclar": [{"sirket": o.get("sirket"),
                      "itemlar": o.get("item_kodlari"),
                      "gonderim": bildirim.gonder(o)} for o in secili],
        "bildirim_etkin": bildirim.ETKIN,
    }
