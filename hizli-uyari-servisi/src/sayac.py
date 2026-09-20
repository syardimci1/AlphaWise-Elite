"""Gunluk istek sayaci - paylasilan $0.25/gun butceyi bu servisin tek
basina tuketmesini onlemek icin yerel, ek bir istek-sayisi siniri.

butce-vekili'nin kendi gun/harcama defteri (butce-veri/) deseniyle
tutarli: gune gore sifirlanan basit bir JSON dosyasi.
"""
import json
import os
import threading
from datetime import date

VERI_YOLU = os.environ.get("SAYAC_DOSYA_YOLU", "/veri/sayac.json")
GUNLUK_LIMIT = int(os.environ.get("GUNLUK_ISTEK_LIMITI", "20"))

_kilit = threading.Lock()


class GunlukLimitAsildi(Exception):
    pass


def _oku() -> dict:
    try:
        with open(VERI_YOLU, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"gun": None, "sayac": 0}


def _yaz(veri: dict) -> None:
    os.makedirs(os.path.dirname(VERI_YOLU), exist_ok=True)
    with open(VERI_YOLU, "w") as f:
        json.dump(veri, f)


def istek_izni_al() -> dict:
    """Bugun icin bir istek hakki dusurur.

    Limit asilirsa GunlukLimitAsildi firlatir (Y5: sessizce izin vermez).
    Donen: {"gun": str, "kullanilan": int, "limit": int}
    """
    bugun = date.today().isoformat()
    with _kilit:
        veri = _oku()
        if veri.get("gun") != bugun:
            veri = {"gun": bugun, "sayac": 0}
        if veri["sayac"] >= GUNLUK_LIMIT:
            raise GunlukLimitAsildi(
                f"Gunluk istek limiti ({GUNLUK_LIMIT}) asildi: {bugun}"
            )
        veri["sayac"] += 1
        _yaz(veri)
        return {"gun": bugun, "kullanilan": veri["sayac"], "limit": GUNLUK_LIMIT}


def durum() -> dict:
    bugun = date.today().isoformat()
    with _kilit:
        veri = _oku()
        if veri.get("gun") != bugun:
            return {"gun": bugun, "kullanilan": 0, "limit": GUNLUK_LIMIT}
        return {"gun": bugun, "kullanilan": veri["sayac"], "limit": GUNLUK_LIMIT}
