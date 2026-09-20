"""Hizli Uyari Modu - opsiyonel, God Mode karar mantigindan tamamen ayri
farkindalik-uyarisi servisi.

Y3: Bu servis HICBIR ZAMAN AL/SAT/TUT/BEKLE veya pozisyon buyuklugu
onermez - sadece "bugun dikkatli olun" tipi farkindalik metni uretir.
Y4: karar_uret ile SIFIR baglanti - bagimsiz bir FastAPI servisi,
God Mode'un 3 kutsal main.py dosyasindan hicbirini import etmez.
"""
import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from . import filtre, sayac, vane_istemci

HIZLI_UYARI_AKTIF = os.environ.get("HIZLI_UYARI_AKTIF", "false").lower() == "true"

app = FastAPI(title="Hizli Uyari Modu", version="1.0.0")


@app.get("/saglik")
def saglik():
    return {
        "durum": "ayakta",
        "aktif": HIZLI_UYARI_AKTIF,
        "gunluk_sayac": sayac.durum(),
    }


@app.get("/uyari/{sembol}")
def uyari_uret(sembol: str):
    if not HIZLI_UYARI_AKTIF:
        raise HTTPException(
            status_code=503,
            detail="Hizli Uyari Modu su anda devre disi (HIZLI_UYARI_AKTIF=false).",
        )

    sembol = sembol.strip().upper()
    if not sembol or not sembol.replace(".", "").isalnum():
        raise HTTPException(status_code=400, detail="Gecersiz sembol.")

    try:
        limit_bilgisi = sayac.istek_izni_al()
    except sayac.GunlukLimitAsildi as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    try:
        vane_sonucu = vane_istemci.tara(sembol)
    except vane_istemci.VaneHatasi as exc:
        # Y5: fail-loud - sessizce bos/basarili gibi donmez, hata acikca yukselir.
        raise HTTPException(
            status_code=502, detail=f"Tarama basarisiz oldu: {exc}"
        ) from exc

    denetim = filtre.denetle(vane_sonucu["mesaj"])

    onemli_gelisme_yok = "onemli bir gelisme bulunamadi" in vane_sonucu["mesaj"].lower()

    return {
        "sembol": sembol,
        "uyari_var": not onemli_gelisme_yok,
        "mesaj": denetim["guvenli_metin"],
        "filtre_tetiklendi": denetim["tetiklendi"],
        "kaynaklar": [
            {"baslik": k.get("metadata", {}).get("title"), "url": k.get("metadata", {}).get("url")}
            for k in vane_sonucu["kaynaklar"]
        ],
        "tarama_suresi_sn": vane_sonucu["sure_sn"],
        "gunluk_sayac": limit_bilgisi,
        "olusturulma_zamani": datetime.now(timezone.utc).isoformat(),
    }
