"""
Portfoy performans serisi — GERCEK defterden (Madde 30).

VERI KAYNAGI VE ERISIM BICIMI
=============================
Defter, godmode-paper-trading servisinin /veri/defter.sqlite dosyasidir.
Servisin /islemler, /kar-zarar gibi uclari kimlik istiyor (olculdu: hepsi
HTTP 401). Yonetici anahtarini yeni bir servise tasimak SIR YAYMAK olurdu;
bunun yerine defter dosyasi SALT-OKUNUR baglanir (en az yetki). Bu servis
deftere HICBIR SEY YAZMAZ.

DEFTERIN OLCULEN GERCEGI (08.09.2026)
=====================================
  islem tablosu : 8 satir, HEPSI 'buy', HEPSI MSFT, 25.08-02.09 arasi
  karar tablosu : 373 satir (360 BEKLE, 13 AL)
  SATIS YOK     -> GERCEKLESMIS kar/zarar YOK
Bu yuzden uretilen seri bir "strateji getiri gecmisi" DEGILDIR; acik
pozisyonun maliyet ve piyasa degeri egrisidir. Cikti bunu acikca yazar;
aksi halde 8 islemlik bir defterden "portfoy performansi" cikarmak, veriye
hak etmedigi bir anlam yuklemek olurdu.

OLCULEMEDI != SIFIR
===================
Bir gun icin fiyat bulunamazsa o gunun piyasa degeri None'dir, SIFIR degil.
Sifir yazmak "pozisyon degersizlesti" demek olurdu.
"""
from __future__ import annotations
from datetime import date, timedelta
from typing import Optional


def _gun(zaman: str) -> str:
    """ISO zaman damgasindan YYYY-MM-DD."""
    return str(zaman)[:10]


def pozisyon_gecmisi(islemler: list) -> dict:
    """Sembol basina, GUN GUN kumulatif adet ve maliyet.

    islemler: [{zaman, sembol, yon('buy'/'sell'), adet, fiyat, komisyon}]
    Doner: {sembol: {gun: {"adet": x, "maliyet": y}}} — yalnizca ISLEM OLAN
    gunler; aradaki gunleri seri_uret dolduracak.
    """
    birikim: dict = {}
    for i in sorted(islemler, key=lambda x: str(x.get("zaman", ""))):
        s = i.get("sembol")
        if not s:
            continue
        adet = float(i.get("adet") or 0)
        fiyat = float(i.get("fiyat") or 0)
        komisyon = float(i.get("komisyon") or 0)
        yon = str(i.get("yon", "")).lower()
        if yon not in ("buy", "sell"):
            continue
        d = birikim.setdefault(s, {"adet": 0.0, "maliyet": 0.0, "gunler": {}})
        if yon == "buy":
            d["adet"] += adet
            d["maliyet"] += adet * fiyat + komisyon
        else:
            # Satista ORTALAMA MALIYET yontemi: satilan kismin maliyeti
            # dusulur. Boylece kalan pozisyonun maliyeti bozulmaz.
            if d["adet"] > 0:
                birim = d["maliyet"] / d["adet"]
                satilan = min(adet, d["adet"])
                d["maliyet"] -= birim * satilan
                d["adet"] -= satilan
            d["maliyet"] -= komisyon * 0  # komisyon gercekleseni etkiler, maliyeti degil
        d["gunler"][_gun(i["zaman"])] = {"adet": d["adet"], "maliyet": d["maliyet"]}
    return {s: v["gunler"] for s, v in birikim.items()}


def _tasi(gunler: dict, sirali_gunler: list) -> dict:
    """Islem olmayan gunlerde son bilinen pozisyonu TASIR (forward fill)."""
    cikti, son = {}, None
    for g in sirali_gunler:
        if g in gunler:
            son = gunler[g]
        if son is not None:
            cikti[g] = son
    return cikti


def seri_uret(islemler: list, fiyatlar: dict,
              baslangic: Optional[str] = None) -> dict:
    """Gunluk portfoy serisi.

    fiyatlar: {sembol: {gun: kapanis}}
    Yalnizca FIYAT VERISI OLAN gunler (islem gunleri) seriye girer; hafta
    sonu icin uydurma nokta URETILMEZ.
    """
    gecmis = pozisyon_gecmisi(islemler)
    if not gecmis:
        return {"noktalar": [], "semboller": [], "durum": "islem_yok",
                "gerekce": "Defterde hiç işlem yok; seri üretilemez."}

    ilk_islem = min(min(g) for g in gecmis.values())
    bas = baslangic or ilk_islem

    # Islem gunleri: fiyat verisinin OLDUGU gunler.
    gunler = sorted({g for s in gecmis for g in fiyatlar.get(s, {}) if g >= bas})
    if not gunler:
        return {"noktalar": [], "semboller": sorted(gecmis), "durum": "fiyat_yok",
                "gerekce": ("İşlem günleri için fiyat verisi bulunamadı; "
                            "seri üretilemez. Bu bir ölçüm eksikliğidir.")}

    tasinmis = {s: _tasi(gecmis[s], gunler) for s in gecmis}

    noktalar = []
    for g in gunler:
        toplam_maliyet = 0.0
        toplam_deger = 0.0
        olculemeyen = []
        acik_sembol = 0
        for s in gecmis:
            poz = tasinmis[s].get(g)
            if not poz or poz["adet"] == 0:
                continue
            acik_sembol += 1
            toplam_maliyet += poz["maliyet"]
            fiyat = fiyatlar.get(s, {}).get(g)
            if fiyat is None:
                olculemeyen.append(s)
            else:
                toplam_deger += poz["adet"] * float(fiyat)
        if acik_sembol == 0:
            continue
        # Bir sembolun fiyati eksikse TOPLAM DEGER olculemez; kismi toplam
        # gostermek, eksik parcayi sifir saymak olurdu.
        deger = None if olculemeyen else round(toplam_deger, 2)
        noktalar.append({
            "gun": g,
            "maliyet": round(toplam_maliyet, 2),
            "piyasa_degeri": deger,
            "gerceklesmemis_kz": (None if deger is None
                                  else round(deger - toplam_maliyet, 2)),
            "gerceklesmemis_kz_yuzde": (
                None if deger is None or toplam_maliyet == 0
                else round(100.0 * (deger - toplam_maliyet) / toplam_maliyet, 2)),
            "olculemeyen_sembol": olculemeyen,
            "acik_sembol": acik_sembol,
        })
    return {"noktalar": noktalar, "semboller": sorted(gecmis),
            "durum": "olculdu" if noktalar else "acik_pozisyon_yok",
            "gerekce": "" if noktalar else "Seride açık pozisyon bulunan gün yok."}


