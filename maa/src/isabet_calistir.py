"""Duzeltilmis isabet degerlendirmesini decision_log'a YAN SUTUNLARA yazar.

KORUNAN main.py'YE VE was_correct ALANINA DOKUNMAZ
==================================================
main.py'nin evaluate_decisions() fonksiyonu ve yazdigi was_correct /
evaluated_at alanlari OLDUGU GIBI KALIR. Bu betik yalnizca YENI sutunlara
yazar:

    goreli_sonuc          dogru | yanlis | uygulanamaz | olculemedi
    goreli_gerekce        neden oyle isaretlendigi
    goreli_piyasa_getirisi  ayni pencerede piyasa vekilinin getirisi
    goreli_zaman          bu degerlendirmenin yapildigi an

Boylece iki olcut YAN YANA durur ve karsilastirilabilir.

PIYASA VEKILI
=============
SPY (market-data-service'ten). Getiri, kararin verildigi gun ile
degerlendirildigi gun arasinda hesaplanir - hisse getirisiyle AYNI
PENCERE. Vekil o pencerede okunamazsa TUT icin sonuc 'olculemedi'
olur; sifir varsaymak duz bir piyasa varsaymak olurdu.

SEMA DEGISIKLIGI EKLEMELIDIR
============================
Yalnizca yeni sutun eklenir; hicbir sutun silinmez ya da degistirilmez.
Betik iki kez calistirilirsa ayni satirlari yeniden hesaplar (idempotent).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import date

try:
    from .isabet_olcut import OLCULEMEDI, karar_degerlendir, pencere_gecerli_mi
except ImportError:                                  # duz modul olarak
    from isabet_olcut import OLCULEMEDI, karar_degerlendir, pencere_gecerli_mi

PIYASA_VEKILI = os.getenv("PIYASA_VEKILI", "SPY")
MARKET_DATA_URL = os.getenv("MARKET_DATA_URL", "http://alphawise-market-data:8000")

YENI_SUTUNLAR = [
    ("goreli_sonuc", "TEXT"),
    ("goreli_gerekce", "TEXT"),
    ("goreli_piyasa_getirisi", "NUMERIC"),
    ("goreli_zaman", "TIMESTAMPTZ"),
]


def semayi_hazirla(cur):
    """Eksik sutunlari ekler. Hicbir sutun silinmez/degistirilmez."""
    # NOT: cagiran RealDictCursor kullaniyor olabilir; sutun adiyla okunur.
    cur.execute("SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'decision_log'")
    var = {(r["column_name"] if isinstance(r, dict) else r[0])
           for r in cur.fetchall()}
    eklenen = []
    for ad, tur in YENI_SUTUNLAR:
        if ad not in var:
            cur.execute(f"ALTER TABLE decision_log ADD COLUMN {ad} {tur}")
            eklenen.append(ad)
    return eklenen


def piyasa_serisi(sembol: str = PIYASA_VEKILI) -> dict:
    """{tarih: kapanis} — piyasa vekili."""
    with urllib.request.urlopen(f"{MARKET_DATA_URL}/price/{sembol}",
                                timeout=45) as f:
        d = json.load(f)
    if isinstance(d, dict) and d.get("error"):
        raise RuntimeError(f"market-data hata: {d['error']}")
    out = {}
    for b in (d or {}).get("data") or []:
        t, k = b.get("date"), b.get("close")
        if t and k:
            try:
                out[t] = float(k)
            except (TypeError, ValueError):
                continue
    if not out:
        raise RuntimeError(f"{sembol}: kapanis serisi bos")
    return out


def _en_yakin_kapanis(seri: dict, hedef: date, geriye: int = 7):
    """Hedef gun tatilse en fazla `geriye` gun geri bakar.

    Ileri BAKMAZ: gelecege bakmak, karar aninda bilinmeyen bir fiyati
    kullanmak olurdu.
    """
    for i in range(geriye + 1):
        g = date.fromordinal(hedef.toordinal() - i).isoformat()
        if g in seri:
            return seri[g], g
    return None, None


def piyasa_getirisi(seri: dict, baslangic: date, bitis: date):
    """Ayni pencerede piyasa vekilinin getirisi; okunamazsa (None, neden)."""
    b, bt = _en_yakin_kapanis(seri, baslangic)
    s, st = _en_yakin_kapanis(seri, bitis)
    if b is None or s is None:
        return None, (f"{PIYASA_VEKILI} icin "
                      f"{baslangic if b is None else bitis} civarinda kapanis yok")
    if b <= 0:
        return None, f"{PIYASA_VEKILI} baslangic kapanisi gecersiz"
    return (s - b) / b, f"{PIYASA_VEKILI} {bt} -> {st}"


def satirlari_degerlendir(satirlar, seri) -> list:
    """Her satiri degerlendirir. Veritabanina DOKUNMAZ (saf fonksiyon)."""
    cikti = []
    for r in satirlar:
        pencere = None
        if r.get("decided_at") and r.get("evaluated_at"):
            pencere = (r["evaluated_at"] - r["decided_at"]).days
        pg = None
        pg_not = ""
        if r.get("decided_at") and r.get("evaluated_at"):
            pg, pg_not = piyasa_getirisi(seri, r["decided_at"], r["evaluated_at"])

        p = pencere_gecerli_mi(pencere)
        if p["sonuc"] == OLCULEMEDI:
            cikti.append({"id": r["id"], "sonuc": OLCULEMEDI,
                          "gerekce": p["gerekce"], "piyasa": pg})
            continue
        d = karar_degerlendir(r.get("decision"), r.get("pct_change"), pg)
        gerekce = d["gerekce"] + (f" | {pg_not}" if pg_not and pg is not None else "")
        cikti.append({"id": r["id"], "sonuc": d["sonuc"],
                      "gerekce": gerekce, "piyasa": pg})
    return cikti


def main():
    import psycopg2
    import psycopg2.extras
    con = psycopg2.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
        dbname=os.getenv("DB_NAME"))
    yaz = "--yaz" in sys.argv
    with con, con.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        eklenen = semayi_hazirla(cur) if yaz else []
        if eklenen:
            print(f"sema: {len(eklenen)} sutun eklendi -> {', '.join(eklenen)}")
        cur.execute("SELECT id, ticker, decision, pct_change, decided_at, "
                    "evaluated_at FROM decision_log "
                    "WHERE evaluated_at IS NOT NULL ORDER BY id")
        satirlar = [dict(r) for r in cur.fetchall()]
        for r in satirlar:
            if r["pct_change"] is not None:
                r["pct_change"] = float(r["pct_change"])
            for a in ("decided_at", "evaluated_at"):
                if r[a] is not None:
                    r[a] = r[a].date()
        seri = piyasa_serisi()
        sonuclar = satirlari_degerlendir(satirlar, seri)
        if yaz:
            for s in sonuclar:
                cur.execute(
                    "UPDATE decision_log SET goreli_sonuc=%s, goreli_gerekce=%s, "
                    "goreli_piyasa_getirisi=%s, goreli_zaman=NOW() WHERE id=%s",
                    (s["sonuc"], s["gerekce"][:500], s["piyasa"], s["id"]))
    con.close()

    sayim = {}
    for s in sonuclar:
        sayim[s["sonuc"]] = sayim.get(s["sonuc"], 0) + 1
    print(f"\n{len(sonuclar)} satir degerlendirildi"
          f"{' ve YAZILDI' if yaz else ' (KURU CALISMA - yazilmadi)'}")
    for k, v in sorted(sayim.items(), key=lambda x: -x[1]):
        print(f"  {k:<14} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
