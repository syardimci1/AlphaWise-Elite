"""DIX metodolojisi — borsa disi kisa hacim orani, sepet agirlikli.

MEVCUT DPKE GOSTERGESI KALDIRILMIYOR. Bu, onun yerine gecmez; farkli
bir sey olcer ve gamma-exposure-service'teki DPKE oldugu gibi durur.

ESKIMIS BIR IMKANSIZLIK IDDIASI
===============================
gamma-exposure-service'teki METODOLOJI metni sunu soyluyor:

    "FINRA'nin haftalik ATS Transparency verisi islem YONU ICERMEZ ...
     Bu nedenle gercek DIX bu veriden HESAPLANAMAZ."

Bu ifade HAFTALIK ATS veri kumesi icin dogrudur ve o gun icin dogruydu.
Ama GUNLUK Reg SHO veri kumesi 23.08.2026'da, o metin yazildiktan SONRA
eklendi — ve DIX'in yayimlanmis mekanizmasi tam olarak o veriye dayanir.
Yani imkansizlik iddiasi bugun artik kapsam disi kalmistir.

DIX'IN YAYIMLANMIS MEKANIZMASI
==============================
SqueezeMetrics'in acikladigi sezgi sudur: bir yatirimci karanlik havuzda
ALIRKEN, karsi tarafta duran piyasa yapici pozisyonu ACIGA SATAR. Bu
yuzden borsa disi baskilarda "short" isaretli hacmin PAYI, alis baskisinin
vekilidir. Yani yon bilgisi islem bazinda isaretlemeden degil, kisa hacim
oranindan gelir.

Reg SHO gunluk dosyasi tam olarak bunu verir:
    ShortVolume / TotalVolume, FINRA'ya bildirilen (borsa disi) hacim icin.

OLCULDU (10.09.2026, CDN'den indirilerek):
    2026-09-03: 12.266 sembol, hacim agirlikli %50,89; 7 mega-cap %38,68
    2026-09-09: 12.275 sembol, hacim agirlikli %52,11; 7 mega-cap %44,77
Gercek DIX tarihsel olarak %38-48 bandinda hareket eder; mega-cap
agirlikli degerler bu bantla ortusuyor.

BU YINE DE RESMI DIX DEGILDIR — FARKLAR ACIKCA:
===============================================
  1. KAPSAM. Reg SHO "FINRA'ya bildirilen" tum borsa disi hacmi kapsar:
     ATS (karanlik havuz) VE broker ic eslestirmesi. DIX yalnizca karanlik
     havuz baskilarini kullanir. Bu payda daha genistir.
  2. SEPET. DIX S&P 500 bilesenleri uzerinden hesaplanir. Bu depoda
     dogrulanmis bir S&P 500 listesi YOK; sepet uydurulmaz, DISARIDAN
     verilir ve kapsam raporlanir.
  3. AGIRLIK. DIX dolar hacmiyle agirliklandirir. Fiyat verisi yoksa
     dolar agirlik hesaplanamaz; bu durumda hisse hacmi agirligi
     kullanilir ama bu SESSIZCE YAPILMAZ - hangi agirligin kullanildigi
     her yanitta bildirilir. Iki agirlik farkli seylerdir ve birini
     otekinin yerine gecirmek olcumu degistirir.
  4. NORMALIZASYON. DIX'in ic olcekleme/duzlestirme ayrintilari acik
     degildir. Burada ham oran verilir, uydurma bir olcekleme yapilmaz.
"""
from __future__ import annotations

DOLAR_AGIRLIK = "dolar_hacmi"
HISSE_AGIRLIK = "hisse_hacmi"


