"""
Anayasa §8.6 uyumlu backtest cekirdegi — walk-forward + TCA.

  §8.6: "Walk-Forward Optimization (VectorBT): Standard backtest yasak.
         Sadece expanding/rolling window. TCA: %0.20 slippage dahil."

Bu modul, Deney 4'te (23.08.2026) izole olarak dogrulanan metodolojinin
uretim surumudur. Sayisal sonuclarin deney tabaniyla BIREBIR ayni cikmasi
gerekir; bu yuzden sabitler ve hesap sirasi bilerek degistirilmedi.

MALIYET NOTU: %0.20, islem BASINA toplam surtunmedir
(fees %0.10 + slippage %0.10). Mevcut endpoint eskiden fees=0.001 ve
slippage=0 (yani %0.10) kullaniyordu — §8.6 ihlaliydi.

SABIT ORANIN DURUST SINIRI (23.08.2026'da olculdu):
Oran hisseye/likiditeye gore DEGISMIYOR; bu bir basitlestirmedir. Iki
olcumle degerlendirildi:
  1) Duyarlilik — 10 hisselik sepette walk-forward Sharpe:
       %0.00 -> -0.018 | %0.10 -> -0.081 | %0.20 -> -0.192 | %0.40 -> -0.341
     SIFIR maliyette bile Sharpe negatif (al-tut ayni donemde +0.868).
     Yani sonuc oranin tam degerine BAGLI DEGIL; hangi oran secilirse
     secilsin "kenar yok" hukmu degismiyor.
  2) Gercekcilik — sepetin gunluk dolar hacmi medyani 2,39 milyar $
     (en dusuk DIS: 0,98 milyar $). Bu likiditede gercek gidis-donus
     maliyeti ~1-3 bps'tir; 20 bps yaklasik bir buyukluk mertebesi
     MUHAFAZAKARDIR, yani stratejiyi kayirmaz.
Sonuc: bu sepet icin sabit oran yeterlidir ve sonucu carpitmamaktadir.
NEREDE YETMEZ: likit olmayan kucuk olcekli hisselerde 20 bps gercek
maliyeti AZ gosterebilir. Bu yuzden endpoint `maliyet_yuzde` parametresini
disariya acar; boyle bir evrende cagiran taraf orani yukseltmelidir.

LOOK-AHEAD KORUMASI: parametre secimi YALNIZCA [i-EGITIM_GUN, i)
araligini gorur; test penceresi [i, i+TEST_GUN) secime asla girmez.
Bu kural test_walkforward.py ile kilitlenmistir.
"""
import itertools

import numpy as np
import pandas as pd
import vectorbt as vbt

INIT_CASH = 10000.0

# §8.6 varsayilani: islem basina toplam %0.20
TCA_FEES, TCA_SLIP = 0.001, 0.001
# Endpoint'in eski (uyumsuz) hali — yalnizca referans olcum icin
ESKI_FEES, ESKI_SLIP = 0.001, 0.0

EGITIM_GUN = 252   # ~1 yil: parametre secimi
TEST_GUN = 63      # ~1 ceyrek: ornek-disi olcum
ISINMA = 120       # gostergelerin isinmasi icin en az gecmis

IZGARA = {
    "rsi_pencere": [7, 14, 21],
    "rsi_alt": [25, 30, 35],
    "rsi_ust": [65, 70, 75],
    "sma_hizli": [10, 20],
    "sma_yavas": [50, 100],
}
VARSAYILAN = {"rsi_pencere": 14, "rsi_alt": 30, "rsi_ust": 70,
              "sma_hizli": 20, "sma_yavas": 50}


def maliyetten_fees_slip(maliyet_yuzde: float):
    """Toplam islem maliyetini (yuzde) fees/slippage ciftine bolustur."""
    toplam = float(maliyet_yuzde) / 100.0
    return toplam / 2.0, toplam / 2.0


