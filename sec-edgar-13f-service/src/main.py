"""
ALPHAWISE - SEC EDGAR 13F Service

SEC EDGAR'in resmi acik verisinden (data.sec.gov + Archives) dogrudan
13F kurumsal pozisyon verisi uretir. HICBIR API ANAHTARI GEREKTIRMEZ,
hicbir ucretli saglayiciya bagimli degildir.

KAPSAM SINIRI: Bu servis institution-filter-service'in (port 8190)
YERINI ALMAZ ve ona DOKUNMAZ. Ikisi bagimsiz calisir; hangisinin ne
zaman kullanilacagina cagiran taraf (God Mode) karar verir.

DIL KURALI: Bu servis yalnizca OLCULEN veriyi raporlar. Yon tahmini,
oneri ya da emir kipi URETMEZ — 13F verisi gecmis bir donemin
fotografidir, gelecek iddiasi tasimaz.
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, Query

from . import cik_evreni, ciks, cusips
from .rate_limiter import HizSinirlayici, VARSAYILAN_HIZ
from .sec_client import SecIstemci, kullanici_ajani

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
# httpx INFO seviyesinde tam URL loglar. Burada anahtar yok ama
# gurultuyu kesmek ve ileride bir parametre eklenirse sizmamasi icin sessiz.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("sec-edgar-13f")

ONBELLEK_TTL = int(os.getenv("ONBELLEK_TTL_SANIYE", str(7 * 24 * 3600)))  # 7 gun
ONEK = "sec13f:"  # isim alani — diger servislerle carpismaz


def _redis_baglan():
    """Kardes servislerle (gamma-exposure vb.) ayni baglanti deseni."""
    return aioredis.Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        password=os.getenv("REDIS_PASSWORD") or None,
        db=int(os.getenv("REDIS_DB", "0")),
        decode_responses=False,
        socket_connect_timeout=3,
        socket_timeout=5,
    )

_redis = None
_sinirlayici: HizSinirlayici = None
_istemci: SecIstemci = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redis, _sinirlayici, _istemci
    try:
        _redis = _redis_baglan()
        await _redis.ping()
        logger.info("Redis baglandi: jeton kovasi PAYLASIMLI (IP bazli SEC siniriyla uyumlu)")
    except Exception as e:
        _redis = None
        logger.warning(
            "Redis kullanilamiyor (%s) — jeton kovasi surec-ici yedege dusuyor.",
            type(e).__name__,
        )

    hiz = float(os.getenv("SEC_ISTEK_HIZI", str(VARSAYILAN_HIZ)))
    _sinirlayici = HizSinirlayici(_redis, hiz=hiz, anahtar=ONEK + "ratelimit:sec-edgar")
    _istemci = SecIstemci(_sinirlayici)
    logger.info("SEC User-Agent: %s | hiz: %s istek/sn (SEC tavani 10)",
                kullanici_ajani(), hiz)

    # Kurum evrenini arka planda hazirla. BLOKLAMAZ: indirme basarisiz
    # olsa bile servis ayaga kalkar ve elle kuratorlenmis harita ile
    # calismaya devam eder (fail-open). Evren yalnizca EK kapsamdir.
    async def _evreni_hazirla():
        try:
            sonuc = await cik_evreni.indeksi_hazirla(
                _sinirlayici, {"User-Agent": kullanici_ajani(), "Accept-Encoding": "gzip, deflate"}
            )
            logger.info("13F dosyalayici indeksi hazir: %s", sonuc)
        except Exception as e:
            logger.warning(
                "13F indeksi olusturulamadi (%s) — servis elle kuratorlenmis "
                "harita ile calismaya devam ediyor.", type(e).__name__,
            )

    _gorev = asyncio.create_task(_evreni_hazirla())
    yield
    _gorev.cancel()
    if _redis is not None:
        await _redis.aclose()


app = FastAPI(
    title="ALPHAWISE - SEC EDGAR 13F Service",
    description=(
        "SEC EDGAR resmi acik verisinden 13F kurumsal pozisyonlari. "
        "API anahtari gerektirmez. institution-filter-service'ten bagimsizdir."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------- onbellek

async def _onbellek_al(anahtar: str):
    if _redis is None:
        return None
    try:
        import json
        ham = await _redis.get(ONEK + anahtar)
        return json.loads(ham) if ham else None
    except Exception:
        return None


async def _onbellek_yaz(anahtar: str, deger):
    if _redis is None:
        return
    try:
        import json
        await _redis.setex(ONEK + anahtar, ONBELLEK_TTL,
                           json.dumps(deger, ensure_ascii=False))
    except Exception as e:
        logger.warning("Onbellek yazilamadi (%s)", type(e).__name__)


async def _kurum_pozisyonlari(cik: str, donem_limit: int = 1) -> dict:
    """
    Bir kurumun EN SON 13F bilgi tablosunu (onbellekli) getirir.
    """
    ob_anahtar = f"kurum:{cik}:son"
    onbellek = await _onbellek_al(ob_anahtar)
    if onbellek:
        onbellek["onbellekten"] = True
        return onbellek

    liste = await _istemci.onüc_f_dosyalari(cik, limit=donem_limit)
    if not liste["dosyalar"]:
        return {"basarili": False,
                "neden": f"CIK {cik} icin 13F-HR dosyasi bulunamadi",
                "kurum_adi": liste.get("kurum_adi")}

    d = liste["dosyalar"][0]
    tablo = await _istemci.bilgi_tablosu_url(cik, d["accession"])
    if not tablo.get("bulundu"):
        return {"basarili": False, "neden": tablo.get("neden"),
                "kurum_adi": liste.get("kurum_adi")}

    ayr = await _istemci.bilgi_tablosu_ayristir(tablo["url"], donem=d["donem"])

    sonuc = {
        "basarili": True,
        "cik": liste["cik"],
        "kurum_adi": liste["kurum_adi"],
        "donem": d["donem"],
        "dosyalama_tarihi": d["dosyalama_tarihi"],
        "accession": d["accession"],
        "form": d["form"],
        "bilgi_tablosu": {"dosya_adi": tablo["dosya_adi"],
                          "boyut_bayt": tablo["boyut_bayt"]},
        "satir_sayisi": ayr["satir_sayisi"],
        "tekil_cusip": ayr["tekil_cusip"],
        "deger_birimi": ayr["deger_birimi"],
        "kaynak_birim": ayr["kaynak_birim"],
        "pozisyonlar": ayr["pozisyonlar"],
        "isim_indeksi": ayr["isim_indeksi"],
        "onbellekten": False,
    }
    await _onbellek_yaz(ob_anahtar, sonuc)
    return sonuc


def _pozisyon_kaydi(cusip: str, p: dict, meta: dict, cozum: dict) -> dict:
    return {
        "kurum": meta["kurum_adi"],
        "kurum_cik": meta["cik"],
        "donem": meta["donem"],
        "dosyalama_tarihi": meta["dosyalama_tarihi"],
        "accession": meta["accession"],
        "cusip": cusip,
        "cusip_kaynagi": cozum.get("kaynak"),
        "cusip_dogrulandi": cozum.get("dogrulandi", False),
        "ihracci_adi": p.get("isim"),
        "sinif": p.get("sinif"),
        "hisse_pozisyonu": {
            "deger_usd": p["hisse_deger_usd"],
            "adet": p["hisse_adet"],
            "dosyadaki_satir_sayisi": p["hisse_satir"],
            "not": ("Ayni CUSIP birden cok satirda (otherManager kirilimi) "
                    "gecebilir; buradaki deger CUSIP bazinda TOPLANMISTIR."),
        },
        "turev_pozisyonu": {
            "call_deger_usd": p["turev_call_usd"],
            "put_deger_usd": p["turev_put_usd"],
            "satir_sayisi": p["turev_satir"],
            "not": ("putCall alani dolu satirlar opsiyondur; hisse "
                    "pozisyonuna DAHIL EDILMEMISTIR."),
        },
        "deger_birimi": meta["deger_birimi"],
    }


# ---------------------------------------------------------------- endpoints

@app.get("/health")
async def health():
    redis_ok = False
    if _redis is not None:
        try:
            await _redis.ping()
            redis_ok = True
        except Exception:
            redis_ok = False

    return {
        "status": "ok",
        "service": "sec-edgar-13f-service",
        "veri_kaynagi": {
            "submissions": "https://data.sec.gov/submissions/CIK##########.json",
            "arsiv": "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/",
            "api_anahtari_gerekli": False,
            "ucret": "yok (SEC resmi acik veri)",
        },
        "sec_user_agent": kullanici_ajani(),
        "hiz_sinirlayici": _sinirlayici.durum() if _sinirlayici else None,
        "redis": {"connected": redis_ok, "isim_alani": ONEK,
                  "onbellek_ttl_saniye": ONBELLEK_TTL},
        "kurum_evreni": {
            **cik_evreni.dosya_durumu(),
            "kuratorlenmis_kurum": len(ciks.tum_kurumlar()),
            "not": ("Elle kuratorlenmis harita otorite; bulunamayan kurumlar "
                    "SEC'in tam cik-lookup-data.txt evreninde aranir ve her "
                    "aday 13F-HR dosyaladigi dogrulanarak dondurulur."),
        },
        "bagimsizlik_notu": ("institution-filter-service (8190) ile hicbir "
                             "kod/veri bagimliligi yoktur; CIK listesi kendi "
                             "kopyasidir."),
    }


@app.get("/methodology")
async def methodology():
    return {
        "zincir": [
            "1) data.sec.gov/submissions/CIK##########.json -> 13F-HR dosyalari",
            "2) Archives/.../index.json -> bilgi tablosu XML'i (adi SABIT DEGIL)",
            "3) XML ayristirma -> CUSIP bazinda TOPLAMA",
        ],
        "bilinen_tuzaklar": {
            "coklu_satir": ("Ayni CUSIP otherManager kirilimiyla birden cok "
                            "satirda gecer; toplanmazsa pozisyon eksik gorunur."),
            "turev_karisimi": ("putCall dolu satirlar opsiyondur; hisseyle "
                               "toplanirsa deger sisirilir."),
            "deger_birimi": ("2023 oncesi <value> BIN USD, sonrasi TAM USD. "
                             "Normalize edilmezse 1000 kat hata olur."),
            "dosya_adi": ("Bilgi tablosu adi kuruma gore degisir "
                          "(form13fInfoTable.xml / 56757.xml); tahmin edilemez."),
            "blackrock_ikili_kayit": ("CIK 1364742 'BlackRock Finance' 2024'te "
                                      "durmustur; guncel olan 2012383."),
        },
        "hiz_siniri": _sinirlayici.durum() if _sinirlayici else None,
        "cusip_cozumleme": {
            "birincil": "dogrulanmis harita (gercek 13F tablosundan cikarildi)",
            "yedek": "isim eslestirme (sonuc dogrulandi=False bayragiyla doner)",
            "dogrulanmis_ticker_sayisi": len(cusips.DOGRULANMIS),
        },
        "kurum_sayisi": len(ciks.tum_kurumlar()),
        "dil_kurali": ("Bu servis yalnizca olculen gecmis veriyi raporlar; "
                       "yon tahmini veya oneri uretmez."),
    }


@app.get("/position/{ticker}")
async def position(
    ticker: str,
    institution: str = Query(..., description="Kurum adi (orn. blackrock, vanguard)"),
):
    """Belirli bir kurumun belirli bir hissedeki 13F pozisyonu."""
    tk = ticker.upper().strip()

    # 1) ONCE elle kuratorlenmis harita. Bu harita yalnizca 25 kurum icerir
    #    ama tasidigi bilgi ham dosyada YOKTUR — ornegin "blackrock"un guncel
    #    CIK'e (2012383) cozulmesi, 2024'te donmus olan 1364742'ye degil.
    #    Bu ayrim ham cik-lookup-data.txt'den cikarilamaz, o yuzden harita
    #    otorite olarak kalir.
    cozum_kaynagi = "elle_kuratorlenmis_harita"
    adaylar = ciks.coz(institution)

    # 2) Haritada yoksa SEC'in TAM evrenine (1M+ kayit) dus. Her aday,
    #    gercekten 13F-HR dosyalayip dosyalamadigi SEC'e sorularak
    #    dogrulanir; /ADV gibi 13F dosyalamayan tescil kayitlari elenir.
    evren_bilgisi = None
    if not adaylar:
        evren = cik_evreni.coz(institution)
        evren_bilgisi = {
            "toplam_eslesme": evren.get("toplam_eslesme", 0),
            "indeks_boyutu": evren.get("indeks_boyutu", 0),
        }
        adaylar = [
            {"cik": a["manager_cik"], "ad": a["manager_name"]}
            for a in evren.get("adaylar", [])
        ]
        if adaylar:
            cozum_kaynagi = "sec_cik_lookup_evreni"
            # Belirsizligi GIZLEME: "AQR" gibi bir sorgu birden cok gercek
            # 13F dosyalayiciyla eslesebilir. Ilk sirayi dondurmekle
            # yetinip digerlerini yutmak, kullanicinin yanlis kuruma
            # baktigini fark etmemesine yol acardi.
            evren_bilgisi["secilen"] = adaylar[0]["ad"]
            evren_bilgisi["diger_adaylar"] = [
                {
                    "kurum": a["manager_name"],
                    "cik": a["manager_cik"],
                    "onucf_dosyalama_sayisi": a["onucf_dosyalama_sayisi"],
                }
                for a in evren.get("adaylar", [])[1:]
            ]

    if not adaylar:
        raise HTTPException(
            status_code=404,
            detail={
                "neden": f"'{institution}' icin 13F dosyalayan bir kurum bulunamadi",
                "arama_kapsami": (
                    "Once elle kuratorlenmis harita, sonra SEC'in ceyreklik "
                    "full-index (form.idx) 13F dosyalayici indeksi tarandi."
                ),
                "evren": evren_bilgisi,
                "kuratorlenmis_kurumlar": sorted(ciks.AMIRAL_GEMILERI.keys()),
            },
        )

    kurum = adaylar[0]
    veri = await _kurum_pozisyonlari(kurum["cik"])
    if not veri.get("basarili"):
        raise HTTPException(status_code=502, detail=veri)

    cozum = cusips.coz(tk)
    if not cozum["bulundu"]:
        cozum = cusips.isimle_ara(tk, veri["isim_indeksi"])

    if not cozum.get("bulundu"):
        return {
            "ticker": tk, "kurum": veri["kurum_adi"], "kurum_cik": veri["cik"],
            "donem": veri["donem"], "pozisyon_var": False,
            "neden": "ticker CUSIP'e cozulemedi",
            "cozumleme": cozum,
            # Belirsizlik bu yolda da gorunur olmali: kullanici yanlis
            # kuruma bakiyor olabilir ve bunu fark edemezdi.
            "kurum_cozum_kaynagi": cozum_kaynagi,
            "evren_arama": evren_bilgisi,
        }

    cusip = cozum["cusip"]
    p = veri["pozisyonlar"].get(cusip)
    if not p:
        return {
            "ticker": tk, "cusip": cusip, "kurum": veri["kurum_adi"],
            "kurum_cik": veri["cik"], "donem": veri["donem"],
            "pozisyon_var": False,
            "neden": (f"{veri['kurum_adi']} {veri['donem']} donemli 13F'inde "
                      f"{tk} ({cusip}) bildirmedi"),
            "onbellekten": veri.get("onbellekten", False),
            "kurum_cozum_kaynagi": cozum_kaynagi,
            "evren_arama": evren_bilgisi,
        }

    kayit = _pozisyon_kaydi(cusip, p, veri, cozum)
    kayit.update({
        "ticker": tk,
        "pozisyon_var": True,
        "onbellekten": veri.get("onbellekten", False),
        "kaynak": "SEC EDGAR (resmi, anahtarsiz)",
        "kurum_cozum_kaynagi": cozum_kaynagi,
        "evren_arama": evren_bilgisi,
        "not": ("13F verisi ceyrek sonu FOTOGRAFIDIR ve ceyrek bitiminden "
                "45 gun sonrasina kadar aciklanabilir; guncel pozisyonu "
                "gostermez."),
    })
    return kayit


@app.get("/holders/{ticker}")
async def holders(
    ticker: str,
    top: int = Query(10, ge=1, le=30, description="Kac kurum dondurulsun"),
    sadece_onbellek: bool = Query(
        False, description="True ise sadece onbellekteki kurumlara bakar (hizli)"),
    max_kurum: int = Query(
        6, ge=1, le=26,
        description="Bu cagride EN FAZLA kac kurum SEC'ten cekilsin (sinirsiz tarama yok)"),
):
    """
    Bir hissede pozisyonu olan kurumlari, hisse degerine gore siralar.

    KAPSAM DURUSTLUGU: Bu, "en buyuk sahipler" listesi DEGILDIR — yalnizca
    bu servisin bildigi kurum haritasi taranir. Taranmayan/atlanan kurumlar
    yanitta ACIKCA listelenir; sessiz kesme yapilmaz.
    """
    tk = ticker.upper().strip()
    cozum_sabit = cusips.coz(tk)

    tum = ciks.tum_kurumlar()
    bulunanlar, atlanan, hata = [], [], []
    cekilen = 0

    for k in tum:
        ob = await _onbellek_al(f"kurum:{k['cik']}:son")
        if ob is None:
            if sadece_onbellek:
                atlanan.append({**k, "neden": "onbellekte yok (sadece_onbellek=true)"})
                continue
            if cekilen >= max_kurum:
                atlanan.append({**k, "neden": f"max_kurum={max_kurum} sinirina ulasildi"})
                continue
            try:
                ob = await _kurum_pozisyonlari(k["cik"])
                cekilen += 1
            except Exception as e:
                hata.append({**k, "hata": f"{type(e).__name__}: {str(e)[:120]}"})
                continue

        if not ob.get("basarili"):
            hata.append({**k, "hata": ob.get("neden")})
            continue

        cozum = cozum_sabit if cozum_sabit["bulundu"] else cusips.isimle_ara(
            tk, ob.get("isim_indeksi", {}))
        if not cozum.get("bulundu"):
            continue

        p = ob["pozisyonlar"].get(cozum["cusip"])
        if not p or p["hisse_deger_usd"] <= 0:
            continue

        bulunanlar.append(_pozisyon_kaydi(cozum["cusip"], p, ob, cozum))

    bulunanlar.sort(key=lambda x: -x["hisse_pozisyonu"]["deger_usd"])

    return {
        "ticker": tk,
        "cusip": cozum_sabit.get("cusip"),
        "cusip_dogrulandi": cozum_sabit.get("dogrulandi", False),
        "bulunan_kurum_sayisi": len(bulunanlar),
        "sahipler": bulunanlar[:top],
        "kapsam": {
            "haritadaki_kurum": len(tum),
            "bu_cagride_cekilen": cekilen,
            "atlanan": atlanan,
            "hata_alan": hata,
            "uyari": ("Bu liste yalnizca bu servisin kurum haritasini kapsar; "
                      "hissenin TUM 13F sahiplerini gostermez. Atlanan kurumlar "
                      "yukarida acikca listelenmistir."),
        },
        "kaynak": "SEC EDGAR (resmi, anahtarsiz)",
    }
