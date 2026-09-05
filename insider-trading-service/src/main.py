"""
ALPHAWISE — insider-trading-service (SEC Form 4)

Deney 1'in (23.08.2026) kabul edilen veri katmaninin uretim surumu.

NE YAPAR: Sirket ici yoneticilerin (CEO/CFO/yonetim kurulu) SEC'e bildirdigi
Form 4 islemlerini olgusal olarak raporlar. Sistemdeki en TAZE sahiplik
akisidir — olculen yasal gecikme medyan 2 is gunu (13F 45 gun, Kongre 30-45
gun, dark pool 21-27 gun).

NE YAPMAZ: Yon kodu veya yon olasiligi URETMEZ. Bu bir tercih degil, olculen
bir zorunluluktur: 25 mega-cap x 3,57 yilda yalnizca 32 acik piyasa alimi var
(29'u tek hissede). Kisit lambda_sifir.py'de KOD SEVIYESINDE uygulanir —
her yanit dogrula()'dan gecer, yon alani/ifadesi bulunursa yanit gonderilmez.

TURETME AYRISTIRMASI ZORUNLU: Olculen dagilimda kayitlarin yalnizca %28,4'u
acik piyasa islemidir; kalani Rule 16b-3 odulleri, opsiyon kullanimi, vergi
stopaji ve hediyeler. Ayrilmazsa "iceriden satis" sayisi ~3,5 kat sisirilir.
"""
import datetime as dt
import json
import os
import re
import time

import httpx
import redis
from fastapi import FastAPI, HTTPException

from .lambda_sifir import LAMBDA, LambdaSifirIhlali, dogrula
from .istatistik import yeterlilik, ASGARI_PENCERE_OLAY

OPENBB_URL = os.getenv("OPENBB_URL", "http://openbb:8000")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None

# Tasarim kisiti 1: ticker basina >= 6 saat TTL.
# Olculdu: soguk istek 26,3 sn / sicak 1,2 sn. OpenBB'nin kendi uyarisi:
# "This function is not intended for mass data collection."
ONBELLEK_TTL = int(os.getenv("INSIDER_TTL_SANIYE", str(6 * 3600)))
if ONBELLEK_TTL < 6 * 3600:
    raise RuntimeError(
        f"INSIDER_TTL_SANIYE={ONBELLEK_TTL} < 21600. Tasarim kisiti geregi "
        f"ticker basina en az 6 saat onbellek zorunludur (SEC yuk uyarisi).")

# Tasarim kisiti 2: SEC hiz limiti — saniyede 5 istek (SEC tavani 10'un %50'si),
# sec-edgar-13f-service ile ayni disiplin.
SANIYEDE_ISTEK = 5
_son_istekler: list[float] = []

# Deney 1'de olculen tam etiketler (OpenBB `sec` saglayicisi)
ACIK_PIYASA_SATIS = ("Open market or private sale of non-derivative or "
                     "derivative security")
ACIK_PIYASA_ALIM = ("Open market or private purchase of non-derivative or "
                    "derivative security")

app = FastAPI(title="ALPHAWISE - Insider Trading (SEC Form 4)")

try:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD,
                    decode_responses=True, socket_connect_timeout=3)
    r.ping()
    REDIS_HAZIR = True
except Exception:
    r = None
    REDIS_HAZIR = False

_sayac = {"onbellek_isabet": 0, "onbellek_iska": 0, "sec_istek": 0}


def _hiz_limiti():
    """SEC: saniyede en fazla SANIYEDE_ISTEK cagri."""
    global _son_istekler
    simdi = time.time()
    _son_istekler = [t for t in _son_istekler if simdi - t < 1.0]
    if len(_son_istekler) >= SANIYEDE_ISTEK:
        time.sleep(1.0 - (simdi - _son_istekler[0]))
    _son_istekler.append(time.time())


