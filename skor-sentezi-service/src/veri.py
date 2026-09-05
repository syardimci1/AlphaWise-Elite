"""
yfinance -> Sirket donusturucusu.

NEDEN yfinance
==============
Bes eksen icin HAM mali tablo kalemleri gerekir (Total Assets, Retained
Earnings, EBIT, Receivables, ...). Bu depodaki FAA servisi yalnizca TUREV
ORANLAR donuyor (pe, roe, current_ratio gibi) — onlarla Altman/Piotroski/
Beneish hesaplanamaz. financetoolkit kutuphanesi konteynerde kurulu olmasina
ragmen `models` sinifi FMP API ANAHTARI istiyor (olculdu, enforce_source=
"YahooFinance" ile de ayni hatayi veriyor) ve ucretli bagimlilik butce kurali
geregi onaysiz kullanilamaz. yfinance ayni tablolari UCRETSIZ veriyor.

DURUSTLUK
=========
Bu katman veriyi DOLDURMAZ, TAHMIN ETMEZ, VARSAYILAN KOYMAZ. Bir kalem
yoksa sozlukte yoktur; skor katmani da onu "olculemedi" olarak isaretler.
"""
from __future__ import annotations
import math
from typing import Optional
from .skorlar import Donem, Sirket

RISKSIZ_FAIZ_SEMBOLU = "^TNX"   # ABD 10 yillik tahvil getirisi (yuzde olarak)


def _sutun_sozluk(df, sutun) -> dict:
    """Bir donem sutununu {kalem: deger} sozluguna cevirir; NaN'lari ATAR."""
    cikti = {}
    if df is None or getattr(df, "empty", True):
        return cikti
    seri = df[sutun]
    for kalem, deger in seri.items():
        try:
            f = float(deger)
        except (TypeError, ValueError):
            continue
        if math.isnan(f):
            continue
        cikti[str(kalem)] = f
    return cikti


def _kesintisiz_temettu_yili(temettu_serisi) -> Optional[int]:
    """Bugunden geriye dogru, temettu odenen KESINTISIZ yil sayisi."""
    if temettu_serisi is None or len(temettu_serisi) == 0:
        return 0
    yillar = sorted({d.year for d in temettu_serisi.index}, reverse=True)
    if not yillar:
        return 0
    sayac, beklenen = 0, yillar[0]
    for y in yillar:
        if y == beklenen:
            sayac += 1
            beklenen -= 1
        else:
            break
    return sayac


def risksiz_faiz_getir(yf) -> Optional[float]:
    """^TNX yuzde cinsindendir (4.2 = %4.2) -> ondaliga cevrilir."""
    try:
        gecmis = yf.Ticker(RISKSIZ_FAIZ_SEMBOLU).history(period="5d")
        if gecmis is None or gecmis.empty:
            return None
        son = float(gecmis["Close"].dropna().iloc[-1])
        if not (0.0 < son < 30.0):
            return None
        return son / 100.0
    except Exception:
        return None


def sirket_getir(yf, ticker: str, azami_donem: int = 4) -> Sirket:
    t = yf.Ticker(ticker)
    bilanco, gelir, nakit = t.balance_sheet, t.financials, t.cashflow

    sutunlar = []
    if bilanco is not None and not bilanco.empty:
        sutunlar = list(bilanco.columns)[:azami_donem]

    donemler = []
    for s in sutunlar:
        donemler.append(Donem(
            tarih=str(getattr(s, "date", lambda: s)() if hasattr(s, "date") else s)[:10],
            bilanco=_sutun_sozluk(bilanco, s),
            gelir=_sutun_sozluk(gelir, s) if (gelir is not None and s in getattr(gelir, "columns", [])) else {},
            nakit=_sutun_sozluk(nakit, s) if (nakit is not None and s in getattr(nakit, "columns", [])) else {},
        ))

    try:
        bilgi = t.info or {}
    except Exception:
        bilgi = {}
    try:
        temettu = t.dividends
    except Exception:
        temettu = None

    fiyat = bilgi.get("currentPrice") or bilgi.get("regularMarketPrice")
    hisse = bilgi.get("sharesOutstanding")
    piyasa_degeri = bilgi.get("marketCap")
    if piyasa_degeri is None and fiyat and hisse:
        piyasa_degeri = float(fiyat) * float(hisse)

    piyasa = {
        "fiyat": float(fiyat) if fiyat else None,
        "hisse_adedi": float(hisse) if hisse else None,
        "piyasa_degeri": float(piyasa_degeri) if piyasa_degeri else None,
        "beta": float(bilgi["beta"]) if bilgi.get("beta") is not None else None,
        "sektor": bilgi.get("sector"),
        "sirket_adi": bilgi.get("longName") or bilgi.get("shortName"),
        "temettu_kesintisiz_yil": _kesintisiz_temettu_yili(temettu),
    }
    return Sirket(ticker=ticker.upper(), donemler=donemler, piyasa=piyasa)
