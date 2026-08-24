"""
ALPHAWISE - FRED Makro Servisi (9. piyasa sinyali)

NE SUNAR: Fed/BLS/BEA yayin TAKVIMI (bir sonraki TUFE, istihdam raporu,
PCE, GSYH ne zaman aciklanacak) ve sistemde HENUZ OLMAYAN makro
gostergeler.

LIQUIDITY-SIGNAL ILE KARISTIRILMAMALI:
  liquidity-signal-service  -> Fed BILANCO/LIKIDITE tesisati
                               (WALCL/TGA/RRP/M2), kalibrasyonu
                               BASARISIZ oldugu icin lambda=0'da,
                               yon iddiasi tasiyan kod uretmiyor.
  bu servis                 -> makro TAKVIM + getiri egrisi, cekirdek
                               PCE, istihdam, basvurular, guven, dolar.
  Kesisim: SIFIR seri. Ayrintili gerekce fred_client.py basliginda.

Bu servis de yon iddiasi URETMEZ: kalibrasyon_gecerli ve
yon_kodu_uretir alanlari DAIMA false'tur, cikti karar koduna
(EKLE/TUT/BEKLE/DIKKAT ET) BAGLANMAZ.
"""
import logging

from fastapi import FastAPI, HTTPException, Query

from . import fred_client

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("fred-macro")

app = FastAPI(
    title="ALPHAWISE - FRED Makro Servisi",
    description="Makro yayin takvimi ve gostergeler. Yon kodu uretmez.",
    version="1.0.0",
)

UYARI = (
    "Bu kart gozlemlenen resmi verileri ve yayin takvimini tasir. "
    "Gostergelerin AlphaWise icindeki ongoru gucu KALIBRE EDILMEMISTIR; "
    "cikti karar koduna baglanmaz. Takvim tarihleri FRED'in resmi yayin "
    "programindan gelir ve yayin kurumlari tarafindan degistirilebilir."
)


@app.get("/health")
def health():
    return {
        "service": "FRED Makro Servisi",
        "status": "ok",
        "anahtar": fred_client.anahtar_durumu(),
        "redis": fred_client.redis_durumu(),
    }


@app.get("/gostergeler")
def gostergeler():
    veri = fred_client.tum_gostergeler()
    return {
        "gostergeler": veri,
        "kaynak": "FRED (fredapi 0.5.2) — St. Louis Fed, ucretsiz",
        "kalibrasyon_gecerli": False,
        "yon_kodu_uretir": False,
        "uyari": UYARI,
    }


@app.get("/takvim")
def takvim(gun: int = Query(30, ge=1, le=90)):
    try:
        return fred_client.yaklasan_yayinlar(gun)
    except Exception as e:
        logger.warning("Takvim alinamadi: %s: %s", type(e).__name__, e)
        raise HTTPException(status_code=502, detail="FRED takvimi su an alinamadi")


@app.get("/ozet")
def ozet(gun: int = Query(30, ge=1, le=90)):
    """Dashboard kartinin okudugu birlesik uc."""
    try:
        gost = fred_client.tum_gostergeler()
    except Exception as e:
        logger.warning("Gostergeler alinamadi: %s: %s", type(e).__name__, e)
        raise HTTPException(status_code=502, detail="FRED gostergeleri su an alinamadi")

    try:
        tak = fred_client.yaklasan_yayinlar(gun)
        takvim_hatasi = None
    except Exception as e:
        # Takvim duserse gostergeler yine de gosterilsin — kart bos kalmasin.
        logger.warning("Takvim alinamadi (gostergeler donuyor): %s", e)
        tak = {"yaklasan": [], "adet": 0, "pencere_gun": gun}
        takvim_hatasi = type(e).__name__

    basarili = [g for g in gost if g.get("veri_var")]
    return {
        "gostergeler": gost,
        "gosterge_tamlik": f"{len(basarili)}/{len(gost)}",
        "takvim": tak,
        "takvim_hatasi": takvim_hatasi,
        "kaynak": "FRED (fredapi 0.5.2 + resmi /releases/dates ucu) — ucretsiz",
        "kalibrasyon_gecerli": False,
        "yon_kodu_uretir": False,
        "uyari": UYARI,
    }
