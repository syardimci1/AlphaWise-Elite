"""bildirim-service — uygulama ici bildirim merkezi (Madde 28)."""
from __future__ import annotations
import os
from pathlib import Path
from fastapi import FastAPI

from .toplayici import (kaynak_oku, desen_oku, sirala, ozet, tekille,
                        bayatlik_isaretle,
                        yas_gun, BILGI)

VERI_KOK = Path(os.environ.get("BILDIRIM_VERI_KOK", "/veri"))

# Kaynak listesi KODA GOMULU ve gerekceli. Yeni bir alarm kaynagi eklendiginde
# buraya yazilmadikca bildirim merkezinde GORUNMEZ — bu bilincli bir tercih:
# "kendiliginden kesfet" davranisi, bir kaynagin sessizce dusmesini fark
# edilmez kilardi.
KAYNAKLAR = [
    {"kaynak": "otonom_bekci", "ad": "Otonom Çalışma Bekçisi",
     "dosya": "otonom_bekci.log", "bicim": "metin",
     "aciklama": "tmux penceresindeki Claude oturumunu 5 dakikada bir denetler."},
    {"kaynak": "haftalik_egitim", "ad": "Haftalık Eğitim Bekçisi",
     "dosya": "logs/ALARM_watchdog.log", "bicim": "metin",
     "aciklama": "Haftalık model eğitiminin gerçekten tamamlandığını denetler."},
    {"kaynak": "godmode_paper", "ad": "Kâğıt İşlem Otomasyonu",
     "dosya": "logs/ALARM_godmode_paper.log", "bicim": "metin",
     "aciklama": "Kâğıt üzerinde işlem döngüsünün arıza-güvenli durumları."},
    # Mutabakat kontrolu GUNLUK DONDURULEN dosyalara yaziyor ve "MUTABAKAT
    # TAMAM" satirlari orada. Bu kaynak eklenmeseydi, kapanmis bir mutabakat
    # sorunu bayatlik hesabinda hep "acik" gorunurdu (08.09.2026'da olculdu).
    {"kaynak": "godmode_paper", "ad": "Kâğıt İşlem Mutabakatı",
     "desen": "logs/godmode_paper_mutabakat_*.log", "bicim": "metin",
     "aciklama": "Defter ile broker pozisyonlarının günlük karşılaştırması."},
    {"kaynak": "oz_iyilestirme", "ad": "Öz-İyileştirme Bekçisi",
     "dosya": "logs/oz_iyilestirme_bekcisi.jsonl", "bicim": "jsonl",
     "aciklama": "Servis sağlığı ve öneri üreticisinin yapılandırılmış kaydı."},
]

def _kaynak_tekille(sonuclar):
    """Ayni "kaynak" adini paylasan birden fazla dosya var (alarm dosyasi +
    gunluk mutabakat dosyasi). Ozet hesabinda her kaynak BIR kez sayilmali."""
    gorulen, cikti = set(), []
    for s in sonuclar:
        if s["kaynak"] in gorulen:
            # Durumu KOTUYE dogru birlestir: biri okunamadiysa kaynak temiz sayilmaz.
            for c in cikti:
                if c["kaynak"] == s["kaynak"] and s["durum"] != "okundu":
                    c["durum"] = s["durum"]
                    c["gerekce"] = s["gerekce"]
            continue
        gorulen.add(s["kaynak"])
        cikti.append(dict(s))
    return cikti


app = FastAPI(title="AlphaWise Bildirim Merkezi", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "healthy", "servis": "bildirim",
            "kaynak_sayisi": len(KAYNAKLAR)}


@app.get("/kaynaklar")
def kaynaklar():
    return {"kaynaklar": KAYNAKLAR, "veri_kok": str(VERI_KOK)}


@app.get("/bildirimler")
def bildirimler(azami: int = 50, yalnizca_alarm: bool = True):
    if azami < 1 or azami > 500:
        azami = 50
    # HER ZAMAN tum kayitlari okuruz (yalnizca_alarm=False). Normal kayitlar
    # gosterilmese bile BAYATLIK hesabi icin gereklidir: bir alarmdan sonra
    # ayni kaynaktan normal kayit gelmis mi? Yalnizca alarmlari okusaydik,
    # bir hafta once kapanmis bir sorunu ACIK gibi gostermeye devam ederdik
    # (08.09.2026'da canli kullanimda tam olarak bu oldu).
    ham_sonuclar = []
    for k in KAYNAKLAR:
        s = (desen_oku(VERI_KOK, k["desen"], k["kaynak"], k["bicim"],
                       yalnizca_alarm=False) if k.get("desen")
             else kaynak_oku(VERI_KOK / k["dosya"], k["kaynak"], k["bicim"],
                             yalnizca_alarm=False))
        s["ad"] = k["ad"]
        s["aciklama"] = k["aciklama"]
        ham_sonuclar.append(s)

    tum_kayitlar = [o for s in ham_sonuclar for o in s["olaylar"]]

    # Gosterilecek olaylar (istege gore yalnizca alarm)
    sonuclar = []
    for s in ham_sonuclar:
        gosterilecek = (s["olaylar"] if not yalnizca_alarm
                        else [o for o in s["olaylar"] if o["duzey"] != BILGI])
        sonuclar.append({**s, "olaylar": gosterilecek})

    # Ayni satir iki kaynakta birden bulunabiliyor (mutabakat alarmi hem
    # ALARM dosyasinda hem gunluk dosyada). Tekillestirme SIRALAMADAN ONCE
    # yapilir ki sayimlar da dogru olsun.
    gosterilen = tekille([o for s in sonuclar for o in s["olaylar"]])
    bayatlik_isaretle(gosterilen, tekille(tum_kayitlar))
    for g in gosterilen:
        g["yas_gun"] = yas_gun(g.get("zaman"))
    tum = sirala(gosterilen)
    # Ozet de tekillestirilmis listeye gore hesaplanmali; aksi halde ayni
    # alarm iki kez sayilip rozet sayisini sisirir.
    o = ozet([{**s, "olaylar": [x for x in gosterilen
                                if x["kaynak"] == s["kaynak"]]}
              if s["durum"] == "okundu" or s["durum"] == "kismen_okundu" else s
              for s in _kaynak_tekille(sonuclar)])
    return {
        "ozet": o,
        "bildirimler": tum[:azami],
        "kesilen": max(0, len(tum) - azami),
        "kaynak_durumlari": [
            {"kaynak": s["kaynak"], "ad": s["ad"], "durum": s["durum"],
             "gerekce": s["gerekce"], "olay_sayisi": len(s["olaylar"]),
             "aciklama": s["aciklama"]}
            for s in sonuclar],
        # Arayuzun ASLA gizlememesi gereken alanlar.
        "sessiz_mi": o["sessiz_mi"],
        "sessizlik_guvenilir_mi": o["guvenilir_sessizlik"],
        "not": ("Liste boş olması tek başına 'alarm yok' demek DEĞİLDİR. "
                "Kaynak durumlarına bakın: okunamayan bir kaynak varsa "
                "sessizlik güvenilir değildir."),
        "bayatlik_notu": ("Her kayıtta 'sonraki_normal_kayit' alanı, o alarmdan "
                          "SONRA aynı kaynaktan kaç normal kayıt geldiğini "
                          "söyler. Sıfırdan büyükse sorun büyük olasılıkla "
                          "kapanmıştır — ama kayıt SİLİNMEZ; otomatik 'çözüldü' "
                          "kararı yanlış kapatma riski taşır."),
    }