def sinyaller(kapanis: pd.Series, p: dict):
    rsi = vbt.RSI.run(kapanis, window=p["rsi_pencere"]).rsi
    sh = vbt.MA.run(kapanis, window=p["sma_hizli"]).ma
    yv = vbt.MA.run(kapanis, window=p["sma_yavas"]).ma
    giris = (rsi < p["rsi_alt"]) & (sh > yv)
    cikis = (rsi > p["rsi_ust"]) | (sh < yv)
    return giris.squeeze(), cikis.squeeze()


def portfoy(kapanis, giris, cikis, fees, slippage):
    return vbt.Portfolio.from_signals(
        kapanis, giris, cikis,
        init_cash=INIT_CASH, fees=fees, slippage=slippage, freq="1D",
    )


def olcumler(getiriler: pd.Series, islem_sayisi: int, kazanan_oran):
    """Gunluk getiri serisinden Sharpe / toplam getiri / maks dusus."""
    getiriler = getiriler.fillna(0.0)
    if len(getiriler) == 0:
        return None
    birikimli = (1 + getiriler).cumprod()
    toplam = (birikimli.iloc[-1] - 1) * 100
    std = getiriler.std()
    sharpe = float(np.sqrt(252) * getiriler.mean() / std) if std > 0 else 0.0
    zirve = birikimli.cummax()
    maks_dusus = float(((birikimli / zirve) - 1).min() * 100)
    return {
        "toplam_getiri_yuzde": round(float(toplam), 2),
        "son_deger": round(INIT_CASH * float(birikimli.iloc[-1]), 2),
        "sharpe": round(sharpe, 3),
        "maks_dusus_yuzde": round(maks_dusus, 2),
        "islem_sayisi": int(islem_sayisi),
        "kazanma_orani_yuzde": (round(float(kazanan_oran), 2)
                                if kazanan_oran is not None else None),
        "gun_sayisi": int(len(getiriler)),
    }


def ornek_ici(kapanis, fees, slip, p=VARSAYILAN):
    """Ornek-ICI olcum — SADECE referans/karsilastirma icin. Abartir."""
    g, c = sinyaller(kapanis, p)
    pf = portfoy(kapanis, g, c, fees, slip)
    st = pf.stats()
    wr = st.get("Win Rate [%]")
    return olcumler(pf.returns(), st.get("Total Trades", 0),
                    float(wr) if wr is not None and not pd.isna(wr) else None)


def _kombinasyonlar():
    ks = [dict(zip(IZGARA, v)) for v in itertools.product(*IZGARA.values())]
    return [k for k in ks
            if k["sma_hizli"] < k["sma_yavas"] and k["rsi_alt"] < k["rsi_ust"]]


def _etiket(p):
    return (f"r{p['rsi_pencere']}_{p['rsi_alt']}_{p['rsi_ust']}"
            f"_s{p['sma_hizli']}_{p['sma_yavas']}")


def toplu_sinyal_matrisi(kapanis, kombinasyonlar):
    """Tum parametre kombinasyonlarini TEK cagride sutun sutun uretir.

    HIZ: kombinasyon basina ayri Portfolio.from_signals cagirmak
    ~90 kombinasyon x ~17 pencere x 2 maliyet = 3000+ cagri demek ve
    280 sn'de bitmiyor. VectorBT 2 boyutlu sinyal cercevesini tek cagride
    isleyebiliyor; gostergeler benzersiz pencere basina BIR KEZ hesaplanir.
    """
    rsi_ler = {w: vbt.RSI.run(kapanis, window=w).rsi.squeeze()
               for w in set(k["rsi_pencere"] for k in kombinasyonlar)}
    ma_ler = {w: vbt.MA.run(kapanis, window=w).ma.squeeze()
              for w in (set(k["sma_hizli"] for k in kombinasyonlar)
                        | set(k["sma_yavas"] for k in kombinasyonlar))}
    giris, cikis = {}, {}
    for p in kombinasyonlar:
        rsi = rsi_ler[p["rsi_pencere"]]
        sh, yv = ma_ler[p["sma_hizli"]], ma_ler[p["sma_yavas"]]
        ad = _etiket(p)
        giris[ad] = (rsi < p["rsi_alt"]) & (sh > yv)
        cikis[ad] = (rsi > p["rsi_ust"]) | (sh < yv)
    return (pd.DataFrame(giris, index=kapanis.index),
            pd.DataFrame(cikis, index=kapanis.index))


