"""GEX sonuc onbellegi — kota tasarrufu, tazelikten odun VERMEDEN.

NEDEN GEREKLI (olculdu, 10.09.2026)
===================================
FlashAlpha ucretsiz tier'inde anahtar basina gunde 5 istek hakki var; bu
kurulumda 5 anahtar tanimli, yani gunluk TOPLAM 25 istek. Buna karsilik
/gex ucu SONUCU HIC ONBELLEKLEMIYORDU: ayni sembol icin arka arkaya iki
istek, gunluk 25 hakkin ikisini birden yakiyordu. Panelde bir sembolu iki
kez acmak ya da sayfayi yenilemek gunluk butcenin %8'ini harciyordu.

Kardes uc /dex-vanna zaten 15 dakikalik onbellek kullaniyor (ve FlashAlpha
kotasi hic tuketmiyor). Ayni deseni /gex'e tasimak bu maddenin somut ciktisi.

TAZELIK GIZLENMEZ
=================
Onbellek, veriyi "taze" gostermenin bir yolu DEGILDIR. FlashAlpha ucretsiz
tier'i zaten ~15 dakika gecikmeli veri veriyor; ustune 15 dakikalik onbellek
konunca en kotu durumda veri ~30 dakika eski olabilir. Bunu soylemeden
saklamak, kullaniciya olcumden daha yeni bir sey gosterildigi izlenimi
verirdi. Bu yuzden her onbellek isabetinde yanit, verinin KAC SANIYE ONCE
alindigini ve toplam olasi gecikmeyi acikca tasir.

ONBELLEGE YALNIZCA BASARILI YANIT GIRER
=======================================
Hata yanitlari (kota doldu, plan kisitlamasi, 502) onbelleklenmez. Bir
hatayi 15 dakika boyunca tekrar tekrar sunmak, gecici bir arizayi kalici
hale getirirdi.
"""
from __future__ import annotations

ONBELLEK_ONEKI = "gex:sonuc:"

# Kapsam disi sembollerin olumsuz onbellegi. Ayri onek, ayri anlam.
KAPSAM_DISI_ONEKI = "gex:kapsamdisi:"

# FlashAlpha'nin sembolun ucretsiz evrende olmadigini bildirdigi hata kodu.
KAPSAM_DISI_KODU = "symbol_not_in_free_universe"

# FlashAlpha ucretsiz tier'inin kendi gecikmesi (dakika) — belgelenmis deger.
KAYNAK_GECIKMESI_DK = 15


def onbellek_anahtari(ticker: str, expiration: str | None) -> str:
    """Sembol ve vade birlikte anahtari belirler.

    expiration FARKLI ise veri de farklidir; tek anahtarda toplamak yanlis
    vadenin GEX'ini dondururdu.
    """
    # expiration yalnizca str ya da None olabilir. FastAPI HTTP yolunda bunu
    # zaten garanti eder; baska bir tur geldiyse bu bir programlama hatasidir
    # ve SESSIZCE "tum vadeler" diye anahtarlamak, YANLIS vadenin GEX'ini
    # onbellekten sunmak demektir. Bu yuzden gurultulu basarisiz olunur.
    if expiration is not None and not isinstance(expiration, str):
        raise TypeError(
            f"expiration str ya da None olmali, {type(expiration).__name__} geldi")
    if not isinstance(ticker, str):
        raise TypeError(
            f"ticker str olmali, {type(ticker).__name__} geldi")
    t = ticker.upper().strip()
    v = (expiration or "").strip() or "tum"
    return f"{ONBELLEK_ONEKI}{t}:{v}"


def tazelik_metni(onbellek_yasi_sn: int, ttl_sn: int) -> str:
    """Kullaniciya gosterilecek DURUST tazelik aciklamasi."""
    if onbellek_yasi_sn <= 0:
        return (f"FlashAlpha ucretsiz tier: ~{KAYNAK_GECIKMESI_DK} dakika "
                f"gecikmeli (az once alindi)")
    azami_dk = KAYNAK_GECIKMESI_DK + (ttl_sn + 59) // 60
    return (f"FlashAlpha ucretsiz tier: ~{KAYNAK_GECIKMESI_DK} dakika gecikmeli; "
            f"bu yanit {onbellek_yasi_sn} sn once alinmis onbellekten geliyor "
            f"(toplam gecikme en fazla ~{azami_dk} dakika)")


def isabet_yaniti(saklanan: dict, simdi_ts: float, ttl_sn: int,
                  guncel_kota: dict) -> dict:
    """Onbellekten donen yaniti kurar.

    Kota durumu SAKLANMAZ, her zaman canli okunur: saklanan kota bilgisi
    dakikalar icinde yanlislasir ve kullaniciya olmayan bir hak gosterirdi.
    """
    alindi = float(saklanan.get("_alindi_ts") or 0)
    yas = max(0, int(simdi_ts - alindi)) if alindi else 0
    yanit = {k: v for k, v in saklanan.items() if not k.startswith("_")}
    yanit["onbellekten"] = True
    yanit["onbellek_yasi_saniye"] = yas
    yanit["flashalpha_kotasi_tuketildi"] = False
    yanit["veri_tazeligi"] = tazelik_metni(yas, ttl_sn)
    yanit["kota_durumu"] = guncel_kota
    return yanit


def saklanacak_govde(yanit: dict, simdi_ts: float) -> dict:
    """Onbellege yazilacak govdeyi kurar.

    Kota durumu ve onbellek isaretleri saklanmaz — bunlar her yanitta
    yeniden uretilir.
    """
    govde = {k: v for k, v in yanit.items()
             if k not in ("kota_durumu", "onbellekten", "onbellek_yasi_saniye",
                          "veri_tazeligi", "flashalpha_kotasi_tuketildi")}
    govde["_alindi_ts"] = float(simdi_ts)
    return govde


def kapsam_disi_anahtari(ticker: str) -> str:
    """Ucretsiz planin kapsamadigi semboller icin OLUMSUZ onbellek anahtari."""
    if not isinstance(ticker, str):
        raise TypeError(f"ticker str olmali, {type(ticker).__name__} geldi")
    return f"{KAPSAM_DISI_ONEKI}{ticker.upper().strip()}"


def kapsam_disi_mi(govde: str) -> bool:
    """Yanit govdesi 'bu sembol ucretsiz evrende yok' diyor mu?

    NEDEN AYRI ELE ALINIYOR
    =======================
    Genel bir hatayi onbelleklemek yanlistir: gecici bir arizayi kalici
    hale getirir. Ama bu hata GECICI DEGIL — planin kapsadigi sembol
    kumesi (10.09.2026 itibariyla ~250 sembol) dakikalar icinde
    degismez. Onbelleklenmezse kapsam disi bir sembol her soruldugunda
    gunluk 25 hakkin biri kalici olarak yanar; olculdu: ZZTEST icin tam
    olarak bu oldu.

    TTL gun sonuna baglanir: kullanici plani yukseltirse en gec ertesi
    gun (kota sifirlanmasiyla ayni anda) yeniden denenir, yani olumsuz
    kayit bir yukseltmeyi kalici olarak gizlemez.
    """
    return KAPSAM_DISI_KODU in (govde or "").lower()
