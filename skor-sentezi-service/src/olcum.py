"""
Uc durumlu olcum tipi — bu servisin en onemli sozlesmesi.

NEDEN UC DURUM VAR
==================
Bu depoda 02.09.2026'da (commit 232d1a0) su hata kapatildi: SAA'nin DORT
ariza yolu da {"overall":"neutral","average_score":0.0} donuyordu; MAA bunu
gercek notrden ayiramiyor ve arizayi SAHTE KATMAN olarak sayiyordu. Duzeltme,
"olculemedi" ile "olculdu ve notr" ayrimini kurdu ve 16 testle kilitledi
(saa/tests/test_sozlesme.py).

Bes eksenli bir gorsel bu ayrimi BOZMAYA en musait yerdir: eksik bir ekseni
sifir uzunlukta cizmek, tam olarak o kapatilmis hatayi geri getirir. Bu
yuzden burada uc durum ayri ayri temsil edilir:

  OLCULDU     — veri vardi, hesaplandi. deger 0 olabilir; 0 GERCEK bir olcumdur.
  OLCULEMEDI  — veri yoktu/eksikti. deger None. Eksen CIZILMEZ, "veri yok" denir.
  UYGULANAMAZ — veri sorunu degil, olcut bu sirket turune YAPISAL olarak
                uymuyor. Ornegin Altman Z bankalara uygulanmaz (siniflandirilmis
                bilancolari yoktur: yfinance JPM icin Current Assets / Current
                Liabilities / EBIT kalemlerini HIC dondurmez). Bunu "olculemedi"
                saymak yaniltici olurdu: veri eksik degil, olcut yanlis.

UYGULANAMAZ ile OLCULEMEDI'yi ayirmak onemli, cunku ilki icin "yarin tekrar
dene" anlamsizdir; olcut o sirket icin hicbir zaman uygun olmayacaktir.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


OLCULDU = "olculdu"
OLCULEMEDI = "olculemedi"
UYGULANAMAZ = "uygulanamaz"


@dataclass(frozen=True)
class Olcum:
    """Tek bir olcutun sonucu.

    deger:        ham skor (Altman Z, Piotroski F, ...). durum != OLCULDU ise None.
    durum:        OLCULDU | OLCULEMEDI | UYGULANAMAZ
    gerekce:      neden olculemedi/uygulanamaz — kullaniciya gosterilecek metin
    eksik:        hangi kalemler bulunamadi (olculemedi durumunda)
    ayrinti:      ara degerler (X1..X5, F kriterleri gibi) — kanit odasi icin
    """
    deger: Optional[float]
    durum: str
    gerekce: str = ""
    eksik: tuple = ()
    ayrinti: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.durum not in (OLCULDU, OLCULEMEDI, UYGULANAMAZ):
            raise ValueError(f"gecersiz durum: {self.durum}")
        if self.durum == OLCULDU and self.deger is None:
            raise ValueError("OLCULDU durumunda deger None olamaz")
        if self.durum != OLCULDU and self.deger is not None:
            raise ValueError(f"{self.durum} durumunda deger None OLMALI "
                             f"(0 yazmak 'olculdu ve notr' anlamina gelir)")

    @property
    def var_mi(self) -> bool:
        return self.durum == OLCULDU

    def sozluk(self) -> dict:
        return {"deger": self.deger, "durum": self.durum, "gerekce": self.gerekce,
                "eksik": list(self.eksik), "ayrinti": self.ayrinti}


def olculdu(deger: float, **ayrinti) -> Olcum:
    return Olcum(deger=float(deger), durum=OLCULDU, ayrinti=ayrinti)


def olculemedi(gerekce: str, eksik=()) -> Olcum:
    return Olcum(deger=None, durum=OLCULEMEDI, gerekce=gerekce, eksik=tuple(eksik))


def uygulanamaz(gerekce: str) -> Olcum:
    return Olcum(deger=None, durum=UYGULANAMAZ, gerekce=gerekce)
