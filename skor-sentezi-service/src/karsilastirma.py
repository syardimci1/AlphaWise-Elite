"""
Sektor-normalize rakip karsilastirmasi (Madde 24).

NEDEN SEKTOR NORMALIZASYONU
===========================
Ham skorlar sektorler arasinda karsilastirilamaz. Altman Z = 3.0 bir yazilim
sirketi icin siradan, sermaye yogun bir uretici icin cok iyidir; Piotroski'nin
"brut marj artti" olcutu perakendede farkli, ilacta farkli anlam tasir. Bu
yuzden mutlak puan degil, AYNI SEKTORDEKI DAGILIM ICINDEKI KONUM raporlanir.

EN KRITIK KURAL — OLCULEMEYEN RAKIP DAGILIMA GIRMEZ
===================================================
Bir rakibin ekseni olculemediyse o rakip, o eksenin dagilimindan CIKARILIR.
Sifir olarak sayilsaydi, verisi eksik rakipler hedef sirketi yapay olarak
yukari tasirdi — depoda 232d1a0 ile kapatilan "olculemedi = notr" hatasinin
istatistiksel bicimi. Bu modul, her eksen icin KAC rakiple hesaplandigini
ayrica bildirir.

ASGARI RAKIP SAYISI
===================
Uc rakiple hesaplanan bir yuzdelik sira anlamli degildir; "en iyi %25" gibi
bir ifade dort sirketlik bir kumede sahte kesinlik uretir. Asgari sayinin
altinda sonuc URETILMEZ, "yeterli rakip yok" denir.
"""
from __future__ import annotations
from typing import Optional

ASGARI_RAKIP = 5


def yuzdelik_sira(deger: float, digerleri: list) -> float:
    """Hedefin dagilim icindeki konumu, 0-100.

    Tanim: kendisinden DUSUK olanlarin orani + esitlerin YARISI (orta sira
    yontemi). Esitleri yarim saymak, ayni degere sahip sirketlerin hepsinin
    birden "en ust" veya "en alt" gorunmesini engeller.
    """
    if not digerleri:
        raise ValueError("bos dagilimda yuzdelik sira tanimsiz")
    n = len(digerleri)
    dusuk = sum(1 for d in digerleri if d < deger)
    esit = sum(1 for d in digerleri if d == deger)
    return 100.0 * (dusuk + 0.5 * esit) / n


def medyan(degerler: list) -> Optional[float]:
    if not degerler:
        return None
    s = sorted(degerler)
    n = len(s)
    orta = n // 2
    return float(s[orta]) if n % 2 else (s[orta - 1] + s[orta]) / 2.0


def eksen_karsilastir(hedef_puan: Optional[float], rakip_puanlar: list,
                      asgari: int = ASGARI_RAKIP) -> dict:
    """Tek bir eksen icin sektor konumu.

    rakip_puanlar listesi None ICEREBILIR; None'lar (olculemeyen rakipler)
    dagilimdan CIKARILIR, sifir sayilmaz.
    """
    gecerli = [p for p in rakip_puanlar if isinstance(p, (int, float))]
    sonuc = {
        "rakip_sayisi": len(gecerli),
        "olculemeyen_rakip": len(rakip_puanlar) - len(gecerli),
        "medyan": medyan(gecerli),
    }
    if hedef_puan is None:
        sonuc.update({"durum": "hedef_olculemedi", "yuzdelik": None,
                      "gerekce": "Hedef sirketin bu ekseni ölçülemedi; "
                                 "sektör konumu hesaplanamaz."})
        return sonuc
    if len(gecerli) < asgari:
        sonuc.update({"durum": "yetersiz_rakip", "yuzdelik": None,
                      "gerekce": f"Bu eksende yalnızca {len(gecerli)} rakip "
                                 f"ölçülebildi; anlamlı bir sektör konumu için "
                                 f"en az {asgari} gerekiyor."})
        return sonuc
    sonuc.update({"durum": "olculdu",
                  "yuzdelik": round(yuzdelik_sira(hedef_puan, gecerli), 1),
                  "gerekce": ""})
    return sonuc


def sektor_karsilastir(hedef: dict, rakipler: list,
                       asgari: int = ASGARI_RAKIP) -> dict:
    """hedef ve rakipler: sentezle() ciktisi bicimindeki sozlukler."""
    hedef_eksen = {e["anahtar"]: e for e in hedef.get("eksenler", [])}
    cikti = []
    for anahtar, e in hedef_eksen.items():
        rakip_puanlar = []
        for r in rakipler:
            eslesen = next((x for x in r.get("eksenler", [])
                            if x["anahtar"] == anahtar), None)
            rakip_puanlar.append(eslesen.get("puan") if eslesen else None)
        k = eksen_karsilastir(e.get("puan"), rakip_puanlar, asgari)
        cikti.append({"anahtar": anahtar, "ad": e.get("ad"),
                      "puan": e.get("puan"), "durum": e.get("durum"), **k})

    # Genel konum: yalnizca sektor konumu OLCULEBILEN eksenlerin ortalamasi.
    olculen = [c["yuzdelik"] for c in cikti if c["durum"] == "olculdu"]
    if len(olculen) < 3:
        genel = None
        genel_gerekce = (f"Genel sektör konumu üretilmedi: {len(olculen)} eksende "
                         "konum hesaplanabildi, en az 3 gerekiyor. "
                         "Eksik ölçüm sıfır olarak sayılmaz.")
    else:
        genel = round(sum(olculen) / len(olculen), 1)
        genel_gerekce = (f"{len(olculen)} eksende hesaplanan sektör konumunun "
                         "düz ortalaması.")
    return {
        "ticker": hedef.get("ticker"),
        "sektor": hedef.get("sektor"),
        "rakip_sayisi": len(rakipler),
        "eksenler": cikti,
        "genel_yuzdelik": genel,
        "genel_gerekce": genel_gerekce,
        "asgari_rakip": asgari,
    }