def ozet(seri: dict, islemler: list) -> dict:
    """Seriyi ozetler ve NELERI SOYLEYEMEYECEGINI acikca yazar."""
    noktalar = seri.get("noktalar", [])
    satis_var = any(str(i.get("yon", "")).lower() == "sell" for i in islemler)
    olculen = [n for n in noktalar if n["piyasa_degeri"] is not None]
    son = olculen[-1] if olculen else None
    return {
        "islem_sayisi": len(islemler),
        "sembol_sayisi": len(seri.get("semboller", [])),
        "gun_sayisi": len(noktalar),
        "olculebilen_gun": len(olculen),
        "son_maliyet": son["maliyet"] if son else None,
        "son_piyasa_degeri": son["piyasa_degeri"] if son else None,
        "son_gerceklesmemis_kz": son["gerceklesmemis_kz"] if son else None,
        "gerceklesmis_kz_var_mi": satis_var,
        "sinirlar": [
            ("Bu seri GERÇEKLEŞMEMİŞ (açık pozisyon) kâr/zararı gösterir."
             if not satis_var else
             "Seri açık pozisyon değerini gösterir; gerçekleşmiş kâr/zarar ayrıca hesaplanmalıdır."),
            *([] if satis_var else
              ["Defterde hiç satış yok; gerçekleşmiş kâr/zarar HESAPLANAMAZ."]),
            f"Defterde {len(islemler)} işlem var — bu, bir strateji performans "
            f"geçmişi için istatistiksel olarak YETERSİZDİR.",
            "Boş nokta 'ölçülemedi' demektir, sıfır değil.",
        ],
    }


def is_gunu_farki(a: str, b: str) -> int:
    """a ve b (YYYY-MM-DD) arasindaki IS GUNU sayisi. Hafta sonu sayilmaz.

    Takvim gunu kullanmak yaniltici olurdu: Cuma kapanisi Pazartesi sabahi
    3 takvim gunu eski gorunur ama YALNIZCA bir islem gunu geridedir.
    (Resmi tatiller hesaba KATILMAZ; bu bilinen ve belirtilen bir sinirdir.)
    """
    try:
        g1 = date.fromisoformat(a); g2 = date.fromisoformat(b)
    except (TypeError, ValueError):
        return -1
    if g2 < g1:
        return -is_gunu_farki(b, a)
    n, g = 0, g1
    while g < g2:
        g += timedelta(days=1)
        if g.weekday() < 5:
            n += 1
    return n


def tazelik(seri: dict, bugun: Optional[str] = None, esik_is_gunu: int = 2) -> dict:
    """Serinin son gunu ile bugun arasindaki mesafe.

    NEDEN GEREKLI (canli olcumde bulundu, 08.09.2026)
    -------------------------------------------------
    Merkezi fiyat deposunun en yeni gunu 2026-09-03'tu, oysa takvim
    08.09'u gosteriyordu. Seri sessizce 09-03'te bitiyor ve grafikte
    "guncel deger" gibi okunuyordu. Bir portfoy grafiginin BES GUN eski
    oldugunu sylememesi, kullanicinin gordugu sayiya hak etmedigi bir
    guncellik atfetmesine yol acar.
    """
    noktalar = [n for n in seri.get("noktalar", []) if n.get("piyasa_degeri") is not None]
    if not noktalar:
        return {"son_gun": None, "bugun": bugun, "is_gunu_yasi": None,
                "taze_mi": None,
                "gerekce": "Ölçülebilen nokta yok; tazelik değerlendirilemez."}
    son = noktalar[-1]["gun"]
    b = bugun or date.today().isoformat()
    yas = is_gunu_farki(son, b)
    taze = None if yas < 0 else yas < esik_is_gunu
    return {
        "son_gun": son, "bugun": b, "is_gunu_yasi": (None if yas < 0 else yas),
        "taze_mi": taze,
        "gerekce": ("" if taze else
                    f"Seri {son} tarihinde bitiyor; bugün {b}. Aradaki "
                    f"{yas} iş günü için fiyat verisi YOK, dolayısıyla "
                    f"gösterilen değer GÜNCEL DEĞİLDİR."),
    }