def _ham_getir(ticker: str, limit: int = 200):
    """OpenBB servisinden Form 4 kayitlarini getirir (onbellekli)."""
    anahtar = f"insider:form4:{ticker}:{limit}"
    if REDIS_HAZIR:
        try:
            onbellek = r.get(anahtar)
            if onbellek:
                _sayac["onbellek_isabet"] += 1
                return json.loads(onbellek), True
        except Exception:
            pass
    _sayac["onbellek_iska"] += 1
    _hiz_limiti()
    _sayac["sec_istek"] += 1
    try:
        resp = httpx.get(f"{OPENBB_URL}/equity/ownership/insider/{ticker}",
                         params={"limit": limit}, timeout=90.0)
        veri = resp.json()
    except Exception as e:
        raise HTTPException(502, f"OpenBB servisine ulasilamadi: {type(e).__name__}")
    if isinstance(veri, dict) and "error" in veri:
        # Yukari akis metni de yansitilmaz (ayni baypas gerekcesi);
        # ayrinti yalnizca sunucu logunda kalir.
        print(f"[insider] OpenBB hatasi: {veri['error']}", flush=True)
        raise HTTPException(502, "SEC/OpenBB kaynagindan veri alinamadi")
    if not isinstance(veri, list):
        raise HTTPException(502, "OpenBB beklenmeyen bicimde yanit dondu")
    if REDIS_HAZIR:
        try:
            r.setex(anahtar, ONBELLEK_TTL, json.dumps(veri, default=str))
        except Exception:
            pass
    return veri, False


# Frontend'in paylasilan tickerDogrula deseni nokta iceren girdileri
# ("A..") geciriyor; diger 6 kart bunu 200/bos ile yutuyor. Bu servis
# yukari (SEC) bozuk sembol gondermemek icin KENDI dogrulamasini yapar ve
# temiz 400 doner. Paylasilan desen BILEREK degistirilmedi — degistirilse
# mevcut alti kartin davranisi da degisirdi.
_TICKER_DESENI = re.compile(r"^[A-Z][A-Z0-9]{0,8}(?:[.-][A-Z0-9]{1,4})?$")


def _ticker_dogrula(ham: str) -> str:
    t = (ham or "").upper().strip()
    if not _TICKER_DESENI.fullmatch(t):
        # Ham girdi BILEREK yansitilmaz: hata mesajlari dogrula()'dan
        # gecmez, dolayisiyla yansitilan girdi λ=0 denetimini baypas
        # eden bir kanal olurdu (or. /insider/ALINIZ...).
        raise HTTPException(400, "gecersiz ticker bicimi")
    return t


def _tarih(d):
    if not d:
        return None
    return str(d)[:10]


def _normalize(kayit: dict) -> dict:
    """Tek bir Form 4 kaydini olgusal alanlara indirger.

    `acik_piyasa` ayrimi ZORUNLUDUR — odul/opsiyon/stopaj/hediye kayitlari
    acik piyasa islemi DEGILDIR ve ayrilmazsa sayimlar ~3,5 kat siser.
    """
    tur = kayit.get("transaction_type") or ""
    return {
        "islem_tarihi": _tarih(kayit.get("transaction_date")),
        "dosyalama_tarihi": _tarih(kayit.get("filing_date")),
        "kisi": kayit.get("owner_name"),
        "islem_turu_ham": tur,
        "acik_piyasa": tur in (ACIK_PIYASA_ALIM, ACIK_PIYASA_SATIS),
        "acik_piyasa_yonu": ("alim" if tur == ACIK_PIYASA_ALIM
                             else "satis" if tur == ACIK_PIYASA_SATIS else None),
        "adet": kayit.get("securities_transacted"),
        "islem_fiyati": kayit.get("transaction_price"),
    }


def _is_gunu_farki(a: dt.date, b: dt.date) -> int:
    if b < a:
        return -_is_gunu_farki(b, a)
    g, n = a, 0
    while g < b:
        g += dt.timedelta(days=1)
        if g.weekday() < 5:
            n += 1
    return n


@app.get("/healthz")
def healthz():
    """Dis bagimliligi OLMAYAN canlilik ucu (Docker healthcheck bunu kullanir).

    congress-trading'de ogrenilen ders: /health dis API cagirirsa 60 sn'lik
    healthcheck gunde ~1440 gereksiz dis istege donusur.
    """
    return dogrula({"status": "ok"})


