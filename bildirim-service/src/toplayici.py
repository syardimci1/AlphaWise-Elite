"""
Bildirim merkezi — dagilmis ALARM kayitlarini tek bicime indirger (Madde 28).

SORUN
=====
Sistemde alarm uretimi VAR ama gorunurlugu YOK. Uc ayri bicimde, dort ayri
dosyada birikiyor ve kimse bakmadikca hicbir yerde gorunmuyor:
  * ALARM_watchdog.log        -> "[Sun Aug 16 21:33:20 CEST 2026] ALARM: ..."
  * ALARM_godmode_paper.log   -> "[2026-09-03 03:45:37+0200] ALARM: ..."
  * oz_iyilestirme_bekcisi.jsonl -> yapilandirilmis JSONL
  * otonom_bekci.log          -> "[2026-09-06 01:35:01] [ana:claude1] OK: ..."

EN KRITIK KURAL — "ALARM YOK" ILE "BAKAMADIM" AYNI GORUNEMEZ
============================================================
Bir bildirim merkezinde bu ayrimin kaybolmasi, sistemdeki en tehlikeli
sessiz hatadir: kaynak okunamadigi icin bos donen bir liste, kullaniciya
"her sey yolunda" diye gorunur. Bu yuzden her kaynak icin AYRI bir durum
raporlanir (okundu / okunamadi / kaynak_yok) ve arayuz bunu gostermek
zorundadir. Ayni ilke bu depoda 232d1a0 ile veri katmaninda kurulmustu;
burada uyari katmanina tasiniyor.
"""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Duzeyler siddet sirasina gore.
KRITIK, ALARM, UYARI, BILGI = "kritik", "alarm", "uyari", "bilgi"
DUZEY_SIRASI = {KRITIK: 0, ALARM: 1, UYARI: 2, BILGI: 3}

_KOSELI_TARIH = re.compile(r"^\[([^\]]+)\]\s*(.*)$")

