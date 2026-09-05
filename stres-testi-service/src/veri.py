"""
Fiyat serisi kaynagi: yfinance (birincil) + yerel qlib CSV (yedek).

NEDEN IKI KAYNAK
================
2008 krizi penceresi icin uzun gecmis gerekiyor; depodaki yerel qlib verisi
2020-01-02'de BASLIYOR (olculdu) ve 2008'i kapsamiyor. yfinance tam gecmisi
ucretsiz veriyor. Ancak yfinance ag hatasi verdiginde stres testinin tamamen
durmasi gerekmez: yerel CSV 2020 sonrasi icin yeterlidir ve hangi kaynagin
kullanildigi ciktida ACIKCA bildirilir — kaynak gizlenirse 2008 penceresinin
neden "olculemedi" dondugu anlasilmaz.
"""
from __future__ import annotations
import csv
import math
import os
from pathlib import Path
from typing import Optional

YEREL_DIZIN = Path(os.environ.get(
    "YEREL_FIYAT_DIZINI",
    "/veri/us_data"))


def yerel_seri(ticker: str) -> Optional[dict]:
    guvenli = "".join(c for c in ticker.upper() if c.isalnum() or c in ".-")
    p = YEREL_DIZIN / f"{guvenli}.csv"
    if not p.exists():
        return None
    seri = {}
    try:
        with p.open(encoding="utf-8", errors="ignore") as f:
            for satir in csv.DictReader(f):
                tarih = (satir.get("date") or "")[:10]
                try:
                    kapanis = float(satir.get("close"))
                except (TypeError, ValueError):
                    continue
                if tarih and kapanis > 0 and not math.isnan(kapanis):
                    seri[tarih] = kapanis
    except OSError:
        return None
    return seri or None


def yfinance_seri(yf, ticker: str) -> Optional[dict]:
    try:
        gecmis = yf.Ticker(ticker).history(period="max", auto_adjust=True)
    except Exception:
        return None
    if gecmis is None or getattr(gecmis, "empty", True):
        return None
    seri = {}
    for damga, kapanis in gecmis["Close"].items():
        try:
            k = float(kapanis)
        except (TypeError, ValueError):
            continue
        if k > 0 and not math.isnan(k):
            seri[str(damga)[:10]] = k
    return seri or None


def seri_getir(ticker: str, yf=None) -> tuple:
    """(seri, kaynak) doner. Kaynak ciktida bildirilir, gizlenmez."""
    if yf is not None:
        s = yfinance_seri(yf, ticker)
        if s:
            return s, "yfinance (tam gecmis, ucretsiz)"
    s = yerel_seri(ticker)
    if s:
        return s, "yerel qlib CSV (2020 sonrasi)"
    return {}, "kaynak yok"