@app.get("/health")
def health():
    toplam = _sayac["onbellek_isabet"] + _sayac["onbellek_iska"]
    yanit = {
        "service": "insider-trading (SEC Form 4)",
        "status": "ok",
        "redis": REDIS_HAZIR,
        "onbellek_ttl_saniye": ONBELLEK_TTL,
        "onbellek_isabet_orani_yuzde": (
            round(_sayac["onbellek_isabet"] / toplam * 100, 1) if toplam else None),
        "sayaclar": dict(_sayac),
        "lambda": LAMBDA,
        "yon_kodu_uretir": False,
    }
    return dogrula(yanit)


@app.get("/methodology")
def methodology():
    """ZORUNLU seffaflik ucu — ne olculdugu ve ne OLCULMEDIGI."""
    yanit = {
        "kaynak": "SEC EDGAR Form 4 (OpenBB `sec` saglayicisi) — ucretsiz, anahtarsiz",
        "olculen": [
            "Sirket ici yoneticilerin bildirdigi islemler (tarih, kisi, adet, fiyat)",
            "Acik piyasa islemi mi, yoksa odul/opsiyon/stopaj/hediye mi (ayristirilir)",
            "Yasal dosyalama gecikmesi (is gunu)",
        ],
        "OLCULMEYEN": [
            "Yon iddiasi — bu servis fiyatin nereye gidecegine dair HICBIR sey soylemez",
            "Kalibrasyon — bu evrende yapilamadi (asagiya bakiniz)",
        ],
        "yon_kodu_uretir": False,
        "kalibrasyon_gecerli": False,
        "lambda": LAMBDA,
        "lambda_neden_sifir": (
            "Deney 1 (23.08.2026) olctu: 25 mega-cap x 3,57 yilda yalnizca 32 "
            "acik piyasa alimi var ve bunun 29'u tek bir hissede toplaniyor; "
            "21 hissede hic yok. Ornek-disi test bolumu ~12 gozlem olurdu, "
            "God Mode esigi ise 1.000+ gozlem istiyor. Yani yon kalibrasyonu "
            "bu evrende matematiksel olarak mumkun degildir."
        ),
        "kalibrasyon_yolu": (
            "Evren qlib-service/data_prep/us_stock_universe.txt olcegine "
            "(6.783 hisse) cikarilir; kucuk/orta olcekli sirketlerde iceriden "
            "alim mega-cap'lere gore cok daha siktir. Ardindan God Mode "
            "disiplininde (zaman bolmeli, taban oranli, Brier >= +%2) test "
            "edilir. Gecerse lambda yukseltilir, gecmezse 0'da kalir."
        ),
        "olculen_veri_kalitesi": {
            "sepet": "25 mega-cap", "toplam_kayit": 1869,
            "tarih_araligi": "2023-01-25 .. 2026-08-20",
            "yasal_gecikme_is_gunu_medyan": 2,
            "yasal_gecikme_is_gunu_p95": 3,
            "kural_ihlali_orani_yuzde": 9.7,
            "kritik_alan_eksikligi_yuzde": 5.1,
            "acik_piyasa_islem_payi_yuzde": 28.4,
            "maliyet_usd": 0,
        },
        "maa_decide_baglantisi": "YOK — yalnizca baglam/gosterge katmanidir",
    }
    return dogrula(yanit)


@app.get("/quota")
def quota():
    simdi = time.time()
    son_saniye = len([t for t in _son_istekler if simdi - t < 1.0])
    return dogrula({
        "saniyede_izin": SANIYEDE_ISTEK,
        "son_saniyede_kullanilan": son_saniye,
        "sec_tavani": 10,
        "not": "SEC tavaninin %50'si hedeflenir (sec-edgar-13f ile ayni disiplin)",
        "toplam_sec_istegi": _sayac["sec_istek"],
    })


