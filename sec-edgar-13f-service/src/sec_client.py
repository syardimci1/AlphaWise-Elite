"""
SEC EDGAR istemcisi — data.sec.gov + www.sec.gov/Archives, HAM REST.

=======================================================================
NEDEN KUTUPHANE (edgartools) YERINE HAM REST — OLCUMLE KARAR
=======================================================================
dgunning/edgartools incelendi (2026-08-19): MIT lisansli, GERCEKTEN
bakimli (son surum 5.51.0 ayni gun yayinlandi, 90 gunde 76 issue
kapatilmis, 15 surum). Yani "terk edilmis" degil — kutuphane saglikli.
Buna ragmen ham REST secildi, gerekce OLCULDU:

  1) IMAJ MALIYETI (gercek build ile olculdu)
       python:3.11-slim                 189 MB
       + edgartools                     734 MB   (48 paket)
       + httpx/fastapi/redis (bu servis) ~250 MB (~15 paket)
     13F icin gereken 3 HTTP cagrisi ugruna 545 MB ek yuk ve
     pandas/pyarrow bagimlilik yuzeyi tasinmis olurdu.

  2) HIZ SINIRI KOORDINASYONU (belirleyici gerekce)
     SEC'in siniri IP BAZLIDIR ("regardless of the number of machines").
     Bir kutuphanenin kendi ic kisitlayicisi, ayni sunucudaki DIGER
     servislerden habersizdir; her biri kendini uyumlu sanarken toplam
     tavani asabilir. Ham REST ile kova Redis'te tutulur ve ileride
     tum SEC tuketicileri ayni kovayi paylasabilir.

  3) SURUM RISKI
     edgartools PyPI'da hala "4 - Beta" siniflandirmasinda ve 6.0
     yol haritasi Python >= 3.11 + pandas 3.0'a gecisi (kirici
     degisiklik) planliyor.

Karar gerekcesi budur; kutuphane kotu oldugu icin degil, bu servisin
ihtiyaci kutuphanenin getirdigi yukten kucuk oldugu icin.

=======================================================================
13F ZINCIRI (canli dogrulandi, 2026-08-19)
=======================================================================
SEC'de "13F endpoint'i" YOKTUR. Uc adim gerekir:

  1) https://data.sec.gov/submissions/CIK##########.json
     10 haneli, sifir dolgulu CIK. form[] icinde "13F-HR" filtrelenir.
     UYARI: filings.recent ~1000 kayitta kesilir; daha eskisi
     filings.files[] altindadir.

  2) https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_dash}/index.json
     Bilgi tablosunun adi SABIT DEGILDIR:
       BlackRock -> form13fInfoTable.xml
       Berkshire -> 56757.xml
     Bu yuzden dosya adi tahmin edilmez, index.json'dan bulunur.
     primary_doc.xml yalnizca kapak sayfasidir, pozisyon icermez.

  3) Bilgi tablosu XML'i ayristirilir.
     KRITIK: ayni CUSIP BIRDEN COK satirda gecer (otherManager
     kirilimi). BlackRock 2026-06-30'da NVDA 24 ayri COM satirinda.
     Toplama CUSIP bazinda yapilmazsa pozisyon oldugundan kucuk gorunur.

     KRITIK 2: putCall alani dolu satirlar TUREVDIR (opsiyon).
     Ayni NVDA icin 9 Call + 9 Put satiri daha var. Hisse pozisyonuyla
     karistirilirsa deger sisirilir; bu yuzden ayri raporlanir.

=======================================================================
DEGER BIRIMI — SESSIZ HATA KAYNAGI
=======================================================================
SEC'in 2022 degisikligi (Ocak 2023'te yururluge girdi) ile <value>
alani BIN USD yerine TAM USD'ye gecti. Eski dosyalari 1000'le
carpmayi unutmak (ya da yenileri carpmak) 1000 KAT hataya yol acar.
Burada donem tarihine gore normalize edilir ve kullanilan birim
yanitta ACIKCA belirtilir.
"""
import logging
import os
import xml.etree.ElementTree as ET
from collections import defaultdict

