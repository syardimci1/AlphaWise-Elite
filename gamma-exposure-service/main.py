"""
ALPHAWISE - Gamma Exposure Service (19.08.2026)

Iki bagimsiz parca:

  PARCA A - GEX (Gamma Exposure)
    Kaynak: FlashAlpha (lab.flashalpha.com/v1), X-Api-Key header'i.
    Her ucretsiz anahtar GUNDE 5 ISTEK ile sinirli. FLASHALPHA_API_KEY_1..N
    seklinde birden fazla anahtar tanimlanabilir (llmquant_client.py'deki
    cok-anahtarli yedekleme desenine benzer sekilde): her anahtarin kendi
    gunluk sayaci Redis'te "gex:quota:<anahtar_adi>:YYYY-MM-DD" ile tutulur,
    biri kotasi dolunca veya hata verince otomatik siradaki anahtara
    gecilir. TUM anahtarlarin kotasi dolunca sessizce hata verilmez, net
    bir "kota doldu, yarin tekrar dene" yaniti donulur.

  PARCA B - DIX-benzeri gosterge
    YENI DIS API YOK. Ayni ag uzerindeki finra-darkpool-service'in (8200)
    zaten sagladigi haftalik FINRA ATS verisi HTTP ile cagrilir ve
    gosterge BU SERVIS ICINDE hesaplanir.

MAA kaskadina ve daha once kurulan uc servise (institution-filter,
finra-darkpool, congress-trading) DOKUNULMAZ; finra-darkpool yalnizca
disaridan, salt-okunur HTTP ile tuketilir.
Redis isim alani: "gex:" (ifs:, finra:dp:, congress:, llmquant: ile carpismaz)
"""
import os
import json
from datetime import datetime, timezone, timedelta

import httpx
import redis
from fastapi import FastAPI, Query, HTTPException

app = FastAPI(
    title="ALPHAWISE - Gamma Exposure Service",
    description="FlashAlpha GEX (kota korumali) + kendi verimizden DIX-benzeri gosterge",
    version="1.0.0",
)

FLASHALPHA_BASE = os.getenv("FLASHALPHA_BASE_URL", "https://lab.flashalpha.com/v1")
FINRA_DARKPOOL_URL = os.getenv("FINRA_DARKPOOL_URL", "http://alphawise-finra-darkpool:8000")
ANAHTAR_BASINA_GUNLUK_KOTA = int(os.getenv("FLASHALPHA_DAILY_QUOTA", "5"))
CACHE_PREFIX = "gex:"
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "30"))
GECIS_KODLARI = {401, 403, 429}  # bu kodlarda siradaki anahtara gecilir


def _flashalpha_anahtarlari():
    """
    FLASHALPHA_API_KEY_1, FLASHALPHA_API_KEY_2, ... seklinde tanimli tum
    anahtarlari sirayla dondurur. Geriye donuk uyumluluk icin tek anahtarli
    FLASHALPHA_API_KEY de (varsa) listenin basina eklenir.
    Doner: [(anahtar_adi, deger), ...]
    """
    anahtarlar = []
    tekil = os.getenv("FLASHALPHA_API_KEY")
    if tekil:
        anahtarlar.append(("FLASHALPHA_API_KEY", tekil))
    i = 1
    while True:
        ad = f"FLASHALPHA_API_KEY_{i}"
        deger = os.getenv(ad)
        if not deger:
            break
        anahtarlar.append((ad, deger))
        i += 1
    return anahtarlar

_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD"),
            db=int(os.getenv("REDIS_DB", "0")),  # test/izolasyon icin farkli DB secilebilir
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
    return _redis_client


def redis_durumu():
    try:
        _get_redis().ping()
        return {"connected": True}
    except Exception as e:
        return {"connected": False, "detail": str(e)[:200]}


# --- Kota yonetimi -----------------------------------------------------------