# "Sun Aug 16 21:33:20 CEST 2026" bicimi icin ay adlari.
_AYLAR = {a: i for i, a in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def zaman_coz(ham: str) -> Optional[str]:
    """Uc ayri tarih bicimini de ISO'ya cevirir; cozemezse None DONER
    (uydurma zaman damgasi ATMAZ)."""
    ham = ham.strip()
    # 1) 2026-09-03 03:45:37+0200  /  2026-09-06 01:35:01
    m = re.match(r"^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})", ham)
    if m:
        return f"{m.group(1)}T{m.group(2)}"
    # 2) Sun Aug 16 21:33:20 CEST 2026
    m = re.match(r"^\w{3}\s+(\w{3})\s+(\d{1,2})\s+(\d{2}:\d{2}:\d{2})\s+\S+\s+(\d{4})$", ham)
    if m:
        ay = _AYLAR.get(m.group(1))
        if ay:
            return f"{m.group(4)}-{ay:02d}-{int(m.group(2)):02d}T{m.group(3)}"
    return None


def duzey_belirle(mesaj: str) -> str:
    m = mesaj.upper()
    if "KRITIK ALARM" in m or "KRİTİK ALARM" in m:
        return KRITIK
    if "ALARM" in m:
        return ALARM
    if "UYARI" in m:
        return UYARI
    return BILGI


def koseli_log_coz(metin: str, kaynak: str, yalnizca_alarm: bool = True) -> list:
    """'[zaman] mesaj' bicimindeki duz metin loglari."""
    olaylar = []
    for satir in metin.splitlines():
        satir = satir.strip()
        if not satir:
            continue
        m = _KOSELI_TARIH.match(satir)
        if not m:
            continue
        zaman = zaman_coz(m.group(1))
        mesaj = m.group(2).strip()
        duzey = duzey_belirle(mesaj)
        if yalnizca_alarm and duzey == BILGI:
            continue
        olaylar.append({"kaynak": kaynak, "zaman": zaman, "duzey": duzey,
                        "mesaj": mesaj, "ham": satir})
    return olaylar


def jsonl_coz(metin: str, kaynak: str, yalnizca_alarm: bool = True) -> list:
    """Yapilandirilmis JSONL (oz-iyilestirme bekcisi)."""
    olaylar = []
    for satir in metin.splitlines():
        satir = satir.strip()
        if not satir:
            continue
        try:
            k = json.loads(satir)
        except json.JSONDecodeError:
            continue
        if not isinstance(k, dict):
            continue
        saglikli = k.get("saglikli")
        if saglikli is False:
            duzey = KRITIK if k.get("ardisik_basarisiz", 0) >= 3 else ALARM
        elif k.get("oneri_sayisi"):
            duzey = UYARI
        else:
            duzey = BILGI
        if yalnizca_alarm and duzey == BILGI:
            continue
        parcalar = [f"olay={k.get('olay')}"]
        if k.get("cikti"):
            parcalar.append(str(k["cikti"]))
        if k.get("not"):
            parcalar.append(str(k["not"]))
        if k.get("yeniden_baslatildi"):
            parcalar.append("yeniden baslatildi")
        olaylar.append({"kaynak": kaynak, "zaman": zaman_coz(str(k.get("zaman", ""))),
                        "duzey": duzey, "mesaj": " | ".join(parcalar), "ham": satir})
    return olaylar


def kaynak_oku(yol: Path, kaynak: str, bicim: str,
               yalnizca_alarm: bool = True, azami_satir: int = 2000) -> dict:
    """Tek bir kaynagi okur. SONUC HER ZAMAN bir DURUM tasir."""
    if not yol.exists():
        return {"kaynak": kaynak, "yol": str(yol), "durum": "kaynak_yok",
                "gerekce": "Dosya bulunamadı; bu kaynak hiç yazılmamış olabilir.",
                "olaylar": []}
    try:
        satirlar = yol.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as e:
        return {"kaynak": kaynak, "yol": str(yol), "durum": "okunamadi",
                "gerekce": f"Dosya okunamadı ({type(e).__name__}). "
                           f"ALARM OLMADIĞI ANLAMINA GELMEZ.",
                "olaylar": []}
    metin = "\n".join(satirlar[-azami_satir:])
    cozucu = jsonl_coz if bicim == "jsonl" else koseli_log_coz
    return {"kaynak": kaynak, "yol": str(yol), "durum": "okundu",
            "gerekce": "", "olaylar": cozucu(metin, kaynak, yalnizca_alarm)}


def sirala(olaylar: list) -> list:
    """Once siddet, sonra en yeni. Zamani cozulemeyen olay EN SONA gider ama
    ATILMAZ — atmak, bir alarmi sessizce yok etmek olurdu."""
    return sorted(olaylar, key=lambda o: (DUZEY_SIRASI.get(o["duzey"], 9),
                                          o["zaman"] is None,
                                          "" if o["zaman"] is None else
                                          _ters(o["zaman"])))


def _ters(s: str) -> str:
    """Azalan siralama icin dizgeyi tersine cevirir (en yeni once)."""
    return "".join(chr(0x10FFFD - ord(c)) if ord(c) < 0x10FFFD else c for c in s)


def ozet(kaynak_sonuclari: list) -> dict:
    tum = [o for k in kaynak_sonuclari for o in k["olaylar"]]
    sayim = {d: sum(1 for o in tum if o["duzey"] == d)
             for d in (KRITIK, ALARM, UYARI, BILGI)}
    okunamayan = [k for k in kaynak_sonuclari if k["durum"] != "okundu"]
    return {
        "toplam_olay": len(tum),
        "duzey_sayimi": sayim,
        "kaynak_sayisi": len(kaynak_sonuclari),
        "okunamayan_kaynak": len(okunamayan),
        # UC DURUMLU: alan yalnizca liste BOSKEN anlamlidir.
        #   True  -> liste bos VE tum kaynaklar okundu: "alarm yok" denebilir.
        #   False -> liste bos AMA bir kaynak okunamadi: "alarm yok" DENEMEZ.
        #   None  -> liste bos degil; soru zaten gecersiz.
        # Ilk surum olay VARKEN de False donuyordu ve ciktida "SESSIZLIK
        # GUVENILIR MI: False" satiri, sanki bir sorun varmis gibi okunuyordu.
        "sessiz_mi": len(tum) == 0,
        "guvenilir_sessizlik": (None if tum else not okunamayan),
        "uyari_metni": (
            "" if not okunamayan else
            f"{len(okunamayan)} kaynak okunamadı. Listenin boş olması "
            f"'alarm yok' anlamına GELMEZ."),
    }
