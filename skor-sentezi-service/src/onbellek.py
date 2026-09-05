"""
Skor onbellegi ve kendiliginden buyuyen sektor indeksi.

NEDEN ONBELLEK
==============
Bes eksen hesabi tek sirket icin dort mali tablo + ^TNX cekiyor; olculen
sure 20-40 saniye. Rakip karsilastirmasi 5-10 sirket demek, yani onbelleksiz
tek istek dakikalarca surer ve Yahoo'yu gereksiz yorar. Mali tablolar UC AYDA
BIR degistigi icin 24 saatlik bir yasam suresi fazlasiyla guvenlidir.

NEDEN DOSYA, REDIS DEGIL
========================
Ayni agda alphawise-redis var, ama yeni bir baglanti/yapilandirma bagimliligi
eklemek bu servisi tek basina calisamaz hale getirirdi. Dosya onbellegi
bagimlilik gerektirmez ve adlandirilmis Docker birimiyle kalici olur.

SEKTOR INDEKSI — KENDILIGINDEN BUYUR
====================================
Sistemde sektor bilgisi tutan HICBIR kaynak yok (olculdu: depoda sector/sektor
alani olan bir servis bulunmuyor) ve qlib'deki 6.732 sembolun tamamini
yfinance'a sormak hem saatler surer hem de kaba olurdu. Bunun yerine indeks,
SORULAN her sirketle kendiliginden buyur: /skor cagrisi sonucu onbellege
yazilirken sektoru de yazilir. Indekste yeterli rakip yoksa bu ACIKCA
soylenir; uydurma rakip listesi URETILMEZ.
"""
from __future__ import annotations
import json, os, time
from pathlib import Path
from typing import Optional

ONBELLEK_DIZIN = Path(os.environ.get("ONBELLEK_DIZIN", "/app/onbellek"))
YASAM_SURESI_SN = int(os.environ.get("ONBELLEK_YASAM_SN", str(24 * 3600)))


def _yol(ticker: str) -> Path:
    # Ticker zaten uc noktada dogrulaniyor; yine de dosya adi olarak
    # kullanmadan once sertlestiriyoruz (yol asimi tek satirlik bir hata
    # olmamali).
    guvenli = "".join(c for c in ticker.upper() if c.isalnum() or c in ".-")
    # Nokta dizileri temizlenir ve bastaki nokta/tire atilir. Egik cizgi zaten
    # suzuldugu icin yol asimi mumkun degildi, ama "..", "." veya bos bir ad
    # dosya sistemine gore farkli davranabilir; ad TEK BIR bicime indirgenir.
    while ".." in guvenli:
        guvenli = guvenli.replace("..", ".")
    guvenli = guvenli.strip(".-")
    if not guvenli:
        guvenli = "GECERSIZ"
    return ONBELLEK_DIZIN / f"{guvenli}.json"


def yaz(ticker: str, veri: dict) -> None:
    try:
        ONBELLEK_DIZIN.mkdir(parents=True, exist_ok=True)
        gecici = _yol(ticker).with_suffix(".json.tmp")
        gecici.write_text(json.dumps({"zaman": time.time(), "veri": veri},
                                     ensure_ascii=False), encoding="utf-8")
        # Atomik yer degistirme: yarim yazilmis bir dosya asla okunmaz.
        gecici.replace(_yol(ticker))
    except OSError:
        pass  # onbellek yazilamamasi ISLEVI DUSURMEZ, yalnizca yavaslatir


def oku(ticker: str, yasam_sn: Optional[int] = None) -> Optional[dict]:
    yasam = YASAM_SURESI_SN if yasam_sn is None else yasam_sn
    p = _yol(ticker)
    if not p.exists():
        return None
    try:
        kayit = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(kayit, dict) or "zaman" not in kayit:
        return None
    if time.time() - float(kayit["zaman"]) > yasam:
        return None
    return kayit.get("veri")


def tum_kayitlar(yasam_sn: Optional[int] = None) -> list:
    yasam = YASAM_SURESI_SN if yasam_sn is None else yasam_sn
    if not ONBELLEK_DIZIN.exists():
        return []
    cikti = []
    for p in sorted(ONBELLEK_DIZIN.glob("*.json")):
        try:
            kayit = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(kayit, dict) or "zaman" not in kayit:
            continue
        if time.time() - float(kayit["zaman"]) > yasam:
            continue
        veri = kayit.get("veri")
        if isinstance(veri, dict) and veri.get("ticker"):
            cikti.append(veri)
    return cikti


def sektor_indeksi(yasam_sn: Optional[int] = None) -> dict:
    """{sektor: [ticker, ...]} — yalnizca onbellekte GERCEKTEN olan sirketler."""
    indeks: dict = {}
    for v in tum_kayitlar(yasam_sn):
        s = v.get("sektor")
        if not s:
            continue
        indeks.setdefault(s, []).append(v["ticker"])
    return {k: sorted(set(v)) for k, v in indeks.items()}


def sektordeki_rakipler(ticker: str, sektor: Optional[str],
                        yasam_sn: Optional[int] = None) -> list:
    """Hedefin KENDISI haric, ayni sektorde onbellekte bulunan sirketler."""
    if not sektor:
        return []
    return [t for t in sektor_indeksi(yasam_sn).get(sektor, [])
            if t.upper() != ticker.upper()]