def _bugun():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _gece_yarisina_kalan_saniye():
    simdi = datetime.now(timezone.utc)
    yarin = (simdi + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(60, int((yarin - simdi).total_seconds()))


def _kota_redis_anahtari(anahtar_adi):
    return f"{CACHE_PREFIX}quota:{anahtar_adi}:{_bugun()}"


def _sifirlanma_utc():
    return (datetime.now(timezone.utc) + timedelta(seconds=_gece_yarisina_kalan_saniye())).strftime("%Y-%m-%d %H:%M:%S UTC")


def tek_anahtar_kota_durumu(anahtar_adi):
    """Tek bir FlashAlpha anahtarinin gunluk kullanimini okur (artirmiaz)."""
    try:
        ham = _get_redis().get(_kota_redis_anahtari(anahtar_adi))
        kullanilan = int(ham) if ham else 0
    except Exception as e:
        return {"anahtar": anahtar_adi, "hata": f"Redis okunamadi: {str(e)[:120]}"}
    return {
        "anahtar": anahtar_adi,
        "kullanilan": kullanilan,
        "gunluk_kota": ANAHTAR_BASINA_GUNLUK_KOTA,
        "kalan": max(0, ANAHTAR_BASINA_GUNLUK_KOTA - kullanilan),
        "kota_doldu": kullanilan >= ANAHTAR_BASINA_GUNLUK_KOTA,
    }


def kota_durumu():
    """
    Tanimli TUM FlashAlpha anahtarlarinin gunluk kullanimini ve toplam
    kapasiteyi doner. Hicbir sayaci artirmaz.
    """
    anahtarlar = _flashalpha_anahtarlari()
    if not anahtarlar:
        return {
            "tarih_utc": _bugun(),
            "tanimli_anahtar_sayisi": 0,
            "toplam_gunluk_kota": 0,
            "toplam_kullanilan": 0,
            "toplam_kalan": 0,
            "kota_doldu": True,
            "anahtar_basina": [],
        }
    anahtar_basina = [tek_anahtar_kota_durumu(ad) for ad, _ in anahtarlar]
    toplam_kullanilan = sum(a.get("kullanilan", 0) for a in anahtar_basina)
    toplam_kota = ANAHTAR_BASINA_GUNLUK_KOTA * len(anahtarlar)
    return {
        "tarih_utc": _bugun(),
        "tanimli_anahtar_sayisi": len(anahtarlar),
        "anahtar_basina_gunluk_kota": ANAHTAR_BASINA_GUNLUK_KOTA,
        "toplam_gunluk_kota": toplam_kota,
        "toplam_kullanilan": toplam_kullanilan,
        "toplam_kalan": max(0, toplam_kota - toplam_kullanilan),
        "kota_doldu": all(a.get("kota_doldu") for a in anahtar_basina),
        "anahtar_basina": anahtar_basina,
        "sifirlanma_utc": _sifirlanma_utc(),
    }


def _tek_anahtar_kota_ayir(anahtar_adi):
    """
    Tek bir anahtarin kotasindan atomik olarak 1 birim ayirir.
    Doner: (izin_verildi: bool, kullanilan_sonrasi: int)
    Kota asilirsa sayac geri alinir ki raporlanan deger dogru kalsin.
    """
    r = _get_redis()
    rk = _kota_redis_anahtari(anahtar_adi)
    n = r.incr(rk)
    if n == 1:
        r.expire(rk, _gece_yarisina_kalan_saniye())
    if n > ANAHTAR_BASINA_GUNLUK_KOTA:
        r.decr(rk)
        return False, ANAHTAR_BASINA_GUNLUK_KOTA
    return True, n


# --- PARCA A: FlashAlpha GEX -------------------------------------------------

@app.get("/gex/{ticker}")
async def gamma_exposure(
    ticker: str,
    expiration: str = Query(
        None,
        description=(
            "YYYY-MM-DD. Ucretsiz FlashAlpha tier'i FULL-CHAIN (tum vadeler) GEX'i "
            "Growth plan'a kisitlar; tek bir vadeyle filtrelemek Free planda calisir."
        ),
    ),
):
    """
    FlashAlpha'dan gamma exposure. Birden fazla anahtar tanimliysa
    (FLASHALPHA_API_KEY_1..N) sirayla denenir: bir anahtarin gunluk kotasi
    dolmussa VEYA istek 401/403/429 donmusse otomatik siradaki anahtara
    gecilir (llmquant_client.py'deki cok-anahtarli yedekleme desenine
    benzer). TUM anahtarlarin kotasi dolduysa HTTP 429 ve net bir aciklama
    doner (sessiz hata YOK).
    """
    ticker = ticker.upper().strip()
    anahtarlar = _flashalpha_anahtarlari()
    if not anahtarlar:
        raise HTTPException(
            status_code=503,
            detail={
                "hata": "Hicbir FLASHALPHA_API_KEY_* tanimli degil",
                "aciklama": (
                    "FlashAlpha ucretsiz tier anahtari gerekli (kredi karti istemiyor). "
                    "flashalpha.com uzerinden e-posta ile kayit olup anahtari "
                    "gamma-exposure-service/.env icine FLASHALPHA_API_KEY_1 (gerekirse "
                    "_2, _3, ... ile devam) olarak ekleyin."
                ),
                "kota_durumu": kota_durumu(),
            },
        )

    on_durum = kota_durumu()
    if on_durum.get("kota_doldu"):
        raise HTTPException(
            status_code=429,
            detail={
                "hata": "Tum FlashAlpha anahtarlarinin gunluk kotasi doldu",
                "mesaj": (
                    f"{on_durum['tanimli_anahtar_sayisi']} anahtarin toplam "
                    f"{on_durum['toplam_gunluk_kota']} istek hakkinin tamami kullanildi. "
                    "Yarin tekrar deneyin."
                ),
                "kota_durumu": on_durum,
                "istek_yapilmadi": True,
            },
        )

    son_hata = None
    for anahtar_adi, deger in anahtarlar:
        tek_durum = tek_anahtar_kota_durumu(anahtar_adi)
        if tek_durum.get("kota_doldu"):
            son_hata = {"anahtar": anahtar_adi, "neden": "gunluk kotasi dolu, siradaki anahtar denenecek"}
            continue

        izin, kullanilan = _tek_anahtar_kota_ayir(anahtar_adi)
        if not izin:
            son_hata = {"anahtar": anahtar_adi, "neden": "kota ayirma anda doldu, siradaki anahtar denenecek"}
            continue

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as c:
                r = await c.get(
                    f"{FLASHALPHA_BASE}/exposure/gex/{ticker}",
                    headers={"X-Api-Key": deger, "Accept": "application/json"},
                    params={"expiration": expiration} if expiration else None,
                )
        except Exception as e:
            son_hata = {"anahtar": anahtar_adi, "neden": f"{type(e).__name__}: {str(e)[:160]}"}
            continue

        if r.status_code == 200:
            try:
                veri = r.json()
            except Exception:
                raise HTTPException(status_code=502, detail={"hata": "FlashAlpha JSON cozulemedi", "govde": r.text[:300]})
            return {
                "ticker": ticker,
                "expiration": expiration,
                "kaynak": "FlashAlpha (lab.flashalpha.com/v1/exposure/gex)",
                "kullanilan_anahtar": anahtar_adi,
                "veri_tazeligi": "ucretsiz tier: ~15 dakika gecikmeli",
                "kota_durumu": kota_durumu(),
                "gex": veri,
            }

        if r.status_code in GECIS_KODLARI:
            # 403 iki farkli sebepten gelebilir: (a) BU ANAHTAR gecersiz/kotasi
            # bitmis -> siradaki anahtar cozer; (b) plan/tier kisitlamasi
            # (orn. ETF verisi Basic plan gerektirir) -> TUM anahtarlar ayni
            # ucretsiz tier'da oldugu icin hicbiri farkli sonuc vermez, boyle
            # bir hatada rotasyona devam etmek krediyi bosuna tuketir.
            govde_kucuk = r.text.lower()
            if r.status_code == 403 and ("tier_restricted" in govde_kucuk or "upgrade" in govde_kucuk or "plan" in govde_kucuk):
                raise HTTPException(
                    status_code=402,
                    detail={
                        "hata": "FlashAlpha plan/tier kisitlamasi (anahtar sorunu degil)",
                        "aciklama": (
                            "Bu ucretsiz tier'in TUMU ayni kisitlamaya tabi oldugundan "
                            "diger anahtarlar denenmedi (kredi tuketmemek icin)."
                        ),
                        "kullanilan_anahtar": anahtar_adi,
                        "govde": r.text[:300],
                        "kota_durumu": kota_durumu(),
                    },
                )
            son_hata = {"anahtar": anahtar_adi, "http_status": r.status_code, "neden": r.text[:160]}
            continue

        # 404/5xx gibi anahtar sorunu olmayan bir hata - direkt don, baska anahtar denemenin anlami yok
        raise HTTPException(
            status_code=502,
            detail={
                "hata": f"FlashAlpha HTTP {r.status_code}",
                "kullanilan_anahtar": anahtar_adi,
                "govde": r.text[:300],
                "kota_durumu": kota_durumu(),
            },
        )

    # Buraya gelindiyse: tum anahtarlar ya kotasi dolu ya da gecis kodu/hata verdi
    guncel_durum = kota_durumu()
    if guncel_durum.get("kota_doldu"):
        raise HTTPException(
            status_code=429,
            detail={
                "hata": "Tum FlashAlpha anahtarlarinin gunluk kotasi doldu",
                "mesaj": f"Bugun icin toplam {guncel_durum['toplam_gunluk_kota']} istek hakkinin tamami kullanildi. Yarin tekrar deneyin.",
                "kota_durumu": guncel_durum,
                "istek_yapilmadi": True,
            },
        )
    raise HTTPException(
        status_code=502,
        detail={
            "hata": "Tum FlashAlpha anahtarlari denendi, hicbiri basarili olmadi",
            "son_hata": son_hata,
            "kota_durumu": guncel_durum,
        },
    )


@app.get("/quota")
async def kota():
    """
    Tanimli TUM FlashAlpha anahtarlarinin gunluk kota durumu (toplu +
    anahtar bazinda kirilim). Hicbir sayaci ARTIRMAZ.
    """
    return {
        "servis": "gamma-exposure-service",
        "kaynak": "FlashAlpha ucretsiz tier (cok anahtarli rotasyon)",
        **kota_durumu(),
    }


# --- PARCA B: DIX-benzeri gosterge ------------------------------------------

METODOLOJI = {
    "gosterge_adi": "Dark Pool Katilim Endeksi (DPKE)",
    "resmi_dix_mi": False,
    "onemli_uyari": (
        "Bu RESMI DIX DEGILDIR. Orijinal DIX (SqueezeMetrics), dark pool'daki ALIM "
        "hacminin toplam dark pool hacmine oranidir ve islem bazinda alis/satis yonu "
        "atamasi (trade signing) gerektirir. FINRA'nin haftalik ATS Transparency verisi "
        "islem YONU ICERMEZ - yalnizca toplam hisse adedi ve islem sayisi verir. "
        "Bu nedenle gercek DIX bu veriden HESAPLANAMAZ. Asagidaki gosterge, elimizdeki "
        "veriyle kurulabilecek en yakin durust yaklasimdir ve farkli bir seyi olcer: "
        "alis/satis baskisini degil, HACMIN NEREDE GERCEKLESTIGINI (venue karmasi)."
    ),
    "ne_olcer": (
        "Borsa disi (off-exchange) hacim icinde ATS/dark pool havuzlarinin payi ve "
        "bu payin kendi gecmisine gore konumu."
    ),
    "formul": "DPKE = ATS_hacim / (ATS_hacim + ATS_disi_OTC_hacim) * 100",
    "payda_notu": (
        "FINRA'da ATS_W_SMBL (dark pool havuzlari) ve OTC_W_SMBL (ATS disi tezgahustu, "
        "yani broker ic eslestirmesi) IC ICE DEGIL, KARDES kategorilerdir. Bu yuzden "
        "ATS/OTC orani %100'u asabilir ve payda olarak yanlistir; dogru payda ikisinin "
        "TOPLAMIDIR. Ham ATS ve OTC hisse adetleri finra-darkpool-service'ten alinip "
        "oran BU SERVISTE yeniden hesaplanir."
    ),
    "baglam_metrikleri": (
        "Cari hafta degeri, son N haftalik pencere icinde yuzdelik dilim ve z-skoru "
        "ile birlikte verilir; boylece 'yuksek/dusuk' yargisi mutlak degil goreli olur."
    ),
    "veri_kaynagi": "finra-darkpool-service (port 8200) -> FINRA ATS Transparency (resmi, ucretsiz)",
    "veri_gecikmesi": "FINRA ATS verisi gecikmeli yayimlanir: NMS Tier 1 ~2 hafta, Tier 2 ~4 hafta.",
    "kullanim_uyarisi": (
        "DPKE'yi DIX yerine kullanmayin. Yuksek DPKE 'kurumsal alim' anlamina GELMEZ; "
        "yalnizca hacmin borsa disi kismi icinde ATS havuzlarina kaymis oldugunu gosterir."
    ),
}


def _yuzdelik_dilim(deger, seri):
    """deger'in seri icindeki yuzdelik dilimi (0-100)."""
    if not seri:
        return None
    altinda = sum(1 for x in seri if x < deger)
    esit = sum(1 for x in seri if x == deger)
    return round((altinda + 0.5 * esit) / len(seri) * 100, 1)


@app.get("/dix-like/{ticker}")
async def dix_benzeri(
    ticker: str,
    weeks: int = Query(12, ge=2, le=52, description="Baglam penceresi (hafta)"),
):
    """
    DIX-BENZERI gosterge - kendi finra-darkpool-service verimizden hesaplanir.
    RESMI DIX DEGILDIR; metodoloji yanitin icinde acikca verilir.
    """
    ticker = ticker.upper().strip()
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as c:
            gecmis = await c.get(f"{FINRA_DARKPOOL_URL}/darkpool/{ticker}/history", params={"weeks": weeks})
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={"hata": f"finra-darkpool-service'e ulasilamadi: {type(e).__name__}: {str(e)[:160]}",
                    "url": FINRA_DARKPOOL_URL},
        )
    if gecmis.status_code != 200:
        raise HTTPException(status_code=502, detail={"hata": f"finra-darkpool-service HTTP {gecmis.status_code}",
                                                     "govde": gecmis.text[:200]})

    seri_ham = (gecmis.json() or {}).get("seri", [])
    if not seri_ham:
        return {
            "ticker": ticker,
            "veri_var": False,
            "uyari": f"{ticker} icin FINRA ATS verisi bulunamadi (sembol yanlis ya da hic borsa disi islem yok).",
            "metodoloji": METODOLOJI,
        }

    seri = []
    for h in seri_ham:
        ats = h.get("ats_shares") or 0
        otc = h.get("otc_shares") or 0
        toplam = ats + otc
        if toplam <= 0:
            continue
        seri.append({
            "week_start_date": h.get("week_start_date"),
            "ats_shares": ats,
            "otc_disi_ats_shares": otc,
            "borsa_disi_toplam": toplam,
            "dpke_yuzde": round(ats / toplam * 100, 2),
        })

    if not seri:
        return {"ticker": ticker, "veri_var": False,
                "uyari": "Hacim verisi sifir; gosterge hesaplanamadi.", "metodoloji": METODOLOJI}

    seri.sort(key=lambda x: x["week_start_date"], reverse=True)
    cari = seri[0]
    degerler = [x["dpke_yuzde"] for x in seri]
    ortalama = sum(degerler) / len(degerler)
    varyans = sum((x - ortalama) ** 2 for x in degerler) / len(degerler)
    std = varyans ** 0.5
    z = round((cari["dpke_yuzde"] - ortalama) / std, 2) if std > 0 else None
    dilim = _yuzdelik_dilim(cari["dpke_yuzde"], degerler)

    if z is None:
        yorum = "Pencere icinde degiskenlik yok; goreli yargi uretilemedi."
    elif z >= 1:
        yorum = "Cari hafta, kendi gecmisine gore BELIRGIN YUKSEK dark pool katilimi."
    elif z <= -1:
        yorum = "Cari hafta, kendi gecmisine gore BELIRGIN DUSUK dark pool katilimi."
    else:
        yorum = "Cari hafta, kendi gecmisinin normal araliginda."

    return {
        "ticker": ticker,
        "veri_var": True,
        "gosterge_adi": METODOLOJI["gosterge_adi"],
        "resmi_dix_mi": False,
        "cari_hafta": {
            "week_start_date": cari["week_start_date"],
            "dpke_yuzde": cari["dpke_yuzde"],
            "ats_shares": cari["ats_shares"],
            "ats_disi_otc_shares": cari["otc_disi_ats_shares"],
            "borsa_disi_toplam_shares": cari["borsa_disi_toplam"],
        },
        "baglam": {
            "pencere_hafta": len(seri),
            "ortalama_dpke_yuzde": round(ortalama, 2),
            "std_sapma": round(std, 2),
            "z_skoru": z,
            "yuzdelik_dilim": dilim,
            "yorum": yorum,
        },
        "haftalik_seri": seri,
        "metodoloji": METODOLOJI,
    }