@app.get("/insider/{ticker}")
def insider(ticker: str, limit: int = 50):
    ticker = _ticker_dogrula(ticker)
    ham, isabet = _ham_getir(ticker, limit=200)
    kayitlar = [_normalize(k) for k in ham]
    kayitlar.sort(key=lambda k: (k["dosyalama_tarihi"] or ""), reverse=True)
    acik = [k for k in kayitlar if k["acik_piyasa"]]
    yanit = {
        "ticker": ticker,
        "kayit_sayisi": len(kayitlar),
        "acik_piyasa_kayit_sayisi": len(acik),
        "acik_piyasa_payi_yuzde": (round(len(acik) / len(kayitlar) * 100, 1)
                                   if kayitlar else None),
        "onbellekten": isabet,
        "kayitlar": kayitlar[:limit],
        "not": ("Odul/opsiyon/stopaj/hediye kayitlari acik piyasa islemi "
                "DEGILDIR ve 'acik_piyasa' alaniyla ayristirilmistir; "
                "ayristirilmazsa sayim yaklasik 3,5 kat sisirilir."),
        "yon_kodu_uretir": False,
    }
    return dogrula(yanit)


@app.get("/insider/{ticker}/ozet")
def insider_ozet(ticker: str):
    ticker = _ticker_dogrula(ticker)
    ham, isabet = _ham_getir(ticker, limit=200)
    kayitlar = [_normalize(k) for k in ham]

    bugun = dt.date.today()
    pencereler = {}
    for gun in (90, 180):
        esik = bugun - dt.timedelta(days=gun)
        dilim = [k for k in kayitlar
                 if k["islem_tarihi"] and k["islem_tarihi"] >= esik.isoformat()
                 and k["acik_piyasa"]]
        alim = [k for k in dilim if k["acik_piyasa_yonu"] == "alim"]
        satis = [k for k in dilim if k["acik_piyasa_yonu"] == "satis"]
        pencereler[f"son_{gun}_gun"] = {
            "acik_piyasa_alim_islem_sayisi": len(alim),
            "acik_piyasa_satis_islem_sayisi": len(satis),
            "net_islem_farki": len(alim) - len(satis),
            "alim_bildiren_kisi_sayisi": len({k["kisi"] for k in alim if k["kisi"]}),
            "satis_bildiren_kisi_sayisi": len({k["kisi"] for k in satis if k["kisi"]}),
        }

    gecikmeler = []
    for k in kayitlar:
        if k["islem_tarihi"] and k["dosyalama_tarihi"]:
            try:
                gecikmeler.append(_is_gunu_farki(
                    dt.date.fromisoformat(k["islem_tarihi"]),
                    dt.date.fromisoformat(k["dosyalama_tarihi"])))
            except ValueError:
                pass
    gecikmeler.sort()

    yanit = {
        "ticker": ticker,
        "onbellekten": isabet,
        "toplam_kayit": len(kayitlar),
        "pencereler": pencereler,
        "en_yeni_dosyalama": max((k["dosyalama_tarihi"] for k in kayitlar
                                  if k["dosyalama_tarihi"]), default=None),
        "yasal_gecikme_is_gunu_medyan": (gecikmeler[len(gecikmeler) // 2]
                                         if gecikmeler else None),
        "yorum": ("Bu sayilar olgusal bildirimlerdir. Az sayida acik piyasa "
                  "alimi gozlenmesi olagandir; bu evrende alim sikligi cok "
                  "dusuktur (3,57 yilda 32 kayit) ve bu nedenle herhangi bir "
                  "yon cikarimi yapilamaz."),
        "yon_kodu_uretir": False,
        "kalibrasyon_gecerli": False,
    }
    return dogrula(yanit)

@app.get("/insider/{ticker}/yon")
def insider_yon(ticker: str, gun: int = 90):
    """Acik piyasa alim/satim yon ayrimi + ISTATISTIKSEL YETERLILIK (Madde 25).

    /ozet ucu alim ve satim sayilarini zaten bildiriyordu ve "yon cikarimi
    yapilamaz" diyordu; ama bunu OLCMUYORDU. Cumle bir YARGIYDI, sayi degil.
    Bu uc, gozlenen farkin sansla aciklanip aciklanamadigini HESAPLAR.

    Karsilastirma "alim ve satim esit olasilikli" varsayimina DAYANMAZ (bu
    evrende yanlis olurdu; acik piyasa alimi cok nadir). Bunun yerine pencere,
    SIRKETIN KENDI GECMISININ GERI KALANIYLA karsilastirilir.

    Birincil olcum birimi KISIDIR: ayni yoneticinin bes islemi bes bagimsiz
    isaret degildir. Islem duzeyi ikincil olarak ayrica bildirilir.
    """
    ticker = _ticker_dogrula(ticker)
    if gun < 7 or gun > 3650:
        return {"ticker": ticker, "hata": "gun 7 ile 3650 arasinda olmali"}
    ham, isabet = _ham_getir(ticker, limit=200)
    kayitlar = [_normalize(k) for k in ham]
    acik = [k for k in kayitlar if k["acik_piyasa"] and k["islem_tarihi"]]

    esik = (dt.date.today() - dt.timedelta(days=gun)).isoformat()
    pencere = [k for k in acik if k["islem_tarihi"] >= esik]
    gecmis = [k for k in acik if k["islem_tarihi"] < esik]

    def kisi_sayimi(dilim, yon):
        return len({k["kisi"] for k in dilim
                    if k["acik_piyasa_yonu"] == yon and k["kisi"]})

    def islem_sayimi(dilim, yon):
        return sum(1 for k in dilim if k["acik_piyasa_yonu"] == yon)

    kisi = yeterlilik(kisi_sayimi(pencere, "alim"), kisi_sayimi(pencere, "satis"),
                      kisi_sayimi(gecmis, "alim"), kisi_sayimi(gecmis, "satis"))
    islem = yeterlilik(islem_sayimi(pencere, "alim"), islem_sayimi(pencere, "satis"),
                       islem_sayimi(gecmis, "alim"), islem_sayimi(gecmis, "satis"))

    tarihler = sorted(k["islem_tarihi"] for k in acik)
    if tarihler:
        try:
            kapsam_gun = (dt.date.fromisoformat(tarihler[-1])
                          - dt.date.fromisoformat(tarihler[0])).days
        except ValueError:
            kapsam_gun = None
    else:
        kapsam_gun = None

    yanit = {
        "ticker": ticker,
        "onbellekten": isabet,
        "pencere_gun": gun,
        "toplam_acik_piyasa_kaydi": len(acik),
        # Veri araligini GIZLEMEK yerine bildiriyoruz: "yetersiz veri"
        # yanitinin nedeni cogu zaman burada gorulur.
        "veri_araligi": {"en_eski": tarihler[0] if tarihler else None,
                         "en_yeni": tarihler[-1] if tarihler else None,
                         "kapsam_gun": kapsam_gun},
        "kaynak_siniri": ("OLCULDU (06.09.2026): yukari akis kaynagi limit "
                          "parametresinden BAGIMSIZ olarak yaklasik 3,7 aylik "
                          "gecmis donduruyor (WDC icin limit=200/500/1000 "
                          "denendi, ucunde de 257 kayit ve ayni tarih araligi). "
                          "Bu nedenle pencere, kapsamin kabaca ucte birinden "
                          "buyuk secilirse karsilastirma temeli olusmaz."),
        "kisi_duzeyi": kisi,
        "islem_duzeyi": islem,
        "birincil_olcum": "kisi_duzeyi",
        "yontem": ("Fisher kesin testi (iki yonlu). Pencere, sirketin kendi "
                   "gecmisinin geri kalaniyla karsilastirilir; 'alim ve satim "
                   "esit olasilikli' varsayimi KULLANILMAZ. Ki-kare yerine "
                   "Fisher secildi cunku bu evrende hucre sayilari kucuktur "
                   "ve ki-kare yaklasimi orada guvenilmezdir."),
        "yon_kodu_uretir": False,
        "not": ("Bu uc bir yon KODU uretmez. Yalnizca gozlenen farkin sansla "
                "aciklanip aciklanamadigini soyler; 'ayirt ediliyor' sonucu "
                "yonun gelecekte surecegi anlamina GELMEZ."),
    }
    return dogrula(yanit)

