"""
AlphaWise Anayasa v4.4 karar kodu ve dil kurallari.

Ticari urunun karar kodlari SABITTIR: EKLE / TUT / BEKLE / DIKKAT ET.
Bu servis M2Quant'in Buy/Sell/Hold uretmez — kompozit skoru ve
kalibrasyon gecerliligini alip anayasa koduna cevirir.

KESIN IFADE YASAK: 'al', 'sat', 'kesinlikle', 'yukari gidecek' vb.
CIkti dili: 'yapilabilir', 'desteklenebilir', 'dikkat edilmeli'.
"""
import re
from typing import Optional

# Anayasa v4.4 karar kodlari
KARAR_KODLARI = ["EKLE", "TUT", "BEKLE", "DIKKAT ET"]

# Yasak kelimeler (kelime siniri ile) — case-insensitive
YASAK_PATTERNS = [
    r"\bal\b", r"\bsat\b", r"\bkesinlikle\b", r"\bmutlaka\b",
    r"\bgaranti\b", r"\byukari gidecek\b", r"\basagi gidecek\b",
    r"\bhemen\b", r"\bacele\b", r"\bpanik\b", r"\bfirsat\b",
    r"\bkacirma\b", r"\bkacirir\b", r"\bkacirmayin\b",
    r"\bmust\b", r"\bshould\b",
]
YASAK_RX = [re.compile(p, re.IGNORECASE) for p in YASAK_PATTERNS]


def dil_denetle(metin: str) -> dict:
    """Metinde yasak patern var mı?"""
    if not isinstance(metin, str):
        return {"temiz": True, "eslesmeler": []}
    eslesmeler = []
    for rx in YASAK_RX:
        for m in rx.finditer(metin):
            eslesmeler.append({"patern": rx.pattern, "eslesme": m.group()})
    return {"temiz": len(eslesmeler) == 0, "eslesmeler": eslesmeler}


def yanit_denetle(veri) -> dict:
    """JSON yanittaki tum string alanlarda yasak patern taramasi."""
    ihlaller = []

    def yuru(x, yol=""):
        if isinstance(x, dict):
            for k, v in x.items():
                yuru(v, f"{yol}.{k}" if yol else k)
        elif isinstance(x, list):
            for i, v in enumerate(x):
                yuru(v, f"{yol}[{i}]")
        elif isinstance(x, str):
            r = dil_denetle(x)
            if not r["temiz"]:
                for e in r["eslesmeler"]:
                    ihlaller.append({"alan": yol, **e})

    yuru(veri)
    return {"temiz": len(ihlaller) == 0, "ihlaller": ihlaller}


def skor_to_kod(skor: Optional[float], kalibrasyon_gecerli: bool) -> str:
    """
    Kompozit skoru anayasa koduna cevir.

    KRITIK: Kalibrasyon gecersizse (buzusme_lambda=0), yon iddiasi
    tasiyan kodlar (EKLE, DIKKAT ET) TETIKLENMEZ. Sadece TUT veya BEKLE
    donebilir. Bu, kalibrasyon gecmeden urete rijim sinyalinin
    ticari karara donusmesini engeller.

    Kalibrasyon gecerli oldugunda:
      skor >= +1.0  -> EKLE
      skor >= +0.3  -> TUT
      skor <= -1.0  -> DIKKAT ET
      skor <= -0.3  -> BEKLE
      diger         -> TUT
    """
    if skor is None:
        return "BEKLE"

    if not kalibrasyon_gecerli:
        # Yon iddiasi tasimayan iki kod: TUT (notr izleme) veya BEKLE (belirsiz)
        if abs(skor) < 0.3:
            return "TUT"
        return "BEKLE"

    if skor >= 1.0:
        return "EKLE"
    if skor >= 0.3:
        return "TUT"
    if skor <= -1.0:
        return "DIKKAT ET"
    if skor <= -0.3:
        return "BEKLE"
    return "TUT"


def guven_seviyesi(kalibrasyon_gecerli: bool, veri_tamlik: float) -> str:
    """
    Iki bilesenli guven:
      tavan = kalibrasyona bagli
      butunluk = veri tamligina bagli (0-1)
    Sonuc = min(tavan, butunluk).
    """
    tavan = "orta" if kalibrasyon_gecerli else "cok dusuk"
    if veri_tamlik >= 0.9:
        butunluk = "yuksek"
    elif veri_tamlik >= 0.7:
        butunluk = "orta"
    elif veri_tamlik >= 0.4:
        butunluk = "dusuk"
    else:
        butunluk = "cok dusuk"
    SIRA = ["cok dusuk", "dusuk", "orta", "yuksek"]
    return SIRA[min(SIRA.index(tavan), SIRA.index(butunluk))]


def oneri_metni(kod: str, guven: str) -> str:
    """
    Kod + guveni AlphaWise dil kuralına uygun oneri metnine cevirir.
    Emir kipi yok, olasi/desteklenebilir dil.
    """
    metinler = {
        "EKLE":     "pozisyon eklemesi degerlendirilebilir",
        "TUT":      "mevcut pozisyon tutulabilir; ek adim gerekmiyor",
        "BEKLE":    "yeni pozisyon acmadan izlenmesi onerilebilir",
        "DIKKAT ET":"risklere karsi dikkat gostermek desteklenebilir",
    }
    aciklama = metinler.get(kod, "pozisyon karari netlestirilemedi")
    return f"{aciklama} (guven seviyesi: {guven})"