@app.get("/methodology")
async def metodoloji():
    """DIX-benzeri gostergenin tam metodolojisi ve sinirlari."""
    return METODOLOJI


# --- Saglik ------------------------------------------------------------------

@app.get("/health")
async def health():
    finra = {"erisilebilir": False}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{FINRA_DARKPOOL_URL}/health")
        finra = {"erisilebilir": r.status_code == 200, "http_status": r.status_code, "url": FINRA_DARKPOOL_URL}
    except Exception as e:
        finra = {"erisilebilir": False, "hata": f"{type(e).__name__}: {str(e)[:120]}", "url": FINRA_DARKPOOL_URL}

    return {
        "status": "ok",
        "service": "gamma-exposure-service",
        "redis": redis_durumu(),
        "parca_a_gex": {
            "kaynak": "FlashAlpha",
            "base_url": FLASHALPHA_BASE,
            "tanimli_anahtar_sayisi": len(_flashalpha_anahtarlari()),
            "tanimli_anahtar_adlari": [ad for ad, _ in _flashalpha_anahtarlari()],
            "eksik_anahtar": None if _flashalpha_anahtarlari() else "FLASHALPHA_API_KEY_1 (veya FLASHALPHA_API_KEY)",
            "kota": kota_durumu(),
        },
        "parca_b_dix_benzeri": {
            "kaynak": "finra-darkpool-service (dahili HTTP, yeni dis API yok)",
            "resmi_dix_degil": True,
            **finra,
        },
    }


