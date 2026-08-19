"""
Kurum adi -> 13F dosyalayici (filer) eslestirme katmani.

NEDEN GEREKLI:
LLMQuant'in /by-ticker endpoint'i yalnizca ILGILI CEYREGIN Top-1000 yonetici
kumesini dondurur. Bir yonetici o ceyrek icin henuz 13F vermediyse kumeye
girmez ve by-ticker sonucunda HIC gorunmez.

Gercek ornek (18.08.2026 dogrulandi): VANGUARD GROUP INC (CIK 102909) en son
2025-12-31 icin dosyalamistir; 2026-03-31 Top-1000 kumesinde YOKTUR. Bu yuzden
by-ticker NVDA sonucunda Vanguard cikmaz - ama /by-manager?manager_cik=102909
sorgusu pozisyonu eksiksiz dondurur.

Bu modul, bilinen amiral-gemisi dosyalayicilarin SEC CIK numaralarini sabitler
ki "Vanguard" sorgusu her zaman dogru tuzel kisiye cozulsun.
"""

# Bilinen buyuk kurumlarin resmi SEC CIK numaralari (kalici, halka acik).
AMIRAL_GEMILERI = {
    "vanguard": [("102909", "VANGUARD GROUP INC")],
    "blackrock": [("2012383", "BlackRock, Inc.")],
    "state street": [("93751", "STATE STREET CORP")],
    "fidelity": [("315066", "FMR LLC")],
    "fmr": [("315066", "FMR LLC")],
    "geode": [("1214717", "GEODE CAPITAL MANAGEMENT, LLC")],
    "berkshire": [("1067983", "BERKSHIRE HATHAWAY INC")],
    "norges": [("1374170", "NORGES BANK")],
    "jpmorgan": [("19617", "JPMORGAN CHASE & CO")],
    "goldman": [("886982", "GOLDMAN SACHS GROUP INC")],
    "morgan stanley": [("895421", "MORGAN STANLEY")],
    "northern trust": [("73124", "NORTHERN TRUST CORP")],
    "citadel": [("1423053", "CITADEL ADVISORS LLC")],
    "renaissance": [("1037389", "RENAISSANCE TECHNOLOGIES LLC")],
    "bridgewater": [("1350694", "BRIDGEWATER ASSOCIATES, LP")],
    "two sigma": [("1179392", "TWO SIGMA INVESTMENTS, LP")],
    "millennium": [("1273087", "MILLENNIUM MANAGEMENT LLC")],
    "point72": [("1603466", "POINT72 ASSET MANAGEMENT, L.P.")],
    "tiger global": [("1167483", "TIGER GLOBAL MANAGEMENT LLC")],
    "soros": [("1029160", "SOROS FUND MANAGEMENT LLC")],
    "invesco": [("914208", "INVESCO LTD.")],
    "schwab": [("1006249", "CHARLES SCHWAB INVESTMENT MANAGEMENT INC")],
    "ubs": [("1610520", "UBS Group AG")],
    "wellington": [("902219", "WELLINGTON MANAGEMENT GROUP LLP")],
    "t. rowe": [("1113169", "PRICE T ROWE ASSOCIATES INC /MD/")],
    "t rowe": [("1113169", "PRICE T ROWE ASSOCIATES INC /MD/")],
}


def _normalize(s: str) -> str:
    return " ".join((s or "").lower().split())


def amiral_gemisi_adaylari(sorgu: str):
    """Sorguyla eslesen bilinen amiral-gemisi CIK'lerini dondurur."""
    q = _normalize(sorgu)
    if not q:
        return []
    bulunan = []
    for anahtar, kayitlar in AMIRAL_GEMILERI.items():
        if anahtar in q or q in anahtar:
            for cik, ad in kayitlar:
                bulunan.append({"manager_cik": cik, "manager_name": ad, "kaynak": "amiral_gemisi_haritasi"})
    return bulunan


def kume_icinde_ara(sorgu: str, yoneticiler: list):
    """
    Top-1000 kapsanan yonetici kumesinde ad ve alias uzerinden
    kismi, buyuk-kucuk harf duyarsiz eslesme yapar.
    """
    q = _normalize(sorgu)
    if not q:
        return []
    eslesenler = []
    for y in yoneticiler or []:
        ad = _normalize(y.get("manager_name", ""))
        aliases = [_normalize(a) for a in (y.get("aliases") or [])]
        if q in ad or any(q == a or q in a for a in aliases):
            eslesenler.append(
                {
                    "manager_cik": str(y.get("manager_cik")),
                    "manager_name": y.get("manager_name"),
                    "period_rank": y.get("period_rank"),
                    "kaynak": "kapsanan_kume",
                }
            )
    return eslesenler


def adaylari_birlestir(sorgu: str, yoneticiler: list):
    """
    Amiral gemisi haritasi + kapsanan kume sonuclarini CIK bazinda tekillestirir.
    Amiral gemileri listenin basina konur (en alakali tuzel kisi).
    """
    adaylar = amiral_gemisi_adaylari(sorgu) + kume_icinde_ara(sorgu, yoneticiler)
    gorulen = set()
    sonuc = []
    for a in adaylar:
        cik = str(a.get("manager_cik"))
        if cik in gorulen:
            continue
        gorulen.add(cik)
        sonuc.append(a)
    return sonuc
