"""bildirim-service — uygulama ici bildirim merkezi (Madde 28)."""
from __future__ import annotations
import os
from pathlib import Path
from fastapi import FastAPI

from .toplayici import kaynak_oku, sirala, ozet, DUZEY_SIRASI

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
    {"kaynak": "oz_iyilestirme", "ad": "Öz-İyileştirme Bekçisi",
     "dosya": "logs/oz_iyilestirme_bekcisi.jsonl", "bicim": "jsonl",
     "aciklama": "Servis sağlığı ve öneri üreticisinin yapılandırılmış kaydı."},
]

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
    sonuclar = []
    for k in KAYNAKLAR:
        s = kaynak_oku(VERI_KOK / k["dosya"], k["kaynak"], k["bicim"],
                       yalnizca_alarm=yalnizca_alarm)
        s["ad"] = k["ad"]
        s["aciklama"] = k["aciklama"]
        sonuclar.append(s)

    tum = sirala([o for s in sonuclar for o in s["olaylar"]])
    o = ozet(sonuclar)
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
    }
