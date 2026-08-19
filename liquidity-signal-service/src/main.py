"""
ALPHAWISE - Liquidity Signal Service

M2Quant metodolojisinin AlphaWise mimarisine uyarlanmis, kalibrasyonu
dogrulanmis versiyonu. FRED (WALCL/TGA/RRP) net likidite skoru
uretir, anayasa v4.4 karar kodlarina (EKLE/TUT/BEKLE/DIKKAT ET) cevirir.

Kalibrasyon test penceresinde (2024-2026) BASARISIZ oldugu icin
suanki bayrak: yon iddiasi tasiyan kodlar (EKLE/DIKKAT ET) URETILMIYOR.
Yalnizca izleme/uyari kodlari (TUT/BEKLE) uretilir.
"""
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from . import fred_client, factors
from .anayasa_dili import (
    skor_to_kod, guven_seviyesi, oneri_metni, yanit_denetle
)
from .kalibrasyon import KALIBRASYON

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
# GUVENLIK: httpx INFO seviyesinde tam URL loglar; api_key query paraminda gorulur.
# Bu servis FRED_API_KEY'i asla loga yazmamali — httpx sessize aliniyor.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger("liquidity-signal")

_baslangic_dogrulama: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _baslangic_dogrulama
    logger.info("Baslangic: FRED anahtar dogrulamasi yapiliyor...")
    _baslangic_dogrulama = await fred_client.anahtar_dogrula()
    if not _baslangic_dogrulama.get("gecerli"):
        logger.warning(
            "BASLANGIC UYARISI: FRED_API_KEY GECERSIZ — detay: %s",
            _baslangic_dogrulama.get("detay"),
        )
    else:
        logger.info("FRED anahtari gecerli, servis hazir")

    if not KALIBRASYON["gecerli"]:
        logger.warning(
            "KALIBRASYON BAYRAK: gecersiz — yon iddiasi tasiyan kodlar "
            "URETILMIYOR (buzusme_lambda=%s). Gerekce: %s",
            KALIBRASYON["buzusme_lambda"],
            KALIBRASYON["gerekce"][:100] + "...",
        )
    yield


