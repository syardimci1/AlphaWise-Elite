"""Katman ablasyonu — hangi katman karari GERCEKTEN degistiriyor?

NEDEN BU OLCUM (madde 42, hiyerarsik surec)
===========================================
CrewAI gibi cercevelerde "hiyerarsik surec" fikri sudur: sabit bir boru
hatti yerine bir yonetici, hangi uzmanin cagrilacagina duruma gore karar
verir. AlphaWise'da MAA her karar icin BES katmanin hepsini cagirir.

Bu fikri benimsemenin sart olup olmadigi, once su soruyla olculur:
"Hangi katman, cagrilmasaydi karari degistirirdi?" Hicbir katman
degistirmiyorsa hiyerarsik secim gereksiz karmasiklik olur; bazi
katmanlar hicbir zaman belirleyici degilse, onlari kosullu cagirmak
gercek bir kazanctir.

BU MODUL KARAR YOLUNU DEGISTIRMEZ. maa/src/main.py KORUNMUSTUR ve ona
dokunulmamistir. Burada yapilan sey yalnizca GECMIS kayitlar uzerinde
olcumdur: her kayit, bir katman cikarilarak yeniden oynatilir.

DIKKAT — IKI FARKLI DEGISIM TURU
================================
Bir katmani cikarmak karari iki ayri yoldan degistirebilir:

  1. TOPLAM SKOR degisir ve esik asilir/asilmaz.
  2. GECERLI KATMAN SAYISI 3'un altina duser ve karar BEKLE olur.

Ikincisi katmanin "bilgi degeri" hakkinda bir sey SOYLEMEZ; yalnizca o
kayitta zaten sinirda olundugunu gosterir. Ikisini tek sayida toplamak
yaniltici olurdu; ayri ayri raporlanir.
"""
from __future__ import annotations

from karar_replay import KATMANLAR, REPLAY_EDILEBILIR, karar_uret, sema_sinifi


def _skorlar(kayit) -> dict | None:
    """Kayittan yalnizca katman skorlarini cikarir; replay edilemezse None."""
    ls = kayit.get("layer_scores")
    if sema_sinifi(ls) not in REPLAY_EDILEBILIR:
        return None
    return {k: v for k, v in ls.items() if k in KATMANLAR}


def tek_kayit_ablasyon(kayit) -> dict | None:
    """Bir kaydi her katman tek tek cikarilarak yeniden oynatir."""
    skorlar = _skorlar(kayit)
    if skorlar is None:
        return None
    taban = karar_uret(skorlar)
    sonuc = {}
    for kat in KATMANLAR:
        if kat not in skorlar:
            continue                     # kayitta zaten yok (eski 4 katmanli sema)
        eksik = {k: v for k, v in skorlar.items() if k != kat}
        y = karar_uret(eksik)
        degisti = y["karar"] != taban["karar"]
        # Degisimin NEDENI ayirt edilir: esik mi asildi, yeter sayi mi dustu?
        yeter_sayi_dustu = (taban["gecerli_katman"] >= 3 and
                            y["gecerli_katman"] < 3)
        sonuc[kat] = {
            "olculdu": skorlar[kat] is not None,
            "taban_karar": taban["karar"],
            "ablasyon_karar": y["karar"],
            "degisti": degisti,
            "yeter_sayi_dustu": yeter_sayi_dustu,
            "esik_kaymasi": degisti and not yeter_sayi_dustu,
        }
    return {"id": kayit.get("id"), "ticker": kayit.get("ticker"),
            "taban_karar": taban["karar"], "katmanlar": sonuc}


def toplu_ablasyon(kayitlar) -> dict:
    """Tum kayitlar icin katman bazinda etki ozeti."""
    tekil = [t for t in (tek_kayit_ablasyon(k) for k in (kayitlar or [])) if t]
    ozet = {kat: {"olculdugu_kayit": 0, "esik_kaymasi": 0,
                  "yeter_sayi_dustu": 0, "toplam_degisim": 0}
            for kat in KATMANLAR}
    for t in tekil:
        for kat, d in t["katmanlar"].items():
            o = ozet[kat]
            if d["olculdu"]:
                o["olculdugu_kayit"] += 1
            if d["esik_kaymasi"]:
                o["esik_kaymasi"] += 1
            if d["yeter_sayi_dustu"]:
                o["yeter_sayi_dustu"] += 1
            if d["degisti"]:
                o["toplam_degisim"] += 1
    for kat, o in ozet.items():
        n = o["olculdugu_kayit"]
        # Oran YALNIZCA katmanin gercekten olculdugu kayitlar uzerinden
        # hesaplanir. Katmanin None oldugu kayitlari paydaya koymak,
        # "etkisiz" gorunmesine yol acardi - oysa orada zaten yoktu.
        o["esik_kaymasi_orani"] = (round(o["esik_kaymasi"] / n * 100, 1)
                                   if n else None)
    return {
        "degerlendirilen_kayit": len(tekil),
        "katman_ozeti": ozet,
        "not": ("esik_kaymasi = katmanin bilgi degerinin isareti. "
                "yeter_sayi_dustu = kaydin zaten 3 katman sinirinda oldugunu "
                "gosterir, katman hakkinda bir sey soylemez. Oranlar yalnizca "
                "katmanin OLCULDUGU kayitlar uzerinden hesaplanir."),
    }
