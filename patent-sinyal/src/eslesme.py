"""Sirket -> patent sahibi (assignee) eslestirmesi.

BU MODULUN VAR OLMA NEDENI
==========================
Patent kayitlarinda sirket, borsa koduyla degil PATENT SAHIBI ADIYLA gecer ve
bu ad genellikle isletme adi DEGILDIR:

    MSFT  -> "Microsoft Technology Licensing, LLC"   (olculdu, 09.2026)
    GOOGL -> "Google LLC" + "GOOGLE LLC" + "Google Inc."  (ayni sirket, uc yazim)

Yanlis bir ad sorgulandiginda kaynak hata VERMEZ — sifir sonuc doner. Bu, bu
depodaki en tehlikeli sessiz hata bicimidir: "eslestiremedik" ekranda
"bu sirketin patenti yok" olarak gorunur ve sirket yenilik uretmiyor sanilir.

BU YUZDEN SIFIR SONUC ASLA OLCUM SAYILMAZ
=========================================
Eslesme yalnizca kaynagin GERI DONDURDUGU sahip adlari sirket adiyla
ortusuyorsa dogrulanmis sayilir. Sifir sonuc her zaman OLCULEMEDI'dir:
sirketin gercekten patenti olmamasi ile adi bilememek, bu veriden
ayirt EDILEMEZ. Ayirt edilemeyen iki durumdan birini secip yazmak,
olcum degil tahmindir.
"""
from __future__ import annotations

import re
import unicodedata

from kaynak import KaynakHatasi, ornek_kayitlar
from olcum import OLCULDU, OLCULEMEDI, Olcum

# Sirket adlarinin sonundaki tuzel kisilik ekleri eslestirmede gurultu yaratir.
TUZEL_EKLER = {
    "inc", "incorporated", "corp", "corporation", "co", "company", "llc", "l l c",
    "ltd", "limited", "plc", "sa", "nv", "ag", "gmbh", "holdings", "holding",
    "group", "technologies", "technology", "licensing", "international",
    "the", "and", "of",
}


def _sadelestir(metin: str) -> str:
    """Buyuk/kucuk, noktalama ve aksan farklarini siler."""
    if not metin:
        return ""
    m = unicodedata.normalize("NFKD", metin)
    m = "".join(c for c in m if not unicodedata.combining(c))
    m = m.lower().replace("&", " and ")
    m = re.sub(r"[^a-z0-9]+", " ", m)
    return re.sub(r"\s+", " ", m).strip()


def anlamli_belirtecler(ad: str) -> tuple:
    """Sirket adindan tuzel kisilik eklerini atip ayirt edici kelimeleri birakir.

    "Microsoft Technology Licensing, LLC" -> ("microsoft",)
    "Advanced Micro Devices, Inc."        -> ("advanced", "micro", "devices")
    """
    parcalar = [p for p in _sadelestir(ad).split() if p and p not in TUZEL_EKLER]
    return tuple(parcalar)


def ortusuyor_mu(sirket_adi: str, sahip_adi: str) -> bool:
    """Donen sahip adi sirketle ortusuyor mu?

    Sirket adinin ayirt edici belirteclerinin TAMAMI sahip adinda geciyorsa
    ortusuyor sayilir. Tek kelimelik kismi eslesme kabul EDILMEZ; "Apple"
    ile "Apple Rush Company" ayrilabilsin diye.
    """
    s = anlamli_belirtecler(sirket_adi)
    if not s:
        return False
    h = set(anlamli_belirtecler(sahip_adi))
    return all(b in h for b in s)


def sahip_adaylari(sirket_adi: str, ornek_adet: int = 20, acan=None) -> Olcum:
    """Sirket adindan patent sahibi adlarini KAYNAKTAN okuyarak dogrular.

    Doner (OLCULDU): ayrinti["adaylar"] = [{"ad", "adet", "ortusuyor"}...]
    Hicbir sonuc gelmezse ya da hicbiri ortusmezse OLCULEMEDI — sifir degil.
    """
    if not (sirket_adi or "").strip():
        return Olcum(None, OLCULEMEDI, gerekce="sirket adi bos",
                     eksik=("sirket_adi",))
    sorgu = f'q=assignee:"{sirket_adi}"'
    try:
        kayitlar = ornek_kayitlar(sorgu, adet=ornek_adet, acan=acan)
    except KaynakHatasi as e:
        return Olcum(None, OLCULEMEDI, gerekce=f"kaynak okunamadi: {e}",
                     ayrinti={"sorgu": sorgu, "kaynak_kirilgan": True})

    sayim: dict = {}
    for k in kayitlar:
        ad = (k.get("sahip") or "").strip()
        if ad:
            sayim[ad] = sayim.get(ad, 0) + 1

    if not sayim:
        return Olcum(
            None, OLCULEMEDI,
            gerekce=(f"'{sirket_adi}' icin hicbir patent sahibi adi donmedi. "
                     f"Bu, sirketin patenti OLMADIGI anlamina GELMEZ — sahip "
                     f"adi bu veriden bilinemedi."),
            ayrinti={"sorgu": sorgu, "kaynak_kirilgan": True})

    adaylar = [{"ad": ad, "adet": n, "ortusuyor": ortusuyor_mu(sirket_adi, ad)}
               for ad, n in sorted(sayim.items(), key=lambda x: -x[1])]
    ortusen = [a for a in adaylar if a["ortusuyor"]]
    if not ortusen:
        return Olcum(
            None, OLCULEMEDI,
            gerekce=(f"'{sirket_adi}' icin donen sahip adlarinin hicbiri sirket "
                     f"adiyla ortusmuyor; eslesme dogrulanamadi."),
            ayrinti={"sorgu": sorgu, "adaylar": adaylar, "kaynak_kirilgan": True})

    return Olcum(float(len(ortusen)), OLCULDU,
                 ayrinti={"sorgu": sorgu, "adaylar": adaylar,
                          "dogrulanan_sahipler": [a["ad"] for a in ortusen],
                          "kaynak_kirilgan": True})
