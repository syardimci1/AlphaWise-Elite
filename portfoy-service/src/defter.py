"""
Defter okuyucu — SALT OKUNUR (Madde 30).

Baglanti 'file:...?mode=ro' ile acilir: yanlislikla bile YAZILAMAZ. Defter,
godmode-paper-trading servisinin canli kayit dosyasidir; bu servis ona
dokunmaz, yalnizca okur.
"""
from __future__ import annotations
import os
import sqlite3
from typing import Optional

DEFTER_YOLU = os.environ.get("DEFTER_YOLU", "/veri/defter.sqlite")


def _baglan(yol: str):
    return sqlite3.connect(f"file:{yol}?mode=ro", uri=True)


def islemleri_oku(yol: Optional[str] = None) -> dict:
    """Doner: {"durum": ..., "islemler": [...], "gerekce": ...}

    Dosya yoksa veya okunamazsa BOS LISTE ile birlikte DURUM bildirilir;
    bos liste tek basina "islem yok" demek DEGILDIR.
    """
    y = yol or DEFTER_YOLU
    if not os.path.exists(y):
        return {"durum": "defter_yok", "islemler": [],
                "gerekce": (f"Defter dosyası bulunamadı ({y}). Bu bir ölçüm "
                            f"eksikliğidir; 'işlem yok' anlamına GELMEZ.")}
    try:
        k = _baglan(y)
        try:
            satirlar = k.execute(
                "SELECT zaman, sembol, yon, adet, fiyat, komisyon, kayma "
                "FROM islem ORDER BY zaman").fetchall()
        finally:
            k.close()
    except sqlite3.Error as e:
        return {"durum": "okunamadi", "islemler": [],
                "gerekce": (f"Defter okunamadı ({type(e).__name__}). "
                            f"'İşlem yok' anlamına GELMEZ.")}
    islemler = [{"zaman": r[0], "sembol": r[1], "yon": r[2], "adet": r[3],
                 "fiyat": r[4], "komisyon": r[5] or 0.0, "kayma": r[6] or 0.0}
                for r in satirlar]
    return {"durum": "okundu", "islemler": islemler, "gerekce": ""}


def karar_ozeti(yol: Optional[str] = None) -> dict:
    """Karar tablosunun dagilimi — islem sayisinin neden dusuk oldugunu
    anlamak icin baglam saglar (cogu karar BEKLE cikmis olabilir)."""
    y = yol or DEFTER_YOLU
    if not os.path.exists(y):
        return {"durum": "defter_yok", "dagilim": {}}
    try:
        k = _baglan(y)
        try:
            satirlar = k.execute(
                "SELECT eylem, count(*) FROM karar GROUP BY eylem").fetchall()
            aralik = k.execute("SELECT min(zaman), max(zaman) FROM karar").fetchone()
        finally:
            k.close()
    except sqlite3.Error:
        return {"durum": "okunamadi", "dagilim": {}}
    return {"durum": "okundu", "dagilim": {a: n for a, n in satirlar},
            "ilk_karar": aralik[0], "son_karar": aralik[1]}
