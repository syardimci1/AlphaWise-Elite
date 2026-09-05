"""
Ham skorlari ORTAK 0-100 olcegine cevirir.

NEDEN AYRI BIR KATMAN
=====================
Bu depoda MAA'nin bes katmani ESIT ARALIKLI DEGILDIR (taa -4..+4, faa -2..+5,
raa -2..+1, saa -1..+1, chronos -1..+1). Bunlari esit uzunlukta cizen bir
gorsel okuyucuyu yaniltir: "faa +5" ile "raa +1" ayni gorunur. Bes eksenli
sentezde ayni hatayi tekrarlamamak icin her eksen, ONCE yayimlanmis esik
degerlerine dayali capalarla 0-100'e tasinir; capalar burada TEK YERDE ve
acikca yazilidir.

Capalarin gerekcesi her fonksiyonun docstring'indedir. Capa secimi bir
YARGI'dir ve boyle etiketlenir; gizli sabit degildir.
"""
from __future__ import annotations
from typing import Optional


def parcali_dogrusal(x: float, capalar: list) -> float:
    """capalar: [(x0,y0), (x1,y1), ...] artan x. Aralik disi uclar kirpilir."""
    if x <= capalar[0][0]:
        return float(capalar[0][1])
    if x >= capalar[-1][0]:
        return float(capalar[-1][1])
    for (x0, y0), (x1, y1) in zip(capalar, capalar[1:]):
        if x0 <= x <= x1:
            if x1 == x0:
                return float(y1)
            return float(y0 + (y1 - y0) * (x - x0) / (x1 - x0))
    return float(capalar[-1][1])


# Altman'in kendi bolgeleri: Z < 1.81 sikinti, 1.81-2.99 gri, > 2.99 guvenli.
# Capalar bu esiklere oturtuldu; Z=6 pratikte ust sinir sayildi.
ALTMAN_CAPALAR = [(0.0, 0.0), (1.81, 30.0), (2.99, 70.0), (6.0, 100.0)]

# Beneish esigi -1.78 (uzerinde kazanc yonetimi olasiligi). Eksen "kazanc
# kalitesi" oldugu icin TERS cevrilir: dusuk M = yuksek puan.
BENEISH_CAPALAR = [(-2.76, 100.0), (-1.78, 50.0), (-0.80, 0.0)]

# Icsel deger / fiyat orani: 0 (veya negatif ozkaynak) -> 0, 1.0 (fiyat =
# icsel deger) -> 50, 2.0 (icsel degerin yarisina fiyatlanmis) -> 100.
# Klasik guvenlik payi yerine bu oran kullaniliyor: monoton ve sifirin her
# iki yaninda sureklidir (bkz. skorlar.dcf_icsel_fiyat_orani docstring'i).
DCF_CAPALAR = [(0.0, 0.0), (1.0, 50.0), (2.0, 100.0)]


def altman_puan(z: float) -> float:
    """Altman Z -> 0-100."""
    return parcali_dogrusal(z, ALTMAN_CAPALAR)


def piotroski_puan(f: float) -> float:
    """F-Score zaten 0-9 tam sayidir; dogrudan olceklenir."""
    return 100.0 * max(0.0, min(9.0, f)) / 9.0


def beneish_puan(m: float) -> float:
    """M-Score -> 0-100, TERS (dusuk M daha iyi kazanc kalitesi)."""
    return parcali_dogrusal(m, BENEISH_CAPALAR)


def dcf_puan(icsel_fiyat_orani: float) -> float:
    return parcali_dogrusal(icsel_fiyat_orani, DCF_CAPALAR)


def temettu_puan(p: float) -> float:
    """Temettu ekseni zaten 0-100 uretilir; yalnizca kirpilir."""
    return max(0.0, min(100.0, p))
