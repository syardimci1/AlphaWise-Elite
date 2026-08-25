"""
BILDIRIM — mevcut WhatsApp altyapisi (whapi.cloud).

DIL KURALI (CLAUDE.md): mesaj hicbir kosulda yon iddiasi ya da emir
icermez. Bicim sabittir:
    "<SIRKET> icin <OLAY> tespit edildi. Kaynak: <KAYNAK> (resmi/kamuya acik)."
Karar tamamen kullaniciya aittir; bu servis bilgi verir, tavsiye etmez.

GONDERIM VARSAYILAN OLARAK KAPALIDIR (BILDIRIM_ETKIN=0). Boylece servis
ayaga kalkar kalkmaz kimseye mesaj gitmez; acik onay olmadan disariya
mesaj cikmaz.
"""
import logging
import os
import re

import httpx

logger = logging.getLogger("olay-tarayici.bildirim")

ETKIN = os.getenv("BILDIRIM_ETKIN", "0") == "1"
WHAPI_URL = os.getenv("WHAPI_URL", "https://gate.whapi.cloud/messages/text")
WHAPI_TOKEN = os.getenv("WHAPI_TOKEN", "")
HEDEF = os.getenv("WHAPI_HEDEF", "")

# Yasak dil — CLAUDE.md DIL KURALLARI. Kendi urettigimiz metne uygulanir.
YASAK = [
    r"\bal\b", r"\bsat\b", r"\bkesinlikle\b", r"\bmutlaka\b", r"\bgaranti\b",
    r"\byukari gidecek\b", r"\basagi gidecek\b", r"\bhemen\b", r"\bacele\b",
    r"\bpanik\b", r"\bfirsat\b", r"\bkacirma\b", r"\btavsiye\b",
]
YASAK_RX = [re.compile(p, re.IGNORECASE) for p in YASAK]


def dil_denetle(metin: str) -> list:
    return [rx.pattern for rx in YASAK_RX if rx.search(metin)]


def mesaj_kur(olay: dict) -> str:
    """Sabit sablon — serbest metin uretilmez, dolayisiyla dil kaymasi olamaz."""
    if olay.get("tur") == "sec_8k":
        kodlar = ", ".join(
            f"{d['kod']} ({d['aciklama']})" for d in olay.get("item_aciklamalari", [])
        )
        return (
            f"{olay.get('sirket')} icin SEC 8-K dosyalamasi tespit edildi.\n"
            f"Bildirilen konu: {kodlar}\n"
            f"Kabul zamani (UTC): {olay.get('kabul_zamani_utc')}\n"
            f"Kaynak: SEC EDGAR resmi dosyalama (kamuya acik)\n"
            f"Bu bir bilgilendirmedir; degerlendirme size aittir."
        )
    return (
        f"{olay.get('kurum')} yeni bir yayin duyurdu.\n"
        f"Baslik: {olay.get('baslik')}\n"
        f"Kaynak: {olay.get('kaynak')} (kamuya acik)\n"
        f"Bu bir bilgilendirmedir; degerlendirme size aittir."
    )


def gonder(olay: dict) -> dict:
    """
    Bildirimi gonderir. Dil denetiminden GECMEYEN mesaj GONDERILMEZ.

    NOT: ucuncu taraf metni (kurum yayin basligi) sablonun icine
    girdigi icin denetim yalnizca SABLON kismina uygulanir; baslik
    oldugu gibi tasinir ve kaynagiyla birlikte gosterilir.
    """
    metin = mesaj_kur(olay)
    sablon = metin.replace(str(olay.get("baslik") or ""), "")
    ihlal = dil_denetle(sablon)
    if ihlal:
        logger.error("DIL IHLALI, gonderim iptal: %s", ihlal)
        return {"gonderildi": False, "sebep": "dil_denetimi", "ihlaller": ihlal}

    if not ETKIN:
        return {"gonderildi": False, "sebep": "bildirim_kapali", "onizleme": metin}
    if not (WHAPI_TOKEN and HEDEF):
        return {"gonderildi": False, "sebep": "yapilandirma_eksik", "onizleme": metin}

    try:
        with httpx.Client(timeout=30) as c:
            y = c.post(
                WHAPI_URL,
                headers={"Authorization": f"Bearer {WHAPI_TOKEN}",
                         "Content-Type": "application/json"},
                json={"to": HEDEF, "body": metin},
            )
        return {"gonderildi": y.status_code < 300, "http": y.status_code}
    except Exception as e:
        logger.warning("Bildirim gonderilemedi: %s", type(e).__name__)
        return {"gonderildi": False, "sebep": "ag_hatasi"}