app = FastAPI(
    title="ALPHAWISE - Liquidity Signal Service",
    description=(
        "FRED (Fed) likidite gostergelerinden anayasa karar kodu uretir. "
        "M2Quant metodolojisinin kalibre edilmis AlphaWise uyarlamasi."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


VARLIK_ETIKETLERI = {
    "nasdaq": "Nasdaq Composite (^IXIC)",
    "sp500": "S&P 500 Composite",
    "btc": "Bitcoin (Coinbase USD)",
}


def _veri_tamligi(walcl, tga, rrp, ast) -> float:
    """Son 60 gundeki eksik veri oranindan tersini dondur (0-1)."""
    n = min(60, len(walcl))
    if n == 0: return 0.0
    total = 0; dolu = 0
    for i in range(len(walcl) - n, len(walcl)):
        total += 4
        for s in (walcl, tga, rrp, ast):
            if s[i] is not None: dolu += 1
    return dolu / total if total > 0 else 0.0


def _son_bilesen(s):
    """Serinin son non-None degerini dondur."""
    for v in reversed(s):
        if v is not None: return v
    return None


@app.get("/health")
async def health(dogrula: bool = Query(False, description="True ise anahtari canli dogrular")):
    global _baslangic_dogrulama
    if dogrula:
        _baslangic_dogrulama = await fred_client.anahtar_dogrula()
    fred_gecerli = _baslangic_dogrulama.get("gecerli", False)
    uyarilar = []
    if not fred_gecerli:
        uyarilar.append("FRED_API_KEY gecersiz — canli veri cekilemez")
    if not KALIBRASYON["gecerli"]:
        uyarilar.append(
            f"DENEYSEL SERVIS — kalibrasyon gecersiz: {KALIBRASYON['denenen_spesifikasyon']} "
            f"spesifikasyondan {KALIBRASYON['basarili_spesifikasyon']} tanesi gecme esigini "
            f"(+{KALIBRASYON['gecme_esigi_puan']} puan) asti. En iyi olculen beceri "
            f"{KALIBRASYON['en_iyi_beceri_puan']:+.2f} puan, en dusuk p={KALIBRASYON['en_dusuk_p']}. "
            "Yon iddiasi tasiyan kodlar (EKLE, DIKKAT ET) URETILMEZ."
        )
    durum = "ok" if fred_gecerli else "degraded"
    return {
        "status": durum,
        "service": "liquidity-signal-service",
        # KAPSAM DURUSTLUGU: cagiran taraf (God Mode) bu servisin
        # dogrulanmis bir yon kenari OLMADIGINI tek bakista gormeli.
        "olgunluk": KALIBRASYON["durum"],
        "yon_kodu_uretir": KALIBRASYON["yon_kodu_uretir"],
        "kullanim_amaci": ("izleme ve baglam verisi; yon karari icin "
                           "girdi olarak KULLANILMAMALIDIR"),
        "uyarilar": uyarilar,
        "fred_anahtari": fred_client.anahtar_durumu(),
        "fred_dogrulama": _baslangic_dogrulama,
        "kalibrasyon_gecerli": KALIBRASYON["gecerli"],
        "buzusme_lambda": KALIBRASYON["buzusme_lambda"],
        "kalibrasyon_ozeti": {
            "denenen_spesifikasyon": KALIBRASYON["denenen_spesifikasyon"],
            "basarili_spesifikasyon": KALIBRASYON["basarili_spesifikasyon"],
            "en_iyi_beceri_puan": KALIBRASYON["en_iyi_beceri_puan"],
            "gecme_esigi_puan": KALIBRASYON["gecme_esigi_puan"],
            "en_dusuk_p": KALIBRASYON["en_dusuk_p"],
            "yeniden_uret": KALIBRASYON["yeniden_uret"],
        },
        "redis": fred_client.redis_durumu(),
    }


@app.get("/methodology")
async def methodology():
    """Kalibrasyon meta-verisi ve metodoloji ozeti."""
    return {
        "olgunluk": KALIBRASYON["durum"],
        "yon_kodu_uretir": KALIBRASYON["yon_kodu_uretir"],
        "elenen_alternatifler": KALIBRASYON["elenen_alternatifler"],
        "metrik": KALIBRASYON["metrik"],
        "kalibrasyon": KALIBRASYON,
        "faktor_parametreleri": {
            "z_penceresi": factors.Z_WINDOW,
            "momentum_penceresi": factors.MOMENTUM_WINDOW,
            "yoy_donem": factors.YOY_PERIODS,
            "rejim_kisa_ma": factors.REGIME_SHORT,
            "rejim_uzun_ma": factors.REGIME_LONG,
            "scissors_z_esigi": factors.SCISSORS_Z_THRESHOLD,
        },
        "veri_kaynaklari": {
            "likidite": ["WALCL", "WTREGEN", "RRPONTSYD"],
            "varliklar": {"nasdaq": "NASDAQCOM", "sp500": "SP500", "btc": "CBBTCUSD"},
        },
        "cikti_kodlari": ["EKLE", "TUT", "BEKLE", "DIKKAT ET"],
        "dil_kurali": "olasi/desteklenebilir, emir kipi yok, kesin ifade yok",
    }


@app.get("/regime")
async def rejim_endpoint():
    """
    Anlik likidite rejim degerlendirmesi (varliksiz, sadece Fed likiditesi).
    Herhangi bir varlik icin karar kodu URETMEZ — sadece rejim adi ve
    ham metrikler.
    """
    veri = await fred_client.fetch_all_liquidity()
    walcl_d = {d: v for d, v in veri["walcl"]}
    tga_d = {d: v for d, v in veri["tga"]}
    rrp_d = {d: v for d, v in veri["rrp"]}

    if not walcl_d or not tga_d or not rrp_d:
        raise HTTPException(status_code=502, detail="FRED verisi eksik")

    son_gun = max(max(walcl_d), max(tga_d), max(rrp_d))
    gunler = factors.gunluk_esik("2022-01-01", son_gun)

    walcl = factors.ffill(gunler, walcl_d)
    tga = factors.ffill(gunler, tga_d)
    rrp = factors.ffill(gunler, rrp_d)
    net_liq = factors.net_likidite(walcl, tga, rrp)

    liq_z = factors.zscore(net_liq)
    liq_yoy = factors.yoy_pct(net_liq)
    liq_mom = factors.momentum(net_liq)

    idx = len(gunler) - 1
    rej = factors.rejim(idx, net_liq, liq_mom)

    return {
        "son_gun": son_gun,
        "net_likidite_milyon_usd": _son_bilesen(net_liq),
        "walcl_milyon_usd": _son_bilesen(walcl),
        "tga_milyon_usd": _son_bilesen(tga),
        "rrp_milyar_usd": _son_bilesen(rrp),
        "z_skor_60g": _son_bilesen(liq_z),
        "yoy_yuzde": _son_bilesen(liq_yoy),
        "momentum_20g_yuzde": _son_bilesen(liq_mom),
        "rejim": rej,
        "kalibrasyon_gecerli": KALIBRASYON["gecerli"],
    }


@app.get("/assessment/{varlik}")
async def assessment(varlik: str):
    """
    Bir varlik icin kompozit skor + anayasa karar kodu.
    Kalibrasyon gecersiz oldugu icin yalnizca TUT veya BEKLE dondurur.
    """
    varlik = varlik.lower()
    if varlik not in VARLIK_ETIKETLERI:
        raise HTTPException(
            status_code=400,
            detail=f"Desteklenen varliklar: {list(VARLIK_ETIKETLERI.keys())}",
        )

    veri = await fred_client.fetch_all_liquidity()
    walcl_d = {d: v for d, v in veri["walcl"]}
    tga_d = {d: v for d, v in veri["tga"]}
    rrp_d = {d: v for d, v in veri["rrp"]}
    ast_d = {d: v for d, v in veri[varlik]}

    if not walcl_d or not tga_d or not rrp_d or not ast_d:
        raise HTTPException(status_code=502, detail=f"FRED verisi eksik ({varlik})")

    son_gun = min(max(walcl_d), max(tga_d), max(rrp_d), max(ast_d))
    gunler = factors.gunluk_esik("2022-01-01", son_gun)

    walcl = factors.ffill(gunler, walcl_d)
    tga = factors.ffill(gunler, tga_d)
    rrp = factors.ffill(gunler, rrp_d)
    ast = factors.ffill(gunler, ast_d)

    net_liq = factors.net_likidite(walcl, tga, rrp)
    liq_z = factors.zscore(net_liq)
    liq_yoy = factors.yoy_pct(net_liq)
    liq_mom = factors.momentum(net_liq)

    ast_z = factors.zscore(ast)
    ast_yoy = factors.yoy_pct(ast)
    ast_mom = factors.momentum(ast)

    sci = factors.scissors(liq_yoy, ast_yoy)
    sci_z = factors.zscore(sci)
    dev = factors.deviation(ast_z, liq_z)

    idx = len(gunler) - 1
    rej = factors.rejim(idx, net_liq, liq_mom)
    skor = factors.composite_skor(rej, sci_z[idx], dev[idx],
                                  liq_mom[idx], ast_mom[idx])
    tamlik = _veri_tamligi(walcl, tga, rrp, ast)
    kod = skor_to_kod(skor, KALIBRASYON["gecerli"])
    guven = guven_seviyesi(KALIBRASYON["gecerli"], tamlik)
    oneri = oneri_metni(kod, guven)

    yanit = {
        "varlik": varlik,
        "etiket": VARLIK_ETIKETLERI[varlik],
        "son_gun": son_gun,
        "kod": kod,
        "guven": guven,
        "oneri": oneri,
        "kompozit_skor": round(skor, 3),
        "faktor_detay": {
            "rejim": rej,
            "scissors_z": round(sci_z[idx], 3) if sci_z[idx] is not None else None,
            "deviation": round(dev[idx], 3) if dev[idx] is not None else None,
            "likidite_momentum_yuzde": round(liq_mom[idx], 3) if liq_mom[idx] is not None else None,
            "varlik_momentum_yuzde": round(ast_mom[idx], 3) if ast_mom[idx] is not None else None,
            "likidite_z_skor": round(liq_z[idx], 3) if liq_z[idx] is not None else None,
            "varlik_z_skor": round(ast_z[idx], 3) if ast_z[idx] is not None else None,
            "veri_tamligi": round(tamlik, 3),
        },
        "kalibrasyon": {
            "gecerli": KALIBRASYON["gecerli"],
            "buzusme_lambda": KALIBRASYON["buzusme_lambda"],
            "not": (
                "Kalibrasyon gecersiz — yon iddiasi tasiyan kodlar "
                "(EKLE, DIKKAT ET) uretilmez. Sadece TUT/BEKLE dondurulur."
                if not KALIBRASYON["gecerli"] else "Kalibre edilmis."
            ),
        },
    }
    yanit["dil_denetimi"] = yanit_denetle(yanit)
    return yanit
