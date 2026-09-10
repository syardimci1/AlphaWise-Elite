"""Karar isabeti — sansla ayirt edilemeyen bir oran RAPORLANMAZ.

NEDEN (madde 47, TradingGoose referansi)
========================================
TradingGoose gibi cok ajanli sistemlerin ayirt edici fikri "yansima"dir:
gecmis kararlarin sonucu olculur ve yeni kararlara geri beslenir.
AlphaWise'da olcum ZATEN var (decision_log.was_correct, /evaluate-decisions,
/performance-report) — ama olculdu: /performance-report ucunu HICBIR
tuketici cagirmiyor. Yani halka olculuyor ama kapanmiyor.

Halkayi kapatmadan once oranin KENDISININ anlamli olmasi gerekir. Iki
sorun olculdu:

1. TUT OLCUTU NEREDEYSE HER ZAMAN SAGLANIYOR
   Kural (maa/src/main.py): TUT dogru sayilir eger |getiri| < %15.
   Gercek fiyatlarla olculdu (12 sembol x 30 gunluk 360 pencere):
       TUT olcutunun TABAN orani  = %71,9
       EKLE olcutunun (r>0) tabani = %41,1
   Yani "TUT kararlarinin %100'u dogru" cumlesi tek basina hicbir sey
   soylemez; hicbir bilgisi olmayan bir sistem de ~%72 alirdi.

2. ORNEK SAYISI COK KUCUK
   102 katman-tabanli kararin yalnizca 12'si degerlendirilmis
   (7 EKLE, 5 TUT). 4/7 = %57 ile %41 taban arasindaki fark, n=7'de
   sanstan ayirt EDILEMEZ.

BU MODULUN KURALI
=================
Gozlenen oran, guven araligi TABAN ORANI ICERIYORSA "sanstan ayirt
edilemedi" olarak raporlanir. Bu bir basarisizlik degil, olcumun
durumudur - ve gizlenmesi, sistemin kendini oldugundan iyi gostermesi
demek olurdu.

Guven araligi Wilson yontemiyle hesaplanir; normal yaklasim (p +- z*se)
kucuk orneklerde ve uc oranlarda (0/5 gibi) sifir genislikte aralik
uretir ve yaniltir.
"""
from __future__ import annotations

import math

# %95 icin normal dagilimin z degeri.
Z95 = 1.959963984540054

# Bu esigin altinda oran hic raporlanmaz — aralik zaten her seyi icerir.
ASGARI_ORNEK = 5


def wilson_araligi(basari: int, toplam: int, z: float = Z95) -> tuple:
    """Wilson skor araligi (alt, ust), 0-1 olceginde.

    Normal yaklasimin aksine 0/n ve n/n durumlarinda da anlamli
    (sifir genislikte olmayan) aralik uretir.
    """
    if toplam <= 0:
        raise ValueError("toplam pozitif olmali")
    if not 0 <= basari <= toplam:
        raise ValueError(f"basari 0..{toplam} araliginda olmali, {basari} geldi")
    p = basari / toplam
    z2 = z * z
    payda = 1.0 + z2 / toplam
    merkez = (p + z2 / (2 * toplam)) / payda
    yari = (z / payda) * math.sqrt(p * (1 - p) / toplam
                                   + z2 / (4 * toplam * toplam))
    return max(0.0, merkez - yari), min(1.0, merkez + yari)


def isabet_degerlendir(basari: int, toplam: int, taban_orani: float,
                       olcut_aciklamasi: str = "") -> dict:
    """Bir karar kodunun isabetini TABANLA karsilastirarak degerlendirir.

    taban_orani: bilgisiz bir sistemin ayni olcutu saglama orani (0-1).
    """
    if toplam < 0 or basari < 0 or basari > max(toplam, 0):
        return _olculemedi("gecersiz sayimlar", basari, toplam, taban_orani)
    if toplam < ASGARI_ORNEK:
        return _olculemedi(
            f"degerlendirilen karar sayisi {toplam}; anlamli bir oran icin "
            f"en az {ASGARI_ORNEK} gerekli", basari, toplam, taban_orani)
    if not 0.0 <= taban_orani <= 1.0:
        return _olculemedi(f"taban orani 0-1 araliginda olmali: {taban_orani}",
                           basari, toplam, taban_orani)

    oran = basari / toplam
    alt, ust = wilson_araligi(basari, toplam)
    taban_icerde = alt <= taban_orani <= ust
    if taban_icerde:
        yargi = "sanstan_ayirt_edilemedi"
        aciklama = (f"Gozlenen oran %{oran*100:.1f}, %95 guven araligi "
                    f"[%{alt*100:.1f}, %{ust*100:.1f}] TABAN ORANI "
                    f"%{taban_orani*100:.1f}'i iceriyor. Bu sonuc, bilgisi "
                    f"olmayan bir sistemin sonucundan AYIRT EDILEMEZ.")
    elif alt > taban_orani:
        yargi = "tabanin_ustunde"
        aciklama = (f"Gozlenen oran %{oran*100:.1f}, guven araligi tamamen "
                    f"taban orani %{taban_orani*100:.1f}'in USTUNDE.")
    else:
        yargi = "tabanin_altinda"
        aciklama = (f"Gozlenen oran %{oran*100:.1f}, guven araligi tamamen "
                    f"taban orani %{taban_orani*100:.1f}'in ALTINDA.")
    return {
        "olculdu": True,
        "basari": basari, "toplam": toplam,
        "oran": round(oran, 4),
        "guven_araligi": [round(alt, 4), round(ust, 4)],
        "taban_orani": round(taban_orani, 4),
        "yargi": yargi,
        "aciklama": aciklama,
        "olcut": olcut_aciklamasi,
    }


def _olculemedi(neden, basari, toplam, taban):
    return {
        "olculdu": False,
        "basari": basari, "toplam": toplam,
        "oran": None, "guven_araligi": None,
        "taban_orani": taban if isinstance(taban, (int, float)) else None,
        "yargi": "olculemedi",
        "aciklama": neden,
        "olcut": "",
    }


def taban_orani_olc(kapanislar, ufuk: int, olcut) -> dict:
    """Gercek fiyat serisinden bir olcutun TABAN oranini olcer.

    kapanislar: {sembol: [kapanis, ...]}
    olcut: getiri -> bool
    """
    basari = toplam = 0
    sembol_bazinda = {}
    for s, k in (kapanislar or {}).items():
        if not k or len(k) <= ufuk:
            sembol_bazinda[s] = None          # olculemedi, sifir DEGIL
            continue
        b = t = 0
        for i in range(len(k) - ufuk):
            if k[i] == 0:
                continue
            r = (k[i + ufuk] - k[i]) / k[i]
            t += 1
            if olcut(r):
                b += 1
        sembol_bazinda[s] = round(b / t, 4) if t else None
        basari += b
        toplam += t
    if toplam == 0:
        return {"olculdu": False, "taban_orani": None, "ornek": 0,
                "sembol_bazinda": sembol_bazinda,
                "aciklama": "hicbir sembolde yeterli bar yok"}
    return {
        "olculdu": True,
        "taban_orani": round(basari / toplam, 4),
        "ornek": toplam,
        "sembol_bazinda": sembol_bazinda,
        "aciklama": (f"{len(sembol_bazinda)} sembolde {toplam} adet {ufuk} "
                     f"gunluk pencere uzerinden olculdu. Bu taban, olculen "
                     f"DONEME ozgudur; genel bir piyasa sabiti DEGILDIR."),
    }