def dix_hesapla(gun_verisi: dict, sepet, fiyatlar: dict | None = None) -> dict:
    """Sepet icin borsa disi kisa hacim oranini agirlikli hesaplar.

    gun_verisi : {sembol: (kisa, muaf, toplam)} — Reg SHO gunluk dosyasi
    sepet      : hesaba katilacak semboller
    fiyatlar   : {sembol: fiyat} — verilirse DOLAR agirligi kullanilir

    Sepetteki bir sembol dosyada yoksa SIFIR SAYILMAZ; kapsam disi olarak
    ayrica raporlanir. Sifir saymak, o sembolun "hic kisa hacmi yoktu"
    demek olurdu ve endeksi asagi cekerdi.
    """
    sepet = [s.upper().strip() for s in (sepet or []) if s and s.strip()]
    if not sepet:
        return _bos("sepet bos; endeks TANIMSIZ", sepet_boyu=0)

    # Hangi semboller icin gercekten hacim var? Agirlik karari YALNIZCA
    # bunlara gore verilir; dosyada olmayan bir sembolun fiyatinin
    # bulunmamasi dolar agirligini dusurmemeli.
    hacimli = []
    kapsanmayan = []
    for s in sepet:
        k = (gun_verisi or {}).get(s)
        if not k or k[2] is None or k[2] <= 0:
            kapsanmayan.append(s)
        else:
            hacimli.append(s)

    if not hacimli:
        return _bos(f"sepetteki {len(sepet)} sembolun hicbiri icin borsa disi "
                    f"hacim bulunamadi; endeks OLCULEMEDI",
                    sepet_boyu=len(sepet), kapsanmayan=kapsanmayan)

    # AGIRLIK KARARI DONGUDEN ONCE VERILIR. Sepetin bir kismini dolar,
    # kalanini hisse hacmiyle tartmak, tanimsiz bir karisim uretirdi.
    fiyatsiz = [s for s in hacimli
                if not fiyatlar or (fiyatlar.get(s) or 0) <= 0]
    dolar = bool(fiyatlar) and not fiyatsiz

    pay = payda = 0.0
    for s in hacimli:
        kisa, _muaf, toplam = gun_verisi[s][0], gun_verisi[s][1], gun_verisi[s][2]
        agirlik = toplam * fiyatlar[s] if dolar else toplam
        # kisa/toplam orani, agirlikla carpilarak toplanir.
        pay += (kisa / toplam) * agirlik
        payda += agirlik

    if payda <= 0:
        return _bos("agirlik toplami sifir; endeks OLCULEMEDI",
                    sepet_boyu=len(sepet), kapsanmayan=kapsanmayan)

    return {
        "olculdu": True,
        "dix_yuzde": round(pay / payda * 100.0, 2),
        "agirlik": DOLAR_AGIRLIK if dolar else HISSE_AGIRLIK,
        "sepet_boyu": len(sepet),
        "katilan_sembol": len(hacimli),
        "kapsanmayan_sembol": len(kapsanmayan),
        "kapsam_yuzde": round(len(hacimli) / len(sepet) * 100.0, 1),
        "kapsanmayanlar": kapsanmayan[:50],
        "fiyati_olmayanlar": fiyatsiz[:50] if fiyatlar else [],
        "resmi_dix_mi": False,
        "not": _not(dolar, fiyatsiz if fiyatlar else []),
    }


def _not(dolar: bool, fiyatsiz) -> str:
    temel = ("RESMI DIX DEGILDIR. Kapsam (ATS + broker ic eslestirmesi), "
             "sepet ve agirlik bakimindan farklidir; ayrintilar modul "
             "basligindadir. Yon iddiasi kalibre EDILMEMISTIR.")
    if dolar:
        return "Dolar hacmi agirligi kullanildi (DIX'in yaptigi gibi). " + temel
    if fiyatsiz:
        return (f"HISSE hacmi agirligi kullanildi cunku {len(fiyatsiz)} sembol "
                f"icin fiyat yoktu. DIX dolar hacmiyle agirliklandirir; bu "
                f"FARKLI bir olcumdur. " + temel)
    return ("HISSE hacmi agirligi kullanildi (fiyat verilmedi). DIX dolar "
            "hacmiyle agirliklandirir; bu FARKLI bir olcumdur. " + temel)


def _bos(neden, sepet_boyu=0, kapsanmayan=None):
    return {
        "olculdu": False, "dix_yuzde": None, "agirlik": None,
        "sepet_boyu": sepet_boyu,
        "katilan_sembol": 0,
        "kapsanmayan_sembol": len(kapsanmayan or []),
        "kapsam_yuzde": 0.0,
        "kapsanmayanlar": (kapsanmayan or [])[:50],
        "fiyati_olmayanlar": [],
        "resmi_dix_mi": False,
        "not": neden,
    }