import httpx

logger = logging.getLogger("sec13f.client")

DATA_TABAN = "https://data.sec.gov"
ARSIV_TABAN = "https://www.sec.gov/Archives"

# SEC User-Agent'i ZORUNLU kilar. Eksikse HTTP 403 "Undeclared Automated Tool".
# Kaynak: sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
#   "Please declare your user agent in request headers:
#    User-Agent: Sample Company Name AdminContact@<sample company domain>.com"
# Ortam degiskeni ile degistirilebilir ama VARSAYILAN CALISIR — bu servis
# hicbir anahtar/ortam degiskeni olmadan da ayaga kalkar.
VARSAYILAN_UA = "AlphaWise Research Platform contact@alphawise.local"

# 2023 oncesi donemlerde <value> BIN USD'dir.
TAM_USD_GECIS_DONEMI = "2023-01-01"

XMLNS = "{http://www.sec.gov/edgar/document/thirteenf/informationtable}"


def kullanici_ajani() -> str:
    return os.getenv("SEC_USER_AGENT", VARSAYILAN_UA).strip() or VARSAYILAN_UA


class SecIstemci:
    def __init__(self, sinirlayici, zaman_asimi: float = 120.0):
        self.sinirlayici = sinirlayici
        self.zaman_asimi = zaman_asimi
        self._basliklar = {
            "User-Agent": kullanici_ajani(),
            # SEC verimli betik yazmayi acikca istiyor; ornek basliklarinda var.
            "Accept-Encoding": "gzip, deflate",
        }

    async def _getir(self, url: str, ikili: bool = False):
        """Her istek ONCE hiz sinirlayicidan gecer."""
        await self.sinirlayici.bekle()
        async with httpx.AsyncClient(timeout=self.zaman_asimi,
                                     follow_redirects=True) as c:
            r = await c.get(url, headers=self._basliklar)
            r.raise_for_status()
            return r.content if ikili else r.json()

    # ---------- ADIM 1: dosyalama listesi ----------

    async def onüc_f_dosyalari(self, cik: str, limit: int = 8) -> dict:
        """
        Bir CIK'in 13F-HR dosyalamalarini (yeniden eskiye) dondurur.
        """
        cik10 = str(cik).strip().lstrip("0").zfill(10)
        url = f"{DATA_TABAN}/submissions/CIK{cik10}.json"
        veri = await self._getir(url)

        son = (veri.get("filings") or {}).get("recent") or {}
        formlar = son.get("form", [])
        dosyalar = []
        for i, f in enumerate(formlar):
            if not f.startswith("13F-HR"):
                continue
            dosyalar.append({
                "form": f,
                "accession": son["accessionNumber"][i],
                "dosyalama_tarihi": son["filingDate"][i],
                "donem": son.get("reportDate", [None] * len(formlar))[i],
                "duzeltme": f.endswith("/A"),
            })
            if len(dosyalar) >= limit:
                break

        return {
            "cik": str(int(cik10)),
            "kurum_adi": veri.get("name"),
            "dosyalar": dosyalar,
            "eski_dosya_paketi_var": bool((veri.get("filings") or {}).get("files")),
            "not": ("filings.recent ~1000 kayitta kesilir; daha eski donemler "
                    "filings.files[] altindadir."),
        }

    # ---------- ADIM 2: bilgi tablosunu bul ----------

    async def bilgi_tablosu_url(self, cik: str, accession: str) -> dict:
        """
        index.json'dan bilgi tablosu XML'ini bulur. Dosya adi tahmin EDILMEZ.
        """
        acc_duz = accession.replace("-", "")
        cik_sade = str(int(str(cik).strip().lstrip("0") or "0"))
        idx_url = f"{ARSIV_TABAN}/edgar/data/{cik_sade}/{acc_duz}/index.json"
        idx = await self._getir(idx_url)

        ogeler = ((idx.get("directory") or {}).get("item")) or []
        adaylar = [
            o for o in ogeler
            if o.get("name", "").lower().endswith(".xml")
            and "primary_doc" not in o.get("name", "").lower()
        ]
        if not adaylar:
            return {"bulundu": False,
                    "neden": "index.json'da primary_doc disinda XML yok",
                    "ogeler": [o.get("name") for o in ogeler]}

        # birden fazlaysa en buyugu bilgi tablosudur
        def boyut(o):
            try:
                return int(o.get("size") or 0)
            except (TypeError, ValueError):
                return 0

        adaylar.sort(key=boyut, reverse=True)
        sec = adaylar[0]
        return {
            "bulundu": True,
            "dosya_adi": sec["name"],
            "boyut_bayt": boyut(sec),
            "url": f"{ARSIV_TABAN}/edgar/data/{cik_sade}/{acc_duz}/{sec['name']}",
        }

    # ---------- ADIM 3: ayristir ----------

    async def bilgi_tablosu_ayristir(self, url: str, donem: str = None) -> dict:
        """
        Bilgi tablosunu CUSIP bazinda toplar.

        Donen:
          {"pozisyonlar": {cusip: {...}}, "isim_indeksi": {norm_ad: {cusip}},
           "satir_sayisi": int, "deger_birimi": "tam_usd"}
        """
        ham = await self._getir(url, ikili=True)
        kok = ET.fromstring(ham)

        # 2023 oncesi BIN USD, sonrasi TAM USD
        bin_usd = bool(donem and donem < TAM_USD_GECIS_DONEMI)
        carpan = 1000 if bin_usd else 1

        poz = defaultdict(lambda: {
            "isim": None, "sinif": None,
            "hisse_deger_usd": 0, "hisse_adet": 0, "hisse_satir": 0,
            "turev_call_usd": 0, "turev_put_usd": 0, "turev_satir": 0,
        })
        satir = 0

        for it in kok:
            satir += 1

            def al(t):
                e = it.find(XMLNS + t)
                return e.text if e is not None else None

            cusip = (al("cusip") or "").strip()
            if not cusip:
                continue

            try:
                deger = int(float(al("value") or 0)) * carpan
            except (TypeError, ValueError):
                deger = 0

            adet = 0
            sh = it.find(XMLNS + "shrsOrPrnAmt")
            if sh is not None:
                s = sh.find(XMLNS + "sshPrnamt")
                if s is not None and s.text:
                    try:
                        adet = int(float(s.text))
                    except ValueError:
                        adet = 0

            p = poz[cusip]
            if p["isim"] is None:
                p["isim"] = al("nameOfIssuer")

            put_call = (al("putCall") or "").strip()
            if put_call:
                # TUREV — hisse pozisyonuyla TOPLANMAZ
                if put_call.lower().startswith("c"):
                    p["turev_call_usd"] += deger
                else:
                    p["turev_put_usd"] += deger
                p["turev_satir"] += 1
            else:
                p["hisse_deger_usd"] += deger
                p["hisse_adet"] += adet
                p["hisse_satir"] += 1
                if p["sinif"] is None:
                    p["sinif"] = al("titleOfClass")

        # isim indeksi (yedek cozumleme icin)
        from .cusips import normalize_ad
        isim_idx = defaultdict(set)
        for c, d in poz.items():
            if d["isim"]:
                isim_idx[normalize_ad(d["isim"])].add(c)

        return {
            "pozisyonlar": dict(poz),
            "isim_indeksi": {k: sorted(v) for k, v in isim_idx.items()},
            "satir_sayisi": satir,
            "tekil_cusip": len(poz),
            "deger_birimi": "tam_usd",
            "kaynak_birim": "bin_usd (2023 oncesi, 1000 ile carpildi)" if bin_usd else "tam_usd (2023 sonrasi)",
        }
