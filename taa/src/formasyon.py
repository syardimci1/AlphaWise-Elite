"""
Klasik mum (candlestick) formasyonu tespiti — 23.08.2026.

KAYNAK VE PORT NOTU
Fikir kaynagi: anupama-srivastava/market-pattern-recognition (MIT).
Kod KOPYALANMADI, sifirdan yeniden yazildi. Guvenlik denetimi (B.1) temiz
cikti (ag cagrisi yok, kimlik bilgisi okumuyor, exec/eval/pickle/base64 yok,
obfuscation yok) ama KOD KALITESI denetiminde kaynakta dogrulanmis hatalar
bulundu; bu surum onlari icermez:

  1. Kaynakta `_detect_engulfing` bool degil -1/0/1 INT donduruyor, digerleri
     bool. Sonra hepsi toplandigi icin bearish engulfing, "formasyon cesitliligi"
     sayacindan SESSIZCE dusuyordu. Burada bogazlama iki AYRI bool alana
     ayrildi (bullish_engulfing / bearish_engulfing).
  2. Kaynakta `bullish_patterns`, adinda "bullish" GECEN sutunlari topluyordu
     ama hicbir formasyon adinda "bullish" gecmiyor -> her zaman 0, dolayisiyla
     `pattern_momentum` de her zaman 0 (olu ozellik). Burada yon siniflandirmasi
     ada gore degil, ACIK bir haritayla yapilir.
  3. Kaynagin bilgisayarli goru sinifi (cv2 + matplotlib + sklearn) PORT
     EDILMEDI: `range(...).index(Timestamp)` ile ve matplotlib 3.8'de
     kaldirilan `tostring_rgb()` ile calismiyor, ayrica O(n^2) LinearRegression
     donguSu iceriyor. Uc agir bagimlilik icin karsiligi yok.

Bu modul YALNIZCA pandas + numpy kullanir; TAA'ya yeni bagimlilik eklemez.

DIL KURALI: Bu modul olgusal tespit yapar. "Bogazlama gorundu" demek
"fiyat yukselecek" demek DEGILDIR; formasyonlarin ongoru gucu bu sistemde
KALIBRE EDILMEMISTIR ve cikti karar koduna baglanmaz.
"""
import numpy as np
import pandas as pd

# Formasyon -> geleneksel yon sinifi. Ada gore tahmin YERINE acik harita
# (kaynak koddaki olu ozellik hatasinin sebebi buydu).
YON_SINIFI = {
    "doji": "notr",
    "hammer": "boga",
    "inverted_hammer": "boga",
    "bullish_engulfing": "boga",
    "morning_star": "boga",
    "piercing_line": "boga",
    "three_white_soldiers": "boga",
    "hanging_man": "ayi",
    "shooting_star": "ayi",
    "bearish_engulfing": "ayi",
    "evening_star": "ayi",
    "dark_cloud_cover": "ayi",
    "three_black_crows": "ayi",
}
FORMASYONLAR = tuple(YON_SINIFI.keys())


def _olcut(df: pd.DataFrame) -> pd.DataFrame:
    """Mum govdesi/golgeleri ve oransal buyuklukleri."""
    d = df.copy()
    d["govde"] = (d["Close"] - d["Open"]).abs()
    d["ust_golge"] = d["High"] - np.maximum(d["Open"], d["Close"])
    d["alt_golge"] = np.minimum(d["Open"], d["Close"]) - d["Low"]
    d["aralik"] = d["High"] - d["Low"]
    gecerli = d["aralik"] > 0
    for ad, kaynak in (("govde_oran", "govde"),
                       ("ust_oran", "ust_golge"),
                       ("alt_oran", "alt_golge")):
        d[ad] = np.where(gecerli, d[kaynak] / d["aralik"].replace(0, np.nan), np.nan)
    return d


