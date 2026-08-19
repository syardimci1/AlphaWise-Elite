"""
Kurum adi -> SEC CIK haritasi (bu servisin KENDI kopyasi).

KAYNAK NOTU: Bu liste institution-filter-service/src/resolver.py'deki
AMIRAL_GEMILERI haritasindan KOPYALANMISTIR. O dosya SADECE OKUNDU,
degistirilmedi. Bu servis institution-filter-service'e hicbir bagimlilik
tasimaz; kendi kopyasiyla bagimsiz calisir.

CIK numaralari SEC'in kalici, halka acik tanimlayicilaridir.

=======================================================================
BLACKROCK UYARISI - DOGRULANMIS BULGU (2026-08-19)
=======================================================================
"BlackRock" adi altinda iki ayri dosyalayici tuzel kisi vardir:

  CIK 2012383  "BlackRock, Inc."          -> GUNCEL. Son 13F-HR:
                                             2026-08-07 (donem 2026-06-30)
  CIK 1364742  "BlackRock Finance, Inc."  -> ESKI. Son 13F-HR:
                                             2024-08-13 (donem 2024-06-30)

Ikisi de data.sec.gov'da canli dogrulandi. 1364742 ile sorgu yapan bir
sistem 2024'te DONMUS veri alir ve bunu fark etmez. Bu yuzden "blackrock"
anahtari 2012383'e cozulur; 1364742 ayri bir anahtar olarak
("blackrock_finance") tutulur ki tarihsel sorgu isteyen bilincli olarak
secebilsin.
"""

# ad -> [(cik, resmi_ad)]
AMIRAL_GEMILERI = {
    "vanguard": [("102909", "VANGUARD GROUP INC")],
    "blackrock": [("2012383", "BlackRock, Inc.")],
    "blackrock_finance": [("1364742", "BlackRock Finance, Inc.")],
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


def coz(sorgu: str):
    """
    Kurum adini CIK'e cozer. Tam eslesme once, sonra parcali eslesme.
    Donen: [{"cik": str, "ad": str}] — bos liste = cozulemedi.
    """
    q = _normalize(sorgu)
    if not q:
        return []

    # 1) tam eslesme
    if q in AMIRAL_GEMILERI:
        return [{"cik": c, "ad": a} for c, a in AMIRAL_GEMILERI[q]]

    # 2) sorgu bir anahtari iceriyor mu (ya da tersi)
    bulunan, gorulen = [], set()
    for anahtar, kayitlar in AMIRAL_GEMILERI.items():
        if anahtar in q or q in anahtar:
            for c, a in kayitlar:
                if c not in gorulen:
                    gorulen.add(c)
                    bulunan.append({"cik": c, "ad": a})
    return bulunan


def cik_normalize(cik: str) -> str:
    """SEC submissions API 10 haneli sifir dolgulu CIK ister."""
    return str(cik).strip().lstrip("0").zfill(10)


def tum_kurumlar():
    """Tekil (cik, ad) listesi — alias'lar tekillestirilmis."""
    gorulen, out = set(), []
    for kayitlar in AMIRAL_GEMILERI.values():
        for c, a in kayitlar:
            if c not in gorulen:
                gorulen.add(c)
                out.append({"cik": c, "ad": a})
    return out
