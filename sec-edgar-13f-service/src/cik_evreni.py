"""
13F DOSYALAYICI EVRENI — SEC full-index'ten isimden CIK cozumleme.

=======================================================================
NEDEN BU MODUL VAR
=======================================================================
ciks.py'deki AMIRAL_GEMILERI haritasi ELLE yazilmis 25 kurum iceriyor.
Bu harita disinda kalan bir kurum sorulunca servis 404 donuyordu; bosluk
LLMQuant'in ucretli API'siyle (1000 yonetici) doldurulmustu ve o servisin
kredisi bitince ozellik tamamen kullanilamaz hale geldi.

SEC ayni bilgiyi UCRETSIZ ve ANAHTARSIZ yayimliyor.

=======================================================================
NEDEN cik-lookup-data.txt DEGIL, form.idx (OLCULEREK DEGISTIRILDI)
=======================================================================
Ilk surum SEC'in cik-lookup-data.txt dosyasini (1.056.221 satir, 39 MB)
kullaniyordu. CALISMADI ve nedeni olculdu:

  1) O dosya TUM EDGAR varliklarini icerir — sirketler, fonlar, trust'lar,
     bireyler. 13F dosyalayanlari ayirt etmenin bir yolu yok. "AQR"
     sorgusu 38+ kayitla eslesiyordu ve bunlarin neredeyse tamami 13F
     dosyalamayan fon kayitlariydi ("AQR FUNDS", "AQR TRUST",
     "AQR ABSOLUTE RETURN OFFSHORE FUND, L.P." ...).
  2) Alfabetik siralamada "AQR ABSOLUTE..." kayitlari "AQR CAPITAL
     MANAGEMENT LLC"nin onune geciyordu; aday listesi kirpilinca aranan
     kurum listeye HIC giremiyordu (38 yerel eslesme / 0 dogrulanan).
  3) Her adayi ayri ayri submissions API'sine sorup 13F dosyalayip
     dosyalamadigini dogrulamak gerekiyordu — 40 istek, SEC hiz
     siniriyla ~8 saniye.

form.idx bu uc sorunu birden ortadan kaldiriyor: SEC'in ceyreklik
full-index dosyasi zaten SADECE dosyalanmis formlari listeler ve form
turunu satirda tasir. "13F-HR" ile baslayan satirlari almak, tanimi
geregi 13F dosyalayan kurumlarin listesini verir — tahmin yok,
dogrulama cagrisi yok, /ADV karisikligi yok.

Olculdu (22.08.2026, 2026/QTR2):
  - form.idx : 53 MB, 352.956 satir, indirme 1.16 sn
  - Bunun icinden 13F-HR: 9.623 dosyalama
  - "AQR CAPITAL MANAGEMENT LLC | 1167557" dogrudan mevcut

Kapsam karsilastirmasi: LLMQuant 1.000 yonetici kapsiyordu; bu yontem
tek ceyrekte ~9.600 dosyalama (binlerce tekil kurum) veriyor.

=======================================================================
NEDEN INDEKS DISKTE KUCUK BIR JSON OLARAK TUTULUYOR
=======================================================================
Ham form.idx dosyalari buyuk (ceyrek basina ~53 MB) ama isimize yarayan
kisim kucuk. Indirme sirasinda satirlar akis halinde suzulup yalnizca
13F-HR kayitlari sakalanir; sonuc birkac yuz KB'lik bir JSON olur.
Boylece ne Redis sisirilir ne de her aramada 53 MB taranir.
"""
import json
import logging
import os
import re
import time

import httpx

logger = logging.getLogger("sec13f.evren")

INDEX_URL = "https://www.sec.gov/Archives/edgar/full-index/{yil}/QTR{ceyrek}/form.idx"
INDEKS_YOLU = os.getenv("CIK_EVREN_INDEKS", "/tmp/13f_filer_indeksi.json")

# Kac ceyrek geriye bakilacak. 2 ceyrek, "su an aktif dosyalayan"
# kurumlari kapsamak icin yeterli; daha geriye gitmek listeyi artik
# dosyalamayan kurumlarla sisirirdi.
CEYREK_SAYISI = int(os.getenv("CIK_EVREN_CEYREK", "2"))
TAZELEME_SANIYE = int(os.getenv("CIK_EVREN_TAZELEME_SANIYE", str(7 * 24 * 3600)))