def tespit_et(df: pd.DataFrame) -> pd.DataFrame:
    """OHLC verisinden 13 formasyonu bool sutunlar olarak dondurur.

    Girdi: Open/High/Low/Close sutunlu DataFrame (TAA'nin get_price_data bicimi).
    Cikti: ayni indeks + her formasyon icin bool sutun.
    """
    d = _olcut(df)
    ort_govde = d["govde"].rolling(20).mean()

    boga = d["Close"] > d["Open"]
    ayi = d["Close"] < d["Open"]
    onceki_boga = boga.shift(1)
    onceki_ayi = ayi.shift(1)

    s = pd.DataFrame(index=d.index)

    s["doji"] = (d["govde_oran"] < 0.1)

    s["hammer"] = ((d["govde_oran"] < 0.3) &
                   (d["alt_oran"] > 2 * d["govde_oran"]) &
                   (d["ust_oran"] < 0.1))

    s["inverted_hammer"] = (boga &
                            (d["ust_oran"] > 2 * d["govde_oran"]) &
                            (d["alt_oran"] < 0.1))

    s["shooting_star"] = (ayi &
                          (d["ust_oran"] > 2 * d["govde_oran"]) &
                          (d["alt_oran"] < 0.1))

    # Cekic YUKSELIS trendinin tepesinde gorulurse "asilmis adam" sayilir.
    # Kaynaktaki shift(5).rolling(5) sirasi hatali; dogrusu once ortalama,
    # sonra bir gun kaydirma (bugunku kapanis ortalamaya sizmasin).
    yukselis = d["Close"] > d["Close"].rolling(5).mean().shift(1)
    s["hanging_man"] = s["hammer"] & yukselis

    s["bullish_engulfing"] = (boga & onceki_ayi &
                              (d["Close"] > d["Open"].shift(1)) &
                              (d["Open"] < d["Close"].shift(1)))
    s["bearish_engulfing"] = (ayi & onceki_boga &
                              (d["Close"] < d["Open"].shift(1)) &
                              (d["Open"] > d["Close"].shift(1)))

    uzun_ayi_2 = onceki_ayi.shift(1) & (d["govde"].shift(2) > ort_govde.shift(2))
    uzun_boga_2 = onceki_boga.shift(1) & (d["govde"].shift(2) > ort_govde.shift(2))
    kucuk_govde_1 = d["govde"].shift(1) < ort_govde.shift(1) * 0.5
    s["morning_star"] = uzun_ayi_2 & kucuk_govde_1 & boga & (d["govde"] > ort_govde)
    s["evening_star"] = uzun_boga_2 & kucuk_govde_1 & ayi & (d["govde"] > ort_govde)

    s["dark_cloud_cover"] = (onceki_boga & ayi &
                             (d["Close"] < d["Open"].shift(1)) &
                             (d["Close"] > d["Close"].shift(1)))
    s["piercing_line"] = (onceki_ayi & boga &
                          (d["Close"] > d["Close"].shift(1)) &
                          (d["Close"] < d["Open"].shift(1)))

    s["three_white_soldiers"] = (
        boga & onceki_boga & onceki_boga.shift(1) &
        (d["Close"] > d["Close"].shift(1)) & (d["Close"].shift(1) > d["Close"].shift(2)) &
        (d["Open"] > d["Open"].shift(1)) & (d["Open"].shift(1) > d["Open"].shift(2)))
    s["three_black_crows"] = (
        ayi & onceki_ayi & onceki_ayi.shift(1) &
        (d["Close"] < d["Close"].shift(1)) & (d["Close"].shift(1) < d["Close"].shift(2)) &
        (d["Open"] < d["Open"].shift(1)) & (d["Open"].shift(1) < d["Open"].shift(2)))

    return s[list(FORMASYONLAR)].fillna(False).astype(bool)


def son_bar_ozeti(df: pd.DataFrame, gun: int = 10) -> dict:
    """Son bar ve son `gun` gundeki formasyonlarin OLGUSAL ozeti."""
    s = tespit_et(df)
    if s.empty:
        return {"hata": "veri yok"}
    son = s.iloc[-1]
    pencere = s.tail(gun)
    sayim = {k: int(pencere[k].sum()) for k in FORMASYONLAR if pencere[k].sum() > 0}
    return {
        "son_bar_tarihi": str(s.index[-1])[:10],
        "son_barda_gorulen": [k for k in FORMASYONLAR if bool(son[k])],
        "son_%d_gun_sayim" % gun: sayim,
        "boga_formasyonu_sayisi": int(sum(v for k, v in sayim.items()
                                          if YON_SINIFI[k] == "boga")),
        "ayi_formasyonu_sayisi": int(sum(v for k, v in sayim.items()
                                         if YON_SINIFI[k] == "ayi")),
        "yon_siniflari": YON_SINIFI,
        "kalibrasyon_gecerli": False,
        "not": ("Formasyonlar OLGUSAL olarak tespit edilir. Bu sistemde ongoru "
                "gucleri KALIBRE EDILMEMISTIR; karar koduna baglanmazlar."),
    }
