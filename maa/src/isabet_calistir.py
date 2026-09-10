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
    from .isabet_olcut import (OLCULEMEDI, UYGULANAMAZ, karar_degerlendir,
                               pencere_gecerli_mi)
except ImportError:                                  # duz modul olarak
    from isabet_olcut import (OLCULEMEDI, UYGULANAMAZ, karar_degerlendir,
                              pencere_gecerli_mi)

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


# market-data /price ucu VARSAYILAN 60 bar donuyor (rows[-limit:]). Diskte
# SPY.csv 1680 bar tasiyor. Limit verilmezse seri sessizce son ~3 aya
# kirpilir ve daha eski kararlarin TUT olcutu "olculemedi" olur - dogru ama
# gereksiz bir kayip. Genis limit isteniyor.
PIYASA_BAR_SINIRI = int(os.getenv("PIYASA_BAR_SINIRI", "3000"))


def piyasa_serisi(sembol: str = PIYASA_VEKILI,
                  limit: int = PIYASA_BAR_SINIRI) -> dict:
    """{tarih: kapanis} — piyasa vekili."""
    with urllib.request.urlopen(
            f"{MARKET_DATA_URL}/price/{sembol}?limit={int(limit)}",
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
    # BITIS kapanisi da dogrulanir. Onceki kod yalnizca baslangici
    # kontrol ediyordu; bitis 0 ya da negatif oldugunda (s-b)/b = -1,0
    # yani "piyasa %100 coktu" gibi UYDURMA bir olcum donuyordu. Olculemeyen
    # bir kapanisi olculmus bir getiriye cevirmek, bu deponun temel
    # degismezinin (olculemedi != sifir) ihlalidir.
    if b <= 0 or s <= 0:
        hangi = "baslangic" if b <= 0 else "bitis"
        return None, f"{PIYASA_VEKILI} {hangi} kapanisi gecersiz ({b if b <= 0 else s})"
    return (s - b) / b, f"{PIYASA_VEKILI} {bt} -> {st}"


def satirlari_degerlendir(satirlar, seri) -> list:
    """Her satiri degerlendirir. Veritabanina DOKUNMAZ (saf fonksiyon).

    KONTROL SIRASI ONEMLIDIR (10.09.2026 duzeltmesi)
    ------------------------------------------------
    Once KARAR KODU, sonra pencere bakilir. Ters sirada yapildiginda kisa
    pencereli bir BEKLE kaydi 'olculemedi' olarak isaretleniyordu; oysa
    BEKLE hicbir pencerede puanlanamaz - o 'uygulanamaz'dir.

    Ayrim onemli: 'uygulanamaz' = daha uzun beklemek DE ise yaramaz;
    'olculemedi' = daha iyi veriyle olculebilirdi. Ikisini karistirmak,
    232d1a0'da kurulan ayrimi kismen geri alir.
    """
    cikti = []
    for r in satirlar:
        # 1) YAPISAL uygunluk: karar kodu puanlanabilir mi?
        yapisal = karar_degerlendir(r.get("decision"), None, None)
        if yapisal["sonuc"] == UYGULANAMAZ:
            cikti.append({"id": r["id"], "decided_at": r.get("decided_at"),
                          "sonuc": UYGULANAMAZ, "gerekce": yapisal["gerekce"],
                          "piyasa": None})
            continue

        # 2) Pencere anlamli mi?
        pencere = None
        if r.get("decided_at") and r.get("evaluated_at"):
            pencere = (r["evaluated_at"] - r["decided_at"]).days
        p = pencere_gecerli_mi(pencere)
        if p["sonuc"] == OLCULEMEDI:
            # OLCULEMEDI satirina piyasa getirisi YAZILMAZ. Sifir gunluk bir
            # pencerede hesap teknik olarak 0,0 verir ama bu "piyasa duzdu"
            # diye okunur - olculemedi'yi sifira cevirmenin ta kendisi.
            cikti.append({"id": r["id"], "decided_at": r.get("decided_at"),
                          "sonuc": OLCULEMEDI, "gerekce": p["gerekce"],
                          "piyasa": None})
            continue

        # 3) Piyasa vekili ve olcut
        pg, pg_not = piyasa_getirisi(seri, r["decided_at"], r["evaluated_at"])
        d = karar_degerlendir(r.get("decision"), r.get("pct_change"), pg)
        # Piyasa okunamadiginda NEDENI gerekceden ATILMAZ - tam da o zaman
        # gerekiyor. Onceki kosul terstiI ve hatayi sessizlestiriyordu.
        gerekce = d["gerekce"] + (f" | {pg_not}" if pg_not else "")
        cikti.append({"id": r["id"], "decided_at": r.get("decided_at"),
                      "sonuc": d["sonuc"], "gerekce": gerekce,
                      "piyasa": pg if d["sonuc"] not in (OLCULEMEDI,) else None})
    return cikti


def main():
    import psycopg2
    import psycopg2.extras
    con = psycopg2.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
        dbname=os.getenv("DB_NAME"))
    yaz = "--yaz" in sys.argv

    # PIYASA SERISI ISLEM ACILMADAN ONCE CEKILIR (10.09.2026 duzeltmesi).
    # Onceki halde ALTER TABLE ile ayni islem icinde 45 saniyelik bir HTTP
    # cagrisi yapiliyordu; DDL, hypertable ve tum parcalari uzerinde
    # AccessExclusiveLock tutuyor ve bu kilit dis servisin yanit suresi
    # boyunca aciktı. Ayri bir veritabaninda olculdu: paralel bir INSERT
    # 9,06 saniye bloklandi. Uretimde sutunlar zaten mevcut oldugu icin DDL
    # tetiklenmiyor, ama yeni bir ortamdaki ilk --yaz calismasi canli
    # uclari askida birakirdi.
    seri = piyasa_serisi()

    with con, con.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        eklenen = semayi_hazirla(cur) if yaz else []
        if eklenen:
            print(f"sema: {len(eklenen)} sutun eklendi -> {', '.join(eklenen)}")
        cur.execute("SELECT id, ticker, decision, pct_change, decided_at, "
                    "evaluated_at, goreli_sonuc AS onceki_sonuc "
                    "FROM decision_log "
                    "WHERE evaluated_at IS NOT NULL ORDER BY id"
                    if yaz else
                    "SELECT id, ticker, decision, pct_change, decided_at, "
                    "evaluated_at, NULL AS onceki_sonuc FROM decision_log "
                    "WHERE evaluated_at IS NOT NULL ORDER BY id")
        satirlar = [dict(r) for r in cur.fetchall()]
        for r in satirlar:
            if r["pct_change"] is not None:
                r["pct_change"] = float(r["pct_change"])
            for a in ("decided_at", "evaluated_at"):
                if r[a] is not None:
                    r[a] = r[a].date()
        # KAPSAM UYARISI: piyasa serisi karar tarih araligini kapsamiyorsa
        # sessiz kalmak, kaybi "seyrek veri" gibi gosterir.
        if satirlar and seri:
            en_eski = min(r["decided_at"] for r in satirlar if r["decided_at"])
            seri_bas = min(seri)
            if en_eski.isoformat() < seri_bas:
                print(f"UYARI: piyasa serisi {seri_bas}'de basliyor ama en eski "
                      f"karar {en_eski}. Bu tarihten oncekiler olculemez.")
        sonuclar = satirlari_degerlendir(satirlar, seri)
        # GECERLI BIR OLCUM 'olculemedi' ILE EZILMEZ (10.09.2026 duzeltmesi).
        # Piyasa vekili serisi kayan bir pencere (60 bar); eski tarihler
        # pencereden dustukce daha once OLCULEN satirlar yeniden
        # calistirildiginda 'olculemedi' olurdu. Bu, elde olan bir bilgiyi
        # silmek demektir. Onceki sonuc olculmus ve yenisi olculemediyse
        # ESKISI KORUNUR.
        onceki = {r["id"]: r.get("onceki_sonuc") for r in satirlar}
        korunan = [s["id"] for s in sonuclar
                   if s["sonuc"] == OLCULEMEDI
                   and onceki.get(s["id"]) not in (None, "", OLCULEMEDI)]
        if korunan:
            print(f"korunan: {len(korunan)} satirin onceki gecerli olcumu "
                  f"'olculemedi' ile EZILMEDI -> {korunan[:10]}")
        sonuclar = [s for s in sonuclar if s["id"] not in set(korunan)]

        if yaz:
            for s in sonuclar:
                # decision_log bir TimescaleDB hypertable ve birincil anahtari
                # BILESIK: (id, decided_at). Yalnizca id ile yazmak bugun
                # calisiyor (id dizi degeri benzersiz) ama tam anahtar
                # kullanmak dogru olan ve parcalar arasinda guvenli olan yol.
                cur.execute(
                    "UPDATE decision_log SET goreli_sonuc=%s, goreli_gerekce=%s, "
                    "goreli_piyasa_getirisi=%s, goreli_zaman=NOW() "
                    "WHERE id=%s AND decided_at::date=%s",
                    (s["sonuc"], s["gerekce"][:500], s["piyasa"],
                     s["id"], s["decided_at"]))
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