_SATIR_BOL = re.compile(r"\s{2,}")

# Bellek ici indeks (surec omru boyunca). Dosyadan bir kez yuklenir.
_indeks: list[dict] | None = None
_indeks_zamani: float = 0.0


def _dosya_yasi_saniye() -> float | None:
    try:
        return time.time() - os.path.getmtime(INDEKS_YOLU)
    except OSError:
        return None


def dosya_durumu() -> dict:
    yas = _dosya_yasi_saniye()
    kayit = None
    if _indeks is not None:
        kayit = len(_indeks)
    elif yas is not None:
        try:
            with open(INDEKS_YOLU) as f:
                kayit = len(json.load(f).get("kurumlar", []))
        except Exception:
            kayit = None
    return {
        "indeks_dosyasi": INDEKS_YOLU,
        "var": yas is not None,
        "yas_saat": round(yas / 3600, 1) if yas is not None else None,
        "tazeleme_saat": TAZELEME_SANIYE / 3600,
        "bayat": yas is None or yas > TAZELEME_SANIYE,
        "tekil_13f_kurum": kayit,
        "taranan_ceyrek": CEYREK_SAYISI,
    }


def _son_ceyrekler(n: int) -> list[tuple[int, int]]:
    """Bugunden geriye dogru n ceyrek. SEC index'i ceyrek bazinda yayimlar."""
    simdi = time.gmtime()
    yil, ceyrek = simdi.tm_year, (simdi.tm_mon - 1) // 3 + 1
    out = []
    for _ in range(n):
        out.append((yil, ceyrek))
        ceyrek -= 1
        if ceyrek == 0:
            ceyrek = 4
            yil -= 1
    return out


async def indeksi_hazirla(sinirlayici, basliklar: dict, zorla: bool = False) -> dict:
    """
    Son N ceyregin form.idx dosyalarini indirip 13F-HR kayitlarini suzer.

    Ham dosya diske YAZILMAZ: akis halinde okunur, yalnizca 13F-HR
    satirlari bellekte tutulur ve kucuk bir JSON'a yazilir.
    """
    global _indeks, _indeks_zamani

    yas = _dosya_yasi_saniye()
    if not zorla and yas is not None and yas <= TAZELEME_SANIYE:
        return {"indirildi": False, "neden": "indeks guncel", "yas_saat": round(yas / 3600, 1)}

    kurumlar: dict[str, dict] = {}
    ceyrek_sonuclari = []
    basladi = time.time()

    async with httpx.AsyncClient(timeout=180.0, follow_redirects=True) as c:
        for yil, ceyrek in _son_ceyrekler(CEYREK_SAYISI):
            url = INDEX_URL.format(yil=yil, ceyrek=ceyrek)
            await sinirlayici.bekle()
            try:
                bulunan = 0
                async with c.stream("GET", url, headers=basliklar) as r:
                    if r.status_code != 200:
                        ceyrek_sonuclari.append(
                            {"ceyrek": f"{yil}Q{ceyrek}", "durum": r.status_code}
                        )
                        continue
                    artik = ""
                    async for parca in r.aiter_text(1 << 20):
                        satirlar = (artik + parca).split("\n")
                        artik = satirlar.pop()
                        for satir in satirlar:
                            if not satir.startswith("13F-HR"):
                                continue
                            p = _SATIR_BOL.split(satir.rstrip())
                            if len(p) < 4:
                                continue
                            ad, cik = p[1].strip(), p[2].strip()
                            if not cik.isdigit() or not ad:
                                continue
                            cik = str(int(cik))
                            mevcut = kurumlar.get(cik)
                            if mevcut is None:
                                kurumlar[cik] = {
                                    "ad": ad,
                                    "cik": cik,
                                    "dosyalama": 1,
                                    "son_tarih": p[3].strip(),
                                }
                            else:
                                mevcut["dosyalama"] += 1
                                if p[3].strip() > mevcut["son_tarih"]:
                                    mevcut["son_tarih"] = p[3].strip()
                                    mevcut["ad"] = ad
                            bulunan += 1
                ceyrek_sonuclari.append(
                    {"ceyrek": f"{yil}Q{ceyrek}", "durum": 200, "onucf_satir": bulunan}
                )
            except Exception as e:
                ceyrek_sonuclari.append(
                    {"ceyrek": f"{yil}Q{ceyrek}", "hata": type(e).__name__}
                )

    if not kurumlar:
        raise RuntimeError("form.idx'ten hicbir 13F-HR kaydi cikarilamadi; eski indeks korundu")

    liste = sorted(kurumlar.values(), key=lambda x: x["ad"])
    gecici = INDEKS_YOLU + ".yaziliyor"
    os.makedirs(os.path.dirname(INDEKS_YOLU) or ".", exist_ok=True)
    with open(gecici, "w") as f:
        json.dump({"uretildi": time.time(), "kurumlar": liste}, f)
    os.replace(gecici, INDEKS_YOLU)

    _indeks = liste
    _indeks_zamani = time.time()
    sure = time.time() - basladi
    logger.info(
        "13F dosyalayici indeksi hazir: %s tekil kurum, %.2f sn, ceyrekler=%s",
        len(liste), sure, ceyrek_sonuclari,
    )
    return {
        "indirildi": True,
        "tekil_kurum": len(liste),
        "sure_sn": round(sure, 2),
        "ceyrekler": ceyrek_sonuclari,
    }


