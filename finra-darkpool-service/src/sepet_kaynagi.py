"""
ALPHAWISE - Equibles tamamlayici istemci: dogrulanmis endeks sepeti +
CFTC COT + CBOE put/call orani (madde 52'nin kalan kapsami).

NEDEN GEREKLI (16.09.2026 canli olculdu):
1) dix.py'nin sepeti DISARIDAN alma zorunlulugu (bkz. dix.py:40-41 -
   "Bu depoda dogrulanmis bir S&P 500 listesi YOK") /dix ucunu her
   cagirana "gecerli bir sepeti sen bul" yukunu birakiyordu. Equibles
   /v1/indexes/{index} CANLI dogrulandi: sp-500 icin 503 bilesen,
   agirlik (weight/fundValueUsd) ve rank ile geliyor, kaynagi ACIKCA
   soyluyor ("iShares Core S&P 500 ETF (IVV) daily basket").
2) CFTC COT ve CBOE put/call orani bu serviste HIC YOKTU. Ikisi de
   SEMBOLDEN BAGIMSIZ (tek cagriyla tum piyasayi kapsar) - madde 52'nin
   notundaki "dusuk istekli" nitelemesiyle tutarli.

PAYLASILAN KOTA (kritik): EQUIBLES_API_KEY, sec-edgar-13f-service VE
congress-trading-service ile AYNI hesaba/kotaya (gunluk 100 istek)
baglanir. Bu servis UCUNCU tuketicidir. Redis anahtarlari (equibles:
gunluk:<UTC-tarih>, equibles:sunucu_kalan) o iki serviste kullanilan
ISIMLERLE BIREBIR AYNI - tek amac uc servisin TEK bir paylasilan
sayaci gormesidir (bkz. madde 58 NOT kaydi: ucu de ayni alphawise-net +
ayni alphawise-redis konteynerine, ayni db=0'a baglaniyor, dogrulandi).

SENKRON REDIS: bu servisin mevcut deseni (finra.py::_get_redis()) sync
redis-py kullanir; ayni istemci burada da kullanilir - yeni bir
bagimlilik/desen EKLENMEZ.
"""
import datetime
import os

import httpx

from .finra import _get_redis

EQUIBLES_BASE = os.getenv("EQUIBLES_BASE_URL", "https://api.equibles.com/v1")
EQUIBLES_TIMEOUT = float(os.getenv("EQUIBLES_TIMEOUT", "15"))
EQUIBLES_GUNLUK_LIMIT = int(os.getenv("EQUIBLES_GUNLUK_LIMIT", "100"))
EQUIBLES_GUVENLIK_PAYI = int(os.getenv("EQUIBLES_GUVENLIK_PAYI", "5"))

SEPET_CACHE_TTL = 26 * 3600   # gunde bir yenilenir, 26 saat pay birakir
CFTC_CACHE_TTL = 24 * 3600    # COT raporu HAFTALIK yayimlanir, gunluk yeter
PUTCALL_CACHE_TTL = 12 * 3600

GECERLI_PUTCALL_TIPLERI = ("Total", "Equity", "Index", "Vix", "Etp")


def _kota_anahtari() -> str:
    gun = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    return f"equibles:gunluk:{gun}"


def kota_durumu() -> dict:
    """sec-edgar-13f-service/src/equibles_client.py::kota_durumu ile AYNI
    mantik, sync redis'e uyarlanmis (bu servisin mevcut deseni)."""
    try:
        r = _get_redis()
        kullanilan = int(r.get(_kota_anahtari()) or 0)
        sunucu_kalan_ham = r.get("equibles:sunucu_kalan")
        sunucu_kalan = int(sunucu_kalan_ham) if sunucu_kalan_ham is not None else None
    except Exception:
        kullanilan = 0
        sunucu_kalan = None

    yerel_izinli = kullanilan < (EQUIBLES_GUNLUK_LIMIT - EQUIBLES_GUVENLIK_PAYI)
    sunucu_izinli = sunucu_kalan is None or sunucu_kalan > EQUIBLES_GUVENLIK_PAYI
    return {
        "limit": EQUIBLES_GUNLUK_LIMIT,
        "guvenlik_payi": EQUIBLES_GUVENLIK_PAYI,
        "yerel_sayac_kullanilan": kullanilan,
        "sunucu_bildirdigi_kalan": sunucu_kalan,
        "yerelden_izinli_mi": yerel_izinli and sunucu_izinli,
    }