def egitim_en_iyi(kapanis_dilim, kombinasyonlar, fees, slip):
    """Egitim penceresinde en yuksek Sharpe'li parametreyi dondurur.

    Girdi olarak SADECE egitim dilimi alir — cagiran taraf test
    penceresini bu fonksiyona asla vermez (look-ahead korumasi).
    """
    try:
        G, C = toplu_sinyal_matrisi(kapanis_dilim, kombinasyonlar)
        fiyat_2d = pd.DataFrame({ad: kapanis_dilim for ad in G.columns},
                                index=kapanis_dilim.index)
        pf = vbt.Portfolio.from_signals(fiyat_2d, G, C, init_cash=INIT_CASH,
                                        fees=fees, slippage=slip, freq="1D")
        sharpe = pf.sharpe_ratio()
        islem = pf.trades.count()
        gecerli = sharpe[(islem >= 2) & sharpe.notna() & np.isfinite(sharpe)]
        if len(gecerli) == 0:
            return VARSAYILAN, float("-inf")
        ad = gecerli.idxmax()
        for p in kombinasyonlar:
            if _etiket(p) == ad:
                return p, float(gecerli.max())
    except Exception:
        pass
    return VARSAYILAN, float("-inf")


def walk_forward(kapanis, fees, slip, egitim_gun=EGITIM_GUN, test_gun=TEST_GUN):
    """
    Kayan pencere: [i-egitim_gun, i) uzerinde parametre secilir,
    [i, i+test_gun) uzerinde ORNEK-DISI olculur; pencereler birlestirilir.

    LOOK-AHEAD KORUMASI: gostergeler her adimda yalnizca 0..i+test_gun
    araligindaki fiyatlarla hesaplanir (isinma icin); parametre secimi ise
    SADECE 0..i araligini gorur. Test penceresinin verisi secime girmez.
    """
    kombinasyonlar = _kombinasyonlar()
    oos_getiriler, secimler = [], []
    toplam_islem = kazanan = kapanan = 0

    baslangic = max(egitim_gun, ISINMA)
    for i in range(baslangic, len(kapanis) - 1, test_gun):
        egitim = kapanis.iloc[i - egitim_gun:i]
        test_son = min(i + test_gun, len(kapanis))
        if test_son - i < 10:
            break

        en_iyi, en_iyi_skor = egitim_en_iyi(egitim, kombinasyonlar, fees, slip)

        g_tum, c_tum = sinyaller(kapanis.iloc[:test_son], en_iyi)
        dilim = kapanis.iloc[i:test_son]
        g = g_tum.iloc[i:test_son].copy()
        c = c_tum.iloc[i:test_son].copy()
        c.iloc[-1] = True                 # pencere sonunda pozisyon kapatilir

        pf = portfoy(dilim, g, c, fees, slip)
        st = pf.stats()
        n_islem = int(st.get("Total Trades", 0))
        wr = st.get("Win Rate [%]")
        if n_islem > 0 and wr is not None and not pd.isna(wr):
            kazanan += float(wr) / 100 * n_islem
            kapanan += n_islem
        toplam_islem += n_islem
        oos_getiriler.append(pf.returns().fillna(0.0))
        secimler.append({
            "test_baslangic": str(dilim.index[0].date()),
            "test_bitis": str(dilim.index[-1].date()),
            "secilen": en_iyi,
            "egitim_sharpe": round(float(en_iyi_skor), 3),
            "oos_islem": n_islem,
        })

    if not oos_getiriler:
        return None, []
    tum = pd.concat(oos_getiriler)
    wr = (kazanan / kapanan * 100) if kapanan else None
    return olcumler(tum, toplam_islem, wr), secimler


def al_tut_referansi(kapanis, secimler):
    """Ayni ornek-disi donemde al-tut karsilastirmasi."""
    if not secimler:
        return None
    bas = pd.Timestamp(secimler[0]["test_baslangic"])
    alt = kapanis[kapanis.index >= bas]
    return olcumler(alt.pct_change().fillna(0.0), 1, None)