def _yukle() -> list[dict]:
    global _indeks, _indeks_zamani
    if _indeks is not None:
        return _indeks
    try:
        with open(INDEKS_YOLU) as f:
            _indeks = json.load(f).get("kurumlar", [])
            _indeks_zamani = time.time()
    except Exception:
        _indeks = []
    return _indeks


def _ad_normalize(s: str) -> str:
    return " ".join((s or "").upper().split())


def coz(sorgu: str, azami: int = 10) -> dict:
    """
    Isimden 13F dosyalayan kurumlari cozer. AG ISTEGI YAPMAZ — indeks
    zaten yalnizca 13F dosyalayanlari icerdigi icin ek dogrulama gereksiz.

    Siralama: isim eslesme kalitesi (tam > basta > icinde), esitlikte
    OLCULEN dosyalama sayisi (cok dosyalayan yerlesik yonetici one gecer).
    Isim UZUNLUGUNA gore siralama YAPILMAZ — ilk surumde denendi ve
    olculebilir sekilde yanlisti ("AQR FUNDS", "AQR CAPITAL MANAGEMENT
    LLC"nin onune geciyordu).
    """
    q = _ad_normalize(sorgu)
    if len(q) < 3:
        return {"adaylar": [], "toplam_eslesme": 0, "indeks_boyutu": len(_yukle())}

    kayitlar = _yukle()
    eslesenler = []
    for k in kayitlar:
        ad = _ad_normalize(k["ad"])
        if q not in ad:
            continue
        if ad == q:
            puan = 0
        elif ad.startswith(q):
            puan = 1
        else:
            puan = 2
        eslesenler.append((puan, -k.get("dosyalama", 0), k))

    eslesenler.sort(key=lambda x: (x[0], x[1]))
    kalite = ["tam", "basta", "icinde"]
    adaylar = [
        {
            "manager_cik": k["cik"],
            "manager_name": k["ad"],
            "eslesme_kalitesi": kalite[p],
            "onucf_dosyalama_sayisi": k.get("dosyalama", 0),
            "son_dosyalama_tarihi": k.get("son_tarih"),
            "kaynak": "sec_full_index_13f",
        }
        for p, _, k in eslesenler[:azami]
    ]
    return {
        "adaylar": adaylar,
        "toplam_eslesme": len(eslesenler),
        "indeks_boyutu": len(kayitlar),
        "not": (
            "Adaylar SEC'in ceyreklik full-index (form.idx) dosyasindan, "
            "SADECE 13F-HR dosyalayan kurumlar arasindan secildi; ayrica "
            "bir dogrulama cagrisi gerekmez."
        ),
    }