def _kota_artir(sunucu_kalan=None) -> None:
    try:
        r = _get_redis()
        anahtar = _kota_anahtari()
        p = r.pipeline()
        p.incr(anahtar)
        p.expire(anahtar, 48 * 3600)
        if sunucu_kalan is not None:
            p.set("equibles:sunucu_kalan", sunucu_kalan, ex=6 * 3600)
        p.execute()
    except Exception:
        pass


def _cache_oku(anahtar: str):
    try:
        r = _get_redis()
        ham = r.get(anahtar)
        if ham:
            import json
            return json.loads(ham)
    except Exception:
        pass
    return None


def _cache_yaz(anahtar: str, deger: dict, ttl: int) -> None:
    try:
        import json
        _get_redis().setex(anahtar, ttl, json.dumps(deger))
    except Exception:
        pass


def _equibles_get(yol: str, params: dict | None = None):
    """Tek cagiri noktasi: kota kontrolu + istek + kota artirimi.
    Basarili -> (yanit_json, None). Basarisiz/kota asimi -> (None, hata)."""
    key = os.getenv("EQUIBLES_API_KEY")
    if not key:
        return None, {"kaynak": "equibles", "neden": "EQUIBLES_API_KEY tanimli degil"}

    kota = kota_durumu()
    if not kota["yerelden_izinli_mi"]:
        return None, {
            "kaynak": "equibles",
            "neden": (f"gunluk PAYLASILAN guvenlik payi asildi (yerel sayac="
                      f"{kota['yerel_sayac_kullanilan']}/{EQUIBLES_GUNLUK_LIMIT}) "
                      "- istek ATILMADI"),
            "kota_asimi": True,
        }

    try:
        with httpx.Client(timeout=EQUIBLES_TIMEOUT) as c:
            r = c.get(f"{EQUIBLES_BASE}{yol}", params=params or {},
                     headers={"Authorization": f"Bearer {key}"})
        _kota_artir(sunucu_kalan=r.headers.get("X-RateLimit-Remaining"))
        if r.status_code == 200:
            return r.json(), None
        if r.status_code == 429:
            return None, {"kaynak": "equibles", "http_status": 429,
                          "neden": "sunucu gunluk limiti asildi"}
        return None, {"kaynak": "equibles", "http_status": r.status_code,
                      "neden": r.text[:160]}
    except Exception as e:
        return None, {"kaynak": "equibles", "neden": f"{type(e).__name__}: {str(e)[:120]}"}


def endeks_sepeti_cek(index: str = "sp-500", azami_sayfa: int = 2) -> tuple:
    """Dogrulanmis endeks bilesen listesi - GUNDE BIR yenilenir (Redis'te
    onbelleklenir). isLinked=false ya da bos ticker'lar sepetten CIKARILIR
    (DIX hesabı tradeable sembol ister) - kac tanesinin cikarildigi
    ACIKCA raporlanir, sessizce yutulmaz.

    azami_sayfa: 500'luk sayfalarla en fazla kac istek atilsin (sp-500 icin
    503 bilesen -> 2 sayfa yeterli). Guvenlik tavani - bozuk bir hasMore
    dongu uretmesin.
    """
    gun = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    onbellek_anahtari = f"equibles:endeks:{index}:{gun}"
    onbellek = _cache_oku(onbellek_anahtari)
    if onbellek is not None:
        return onbellek, None

    tum_satirlar = []
    meta_ilk = None
    offset = 0
    for _ in range(azami_sayfa):
        yanit, hata = _equibles_get(f"/indexes/{index}", {"limit": 500, "offset": offset})
        if hata:
            return None, hata
        if meta_ilk is None:
            meta_ilk = {"slug": yanit.get("slug"), "name": yanit.get("name"),
                       "asOfDate": yanit.get("asOfDate"), "source": yanit.get("source"),
                       "constituentCount": yanit.get("constituentCount")}
        satirlar = yanit.get("data") or []
        tum_satirlar.extend(satirlar)
        meta = yanit.get("meta") or {}
        if not meta.get("hasMore"):
            break
        offset += meta.get("count", len(satirlar)) or 500

    baglanmamis = [s for s in tum_satirlar if not s.get("isLinked") or not s.get("ticker")]
    gecerli = [s for s in tum_satirlar if s.get("isLinked") and s.get("ticker")]

    sonuc = {
        **(meta_ilk or {}),
        "sepet": [s["ticker"].upper() for s in gecerli],
        "agirliklar": {s["ticker"].upper(): s.get("weight") for s in gecerli},
        "toplam_cekilen": len(tum_satirlar),
        "kullanilabilir": len(gecerli),
        "baglanamayan_cikarildi": len(baglanmamis),
        "kaynak": "Equibles (dogrulanmis endeks bileseni, gunde bir yenilenir)",
    }
    _cache_yaz(onbellek_anahtari, sonuc, SEPET_CACHE_TTL)
    return sonuc, None