# ===== DEX / VANNA MARUZIYETI (23.08.2026) =====
# MEVCUT /gex ve /dix-like UCLARINA DOKUNULMADI.
#
# KRITIK: Bu uc FlashAlpha'yi HIC CAGIRMAZ, dolayisiyla gunluk 25'lik kotadan
# HICBIR SEY TUKETMEZ. Zincir, zaten kurulu olan openbb-service'ten
# `yfinance` saglayicisiyla alinir (ucretsiz, anahtarsiz).
# Gerekce: FlashAlpha /gex ucretsiz planda 402 donuyor ve BASARISIZ CAGRI BILE
# kotadan dusuyor (olculdu: 25 -> 24); ayrica bu servis FlashAlpha yanitini
# hic ayristirmadigi icin kontrat bazli veri zaten elimizde yoktu.
import dex_vanna as _dv

OPENBB_TABAN = os.getenv("OPENBB_URL", "http://openbb:8000")
DEX_ONBELLEK_TTL = int(os.getenv("DEX_TTL", "900"))   # 15 dk


@app.get("/dex-vanna/{ticker}")
async def dex_vanna(
    ticker: str,
    min_acik_pozisyon: int = Query(0, ge=0, le=100000,
                                   description="Bu degerin altindaki OI'li kontratlar atlanir"),
):
    """Delta (DEX) ve Vanna maruziyeti — opsiyon zincirinden hesaplanir.

    FlashAlpha kotasi TUKETMEZ. Yon kodu URETMEZ (kalibre edilmemistir).
    """
    t = ticker.upper().strip()
    if not t.replace(".", "").replace("-", "").isalnum() or len(t) > 10:
        raise HTTPException(status_code=400, detail="gecersiz ticker bicimi")

    onbellek_anahtari = f"dexvanna:{t}:{min_acik_pozisyon}"
    try:
        r = _get_redis()
        onbellek = r.get(onbellek_anahtari)
        if onbellek:
            veri = json.loads(onbellek)
            veri["onbellekten"] = True
            return veri
    except Exception:
        pass

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            yanit = await client.get(
                f"{OPENBB_TABAN}/derivatives/options/chains/{t}")
    except Exception as e:
        raise HTTPException(status_code=502,
                            detail=f"openbb-service'e ulasilamadi: {type(e).__name__}")
    if yanit.status_code != 200:
        raise HTTPException(status_code=502,
                            detail=f"openbb-service HTTP {yanit.status_code}")
    zincir = yanit.json()
    if isinstance(zincir, dict) and "error" in zincir:
        raise HTTPException(status_code=502, detail="opsiyon zinciri alinamadi")
    if not isinstance(zincir, list) or not zincir:
        raise HTTPException(status_code=404, detail=f"{t}: opsiyon zinciri bos")

    spot = None
    for k in zincir:
        if k.get("underlying_price"):
            spot = float(k["underlying_price"])
            break
    if not spot:
        raise HTTPException(status_code=502, detail="dayanak fiyati bulunamadi")

    if min_acik_pozisyon:
        zincir = [k for k in zincir
                  if (k.get("open_interest") or 0) >= min_acik_pozisyon]

    sonuc = _dv.maruziyet_hesapla(zincir, spot)
    sonuc["ticker"] = t
    sonuc["kaynak"] = "openbb-service /derivatives/options/chains (yfinance) — UCRETSIZ"
    sonuc["flashalpha_kotasi_tuketildi"] = False
    sonuc["onbellekten"] = False
    try:
        _get_redis().setex(onbellek_anahtari, DEX_ONBELLEK_TTL,
                       json.dumps(sonuc, default=str))
    except Exception:
        pass
    return sonuc
