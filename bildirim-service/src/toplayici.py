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


def tekille(olaylar: list) -> list:
    """Ayni olayi iki kez gostermeyi engeller.

    NEDEN GEREKLI (canli kullanimda bulundu, 08.09.2026)
    ----------------------------------------------------
    Mutabakat alarmi HEM ALARM_godmode_paper.log'a HEM de gunluk
    godmode_paper_mutabakat_*.log dosyasina yaziliyor. Iki kaynak da
    okunmaya baslayinca ayni satir listede IKI KEZ gorundu ve sorun iki
    ayri olay gibi okundu.

    Tekillestirme (kaynak, zaman, mesaj) uclusune gore yapilir; ilk gorulen
    KORUNUR (siralama sonrasi cagrildiginda en onemli kopya kalir).
    """
    gorulen = set()
    cikti = []
    for o in olaylar:
        anahtar = (o.get("kaynak"), o.get("zaman"), o.get("mesaj"))
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        cikti.append(o)
    return cikti


def bayatlik_isaretle(olaylar: list, tum_kayitlar: list) -> list:
    """Bir alarmdan SONRA ayni kaynaktan normal kayit geldiyse bunu isaretler.

    NEDEN GEREKLI (canli kullanimda bulundu, 08.09.2026)
    ----------------------------------------------------
    Bildirim merkezi ilk calistiginda 01.09 tarihli bir "MUTABAKAT ALARMI:
    Defter ile broker AYRISIK" kaydini listenin basina koydu. Kayit gercekti,
    ama GECICIYDI: ayni gun 20:10'dan itibaren ve o gunden bu yana HER
    mutabakat kontrolu "MUTABAKAT TAMAM: defter=broker" diyor. Yani kullanici,
    bir hafta once kapanmis bir sorunu ACIK sanacakti.

    Otomatik "cozuldu" karari vermek kaynak-ozel bir mantik ister ve yanlis
    kapatma riski tasir. Bu yuzden burada YALNIZCA olgusal bir isaret konur:
    "bu alarmdan sonra ayni kaynaktan N normal kayit geldi". Yorumu kullanici
    yapar; alarm listeden SILINMEZ.
    """
    for o in olaylar:
        if not o.get("zaman"):
            o["sonraki_normal_kayit"] = None
            continue
        o["sonraki_normal_kayit"] = sum(
            1 for k in tum_kayitlar
            if k["kaynak"] == o["kaynak"] and k["duzey"] == BILGI
            and k.get("zaman") and k["zaman"] > o["zaman"])
    return olaylar


def yas_gun(zaman: Optional[str], simdi: Optional[str] = None) -> Optional[int]:
    """Olayin kac gun once oldugu. Cozulemeyen zaman icin None."""
    if not zaman:
        return None
    try:
        o = datetime.fromisoformat(zaman)
    except ValueError:
        return None
    s = datetime.fromisoformat(simdi) if simdi else datetime.now()
    return max(0, (s - o).days)


def desen_oku(kok: Path, desen: str, kaynak: str, bicim: str,
              yalnizca_alarm: bool = True, azami_dosya: int = 30) -> dict:
    """Gunluk DONDURULEN loglari (ornegin *_20260908.log) birlikte okur.

    NEDEN GEREKLI (canli kullanimda bulundu, 08.09.2026)
    ----------------------------------------------------
    Kagit islem otomasyonunun ALARM satirlari tek bir dosyada
    (ALARM_godmode_paper.log), "her sey yolunda" satirlari ise GUNLUK
    DONDURULEN ayri dosyalarda (godmode_paper_mutabakat_YYYYMMDD.log)
    tutuluyor. Yalnizca alarm dosyasini okuyunca bayatlik hesabi her alarm
    icin "sonraki normal kayit: 0" veriyordu — yani bir hafta once kapanmis
    MUTABAKAT sorunu hala ACIK gibi gorunuyordu. Kapanis kaydi baska
    dosyadaydi.
    """
    try:
        dosyalar = sorted(kok.glob(desen))[-azami_dosya:]
    except OSError as e:
        return {"kaynak": kaynak, "yol": f"{kok}/{desen}", "durum": "okunamadi",
                "gerekce": f"Desen taranamadı ({type(e).__name__}). "
                           f"ALARM OLMADIĞI ANLAMINA GELMEZ.", "olaylar": []}
    if not dosyalar:
        return {"kaynak": kaynak, "yol": f"{kok}/{desen}", "durum": "kaynak_yok",
                "gerekce": "Desene uyan dosya bulunamadı.", "olaylar": []}
    olaylar, okunamayan = [], 0
    for d in dosyalar:
        s = kaynak_oku(d, kaynak, bicim, yalnizca_alarm)
        if s["durum"] != "okundu":
            okunamayan += 1
            continue
        olaylar.extend(s["olaylar"])
    if okunamayan and not olaylar:
        return {"kaynak": kaynak, "yol": f"{kok}/{desen}", "durum": "okunamadi",
                "gerekce": f"{okunamayan} dosya okunamadı. "
                           f"ALARM OLMADIĞI ANLAMINA GELMEZ.", "olaylar": []}
    return {"kaynak": kaynak, "yol": f"{kok}/{desen}",
            "durum": "okundu" if not okunamayan else "kismen_okundu",
            "gerekce": "" if not okunamayan else
                       f"{okunamayan} dosya okunamadı; liste EKSIK olabilir.",
            "olaylar": olaylar, "dosya_sayisi": len(dosyalar)}


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
    # "kismen_okundu" da guvenilir sessizligi BOZAR: liste eksik olabilir.
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