def cftc_cot_cek(kategori: str | None = None) -> tuple:
    """Haftalik COT pozisyon ozeti - SEMBOLDEN BAGIMSIZ, tum piyasayi tek
    cagriyla kapsar. Gunluk onbelleklenir (rapor zaten haftalik gecikmeli)."""
    gun = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    onbellek_anahtari = f"equibles:cftc:latest:{kategori or 'tumu'}:{gun}"
    onbellek = _cache_oku(onbellek_anahtari)
    if onbellek is not None:
        return onbellek, None

    params = {"category": kategori} if kategori else {}
    yanit, hata = _equibles_get("/cftc/positions/latest", params)
    if hata:
        return None, hata

    satirlar = yanit.get("data") or []
    sonuc = {
        "kategori": kategori or "tumu",
        "kontrat_sayisi": len(satirlar),
        "pozisyonlar": [
            {"piyasa_kodu": s.get("marketCode"), "piyasa_adi": s.get("marketName"),
             "kategori": s.get("category"), "rapor_tarihi": s.get("reportDate"),
             "acik_pozisyon": s.get("openInterest"),
             "ticari_net": s.get("commNet"), "ticari_disi_net": s.get("nonCommNet")}
            for s in satirlar
        ],
        "kaynak": "Equibles (CFTC haftalik COT, gunluk onbelleklenir)",
    }
    _cache_yaz(onbellek_anahtari, sonuc, CFTC_CACHE_TTL)
    return sonuc, None


def putcall_orani_cek(tip: str = "Total", limit: int = 5) -> tuple:
    """CBOE put/call orani gecmisi - SEMBOLDEN BAGIMSIZ."""
    if tip not in GECERLI_PUTCALL_TIPLERI:
        return None, {"kaynak": "yerel", "neden": (
            f"gecersiz tip {tip!r}; gecerli degerler: {GECERLI_PUTCALL_TIPLERI}")}

    gun = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    onbellek_anahtari = f"equibles:putcall:{tip}:{limit}:{gun}"
    onbellek = _cache_oku(onbellek_anahtari)
    if onbellek is not None:
        return onbellek, None

    yanit, hata = _equibles_get("/market/put-call-ratios", {"type": tip, "limit": limit})
    if hata:
        return None, hata

    satirlar = yanit.get("data") or []
    sonuc = {
        "tip": tip,
        "gunluk_seri": [
            {"tarih": s.get("date"), "put_hacmi": s.get("putVolume"),
             "call_hacmi": s.get("callVolume"), "toplam_hacim": s.get("totalVolume"),
             "put_call_orani": s.get("putCallRatio")}
            for s in satirlar
        ],
        "kaynak": "Equibles (CBOE put/call orani, 12 saatte bir onbelleklenir)",
    }
    _cache_yaz(onbellek_anahtari, sonuc, PUTCALL_CACHE_TTL)
    return sonuc, None
