"""
Backtest ↔ canli kod-yolu PARITE OLCERI (Madde 33).

NEDEN VAR
=========
NautilusTrader'in muhendislik dersi: backtest'in kullandigi kod yolu ile
canlinin kullandigi kod yolu ayrisirsa, backtest sonuclari canli davranisi
temsil etmez — ve bu ayrisma SESSIZDIR. Kimse hata almaz.

09.09.2026 denetiminde bu depoda tam olarak boyle bir ayrisma OLCULDU:
    backtest RSI : walkforward.py:71  vbt.RSI.run(...)   (basit ortalama)
    canli RSI    : main.py:109        talib.RSI(...)     (Wilder yumusatmasi)
Gercek veriyle: MSFT'te ortalama 6,28 / maksimum 26,72 RSI puani fark;
30/70 esik karari barlarin %17,9'unda ayrisiyor. Giris kosulu MSFT'te
backtest RSI'iyla 57 gun, canli RSI'iyla 2 gun tetikleniyor.

BU MODULUN ISI DUZELTMEK DEGIL, OLCMEK
======================================
Ayrismayi duzeltmek (iki yolu tek kutuphanede birlestirmek) yayimlanmis tum
backtest sonuclarini degistirir ve ayri bir karardir; ustelik canli yolun
dosyasi (taa/src/main.py) KORUNMUSTUR. Bu modul yalnizca farki SAYIYA
cevirir, boylece:
  * fark gorunur olur (sessiz olmaktan cikar),
  * zamanla buyuyup buyumedigi izlenebilir,
  * "iki yol ayni" varsayimi test tarafindan engellenir.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def rsi_wilder(kapanis: pd.Series, pencere: int = 14) -> pd.Series:
    """CANLI yolun formulu (TA-Lib ile ayni): Wilder yumusatmasi.

    TA-Lib'e bagimli olmadan, ayni ozyinelemeyi acikca uygular:
        ort_kazanc_t = (ort_kazanc_{t-1} * (n-1) + kazanc_t) / n
    Boylece bu modul TA-Lib kurulu olmayan bir ortamda da olculebilir; ayni
    kaldigini test dogrular.
    """
    fark = kapanis.diff()
    kazanc = fark.clip(lower=0.0)
    kayip = (-fark).clip(lower=0.0)
    # Ilk deger: ilk `pencere` degisimin BASIT ortalamasi (Wilder'in baslangici)
    ok = kazanc.rolling(pencere).mean()
    ol = kayip.rolling(pencere).mean()
    ok_l = ok.tolist()
    ol_l = ol.tolist()
    k_l = kazanc.tolist()
    y_l = kayip.tolist()
    for i in range(pencere + 1, len(kapanis)):
        if ok_l[i - 1] == ok_l[i - 1]:      # NaN degilse
            ok_l[i] = (ok_l[i - 1] * (pencere - 1) + k_l[i]) / pencere
            ol_l[i] = (ol_l[i - 1] * (pencere - 1) + y_l[i]) / pencere
    ok_s = pd.Series(ok_l, index=kapanis.index)
    ol_s = pd.Series(ol_l, index=kapanis.index)
    rs = ok_s / ol_s.replace(0.0, np.nan)
    return 100.0 - 100.0 / (1.0 + rs)


def rsi_basit(kapanis: pd.Series, pencere: int = 14) -> pd.Series:
    """BACKTEST yolunun formulu (vectorbt varsayilani, ewm=False):
    kazanc/kayip BASIT hareketli ortalamayla yumusatilir."""
    fark = kapanis.diff()
    ok = fark.clip(lower=0.0).rolling(pencere).mean()
    ol = (-fark).clip(lower=0.0).rolling(pencere).mean()
    rs = ok / ol.replace(0.0, np.nan)
    return 100.0 - 100.0 / (1.0 + rs)


def rsi_ayrismasi(kapanis: pd.Series, pencere: int = 14,
                  alt: float = 30.0, ust: float = 70.0) -> dict:
    """Iki RSI yolunu SAYIYA ceviren olcum.

    Doner: ortalama/maksimum mutlak fark, esik kararinin ayristigi bar orani
    ve her iki yolun esik altinda/ustunde gecirdigi gun sayisi.
    """
    a = rsi_basit(kapanis, pencere)      # backtest
    b = rsi_wilder(kapanis, pencere)     # canli
    gecerli = a.notna() & b.notna()
    if int(gecerli.sum()) == 0:
        return {"durum": "olculemedi", "bar": 0,
                "gerekce": (f"Karsilastirilabilir bar yok (seri {len(kapanis)} "
                            f"bar, pencere {pencere}).")}
    fark = (a[gecerli] - b[gecerli]).abs()
    a_dusuk, b_dusuk = a[gecerli] < alt, b[gecerli] < alt
    a_yuksek, b_yuksek = a[gecerli] > ust, b[gecerli] > ust
    ayrisan = ((a_dusuk != b_dusuk) | (a_yuksek != b_yuksek))
    return {
        "durum": "olculdu",
        "bar": int(gecerli.sum()),
        "ortalama_fark": float(fark.mean()),
        "maksimum_fark": float(fark.max()),
        "esik_ayrisan_bar": int(ayrisan.sum()),
        "esik_ayrisma_orani": float(ayrisan.mean()),
        "backtest_esik_alti_gun": int(a_dusuk.sum()),
        "canli_esik_alti_gun": int(b_dusuk.sum()),
    }


def giris_kosulu_ayrismasi(kapanis: pd.Series, rsi_pencere: int = 14,
                           rsi_alt: float = 30.0, sma_hizli: int = 20,
                           sma_yavas: int = 50) -> dict:
    """Backtest'in GIRIS kosulu (rsi<alt & sma_hizli>sma_yavas) iki RSI
    yoluyla kac gun tetikleniyor?

    Denetimde olculen en carpici sayi buydu: MSFT'te 57 gun (backtest RSI)
    vs 2 gun (canli RSI). Yani backtest, canlinin fiilen uretemeyecegi bir
    islem sikligini olcuyor.
    """
    sh = kapanis.rolling(sma_hizli).mean()
    yv = kapanis.rolling(sma_yavas).mean()
    trend = sh > yv
    bt = (rsi_basit(kapanis, rsi_pencere) < rsi_alt) & trend
    cl = (rsi_wilder(kapanis, rsi_pencere) < rsi_alt) & trend
    return {
        "backtest_giris_gun": int(bt.sum()),
        "canli_esdeger_giris_gun": int(cl.sum()),
        "ortak_gun": int((bt & cl).sum()),
        "yalnizca_backtest": int((bt & ~cl).sum()),
        "yalnizca_canli": int((cl & ~bt).sum()),
    }
