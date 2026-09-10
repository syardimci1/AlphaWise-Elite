#!/usr/bin/env python3
"""Dis API envanteri — CANLI OLCUMDEN uretilir (madde 53).

NEDEN BETIK, NEDEN ELLE YAZILMIS BIR LISTE DEGIL
================================================
Elle yazilan bir envanter yazildigi gun dogrudur ve sonra sessizce
eskir. Bu betik her calistirildiginda uc noktalara GERCEKTEN dokunur;
bir kaynak kapandiginda ya da tasindiginda liste kendini ele verir.
Madde 35'te tam olarak bu oldu: USPTO, PatentsView ve Senate LDA
uclarinin ucu de belgelerde "ucretsiz" gorunuyordu ama olculdugunde
401/403/emekli ciktilar.

HTTP KODLARI NASIL OKUNUR
=========================
Betik ANAHTARSIZ istek atar; bu bilincli bir tercihtir. Amac verinin
kendisi degil, "bu uc nokta hala orada mi ve anahtar mi istiyor" sorusu.
Dolayisiyla:
    200  -> anahtarsiz erisilebiliyor
    401  -> uc nokta AYAKTA, yalnizca anahtar istiyor (BEKLENEN)
    403  -> engelli (cografi/bot/plan)
    404  -> yol degismis ya da uc nokta kaldirilmis  <- INCELENMELI
    503  -> hiz siniri ya da gecici kesinti
    ...  -> istisna adi (baglanti kurulamadi)

Betik hicbir ucretli cagri YAPMAZ: listedeki ucretli kaynaklarda bile
anahtar gonderilmedigi icin istek faturalanabilir bir kullanim
uretmez - yalnizca kimlik dogrulama katmanina kadar gider.
"""
import json, subprocess, urllib.request, urllib.error, concurrent.futures as cf

# (ad, saglik ucu, anahtar gerekli mi, ucret modeli, kota, tuketen servis)
KAYNAKLAR = [
    ("SEC EDGAR",        "https://data.sec.gov/submissions/CIK0000789019.json", False,
     "ucretsiz", "adil kullanim (UA sart)", "sec-edgar-13f, insider-trading"),
    ("FINRA CDN (Reg SHO)", "https://cdn.finra.org/equity/regsho/daily/CNMSshvol20260909.txt", False,
     "ucretsiz", "belirtilmemis", "finra-darkpool"),
    ("DBnomics",         "https://api.db.nomics.world/v22/providers", False,
     "ucretsiz", "belirtilmemis", "liquidity-signal (yedek, madde 44)"),
    ("FRED",             "https://api.stlouisfed.org/fred/series?series_id=WALCL", True,
     "ucretsiz (anahtarli)", "120 istek/dk", "liquidity-signal"),
    ("Tiingo",           "https://api.tiingo.com/api/test", True,
     "ucretsiz katman", "6 anahtar tanimli", "market-data"),
    ("Finnhub",          "https://finnhub.io/api/v1/quote?symbol=MSFT", True,
     "ucretsiz katman", "4 anahtar tanimli", "finnhub-signal"),
    ("FlashAlpha",       "https://lab.flashalpha.com/v1/exposure/gex/MSFT", True,
     "ucretsiz katman", "5 anahtar x 5/gun = 25/gun, ~250 sembol", "gamma-exposure"),
    ("OpenRouter (LLM)", "https://openrouter.ai/api/v1/models", False,
     "UCRETLI (kredi)", "kredi bazli", "maa (cascade)"),
    ("LLMQuant",         "https://api.llmquantdata.com/", True,
     "UCRETLI (kredi)", "2 anahtar tanimli", "institution-filter"),
    ("FMP",              "https://financialmodelingprep.com/api/v3/profile/MSFT", True,
     "UCRETLI", "plan bazli", "faa (kismi)"),
    ("Alpha Vantage",    "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=MSFT", True,
     "ucretsiz katman", "25 istek/gun", "yedek"),
    ("Quiver Quant",     "https://api.quiverquant.com/beta/live/congresstrading", True,
     "UCRETLI", "plan bazli", "congress-trading"),
    ("Alpaca PAPER",     "https://paper-api.alpaca.markets/v2/clock", True,
     "ucretsiz (paper)", "200 istek/dk", "godmode-paper-trading"),
    ("Google Patents",   "https://patents.google.com/xhr/query?url=q%3Dmicrosoft", False,
     "belgelenmemis", "~10 istekte 503, >16 dk blok (madde 35)", "patent-sinyal (BAGLANMADI)"),
    ("Equibles",         "https://api.equibles.com/v1/stocks/AAPL/prices", True,
     "ucretsiz katman", "100 istek/gun (madde 52)", "YOK - anahtar bekliyor"),
    ("Databento",        "https://hist.databento.com/v0/metadata.list_datasets", True,
     "UCRETLI", "kullanim bazli", "YOK (madde 49)"),
    ("Schwab",           "https://api.schwabapi.com/marketdata/v1/quotes?symbols=MSFT", True,
     "dogrulanamadi", "dogrulanamadi", "YOK (madde 50)"),
]

def olc(u):
    r = urllib.request.Request(u, headers={"User-Agent": "AlphaWise-Envanter/1.0 (arastirma)"})
    try:
        with urllib.request.urlopen(r, timeout=25) as f:
            return f.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return type(e).__name__

with cf.ThreadPoolExecutor(max_workers=8) as ex:
    kodlar = list(ex.map(lambda k: olc(k[1]), KAYNAKLAR))

print(f"{'kaynak':<20}{'HTTP':>8}  {'anahtar':<9}{'ucret':<22}{'kota':<42}{'tuketen'}")
print("-" * 150)
for (ad, u, anah, ucret, kota, tuketen), kod in zip(KAYNAKLAR, kodlar):
    print(f"{ad:<20}{str(kod):>8}  {'evet' if anah else 'HAYIR':<9}{ucret:<22}{kota:<42}{tuketen}")
