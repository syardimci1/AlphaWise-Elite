"""
ALPHAWISE - SAA (Sentiment Analysis Agent) v2
DEGISIKLIK (11.08.2026, Opus): 
- Haber kaynagi yfinance (resmi degil, guvenilmez) -> Finnhub (resmi, 4-anahtarli havuz)
- Sentiment motoru: kendi transformers modeli -> merkezi FinBERT servisi (8070)
  (tek dogruluk kaynagi, model-drift yok, halusinasyona kapali siniflandirici)
- Veri kalite kontrolu: bos/eski haber -> durust "sentiment atlandi" (uydurma yok)
"""
from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import os
import time
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ALPHAWISE - SAA (Sentiment Analysis Agent) v2")

FINBERT_URL = os.getenv("FINBERT_URL", "http://finbert:8000")

# --- Finnhub 4-anahtarli havuz (rate-limit dayanikligi icin rotasyon) ---
def _get_finnhub_keys():
    keys = []
    for i in range(1, 5):
        k = os.getenv(f"FINNHUB_API_KEY_{i}")
        if k:
            keys.append(k)
    return keys

_finnhub_keys = _get_finnhub_keys()
_key_index = 0


def _next_finnhub_key():
    """Sirayla anahtar dondurur (round-robin rotasyon)."""
    global _key_index
    if not _finnhub_keys:
        return None
    key = _finnhub_keys[_key_index % len(_finnhub_keys)]
    _key_index += 1
    return key


def fetch_finnhub_news(ticker: str, max_news: int = 10):
    """
    Finnhub'dan son 7 gunun haberlerini ceker.
    Bir anahtar rate-limit'e (429) takilirsa otomatik digerine gecer.
    """
    if not _finnhub_keys:
        return {"error": "Finnhub anahtari tanimli degil"}

    to_date = datetime.now(timezone.utc).date()
    from_date = to_date - timedelta(days=7)

    last_error = None
    # Her anahtari bir kez dene (hepsini tuketene kadar)
    for _ in range(len(_finnhub_keys)):
        key = _next_finnhub_key()
        try:
            resp = httpx.get(
                "https://finnhub.io/api/v1/company-news",
                params={
                    "symbol": ticker.upper(),
                    "from": str(from_date),
                    "to": str(to_date),
                    "token": key,
                },
                timeout=15.0,
            )
            if resp.status_code == 429:
                last_error = "rate_limit"
                continue  # sonraki anahtara gec
            if resp.status_code != 200:
                last_error = f"HTTP {resp.status_code}"
                continue
            data = resp.json()
            if isinstance(data, list):
                # KIRLILIK FILTRESI: sadece hedef ticker'in gercekten ilgili
                # oldugu haberleri tut (related alaninda sembol geçmeli).
                # Finnhub sektor haberlerini de karistirdigi icin bu sart.
                target = ticker.upper()
                filtered = []
                for item in data:
                    related = str(item.get("related", "")).upper()
                    # related virgulle ayrik olabilir: "NVDA,AMD" gibi
                    related_symbols = [s.strip() for s in related.split(",")]
                    if target in related_symbols:
                        filtered.append(item)
                return {"news": filtered[:max_news], "raw_count": len(data), "filtered_count": len(filtered)}
            last_error = "beklenmeyen_format"
        except Exception as e:
            last_error = str(e)
            continue

    return {"error": f"Tum anahtarlar basarisiz: {last_error}"}


def score_with_finbert(texts: list):
    """Metinleri merkezi FinBERT servisine gonderir, sentiment skorlari alir."""
    try:
        resp = httpx.post(
            f"{FINBERT_URL}/sentiment/batch",
            json={"texts": texts},
            timeout=30.0,
        )
        if resp.status_code != 200:
            return {"error": f"FinBERT HTTP {resp.status_code}"}
        return resp.json()
    except Exception as e:
        return {"error": f"FinBERT baglanti hatasi: {str(e)}"}


class TextInput(BaseModel):
    text: str


@app.get("/health")
def health():
    return {
        "service": "SAA",
        "status": "ok",
        "sentiment_engine": "FinBERT (merkezi servis)",
        "news_source": f"Finnhub ({len(_finnhub_keys)} anahtar havuzu)",
    }


@app.post("/analyze")
def analyze_text(input: TextInput):
    """Tek bir metnin sentiment'ini analiz eder (FinBERT uzerinden)."""
    result = score_with_finbert([input.text])
    if "error" in result:
        return {"text": input.text, "error": result["error"]}
    # SAVUNMALI ERISIM (01.09.2026 supheci turu): "results" bos ya da beklenen
    # alanlar eksik gelirse eskiden IndexError/KeyError firliyor, FastAPI bunu
    # HTTP 500 + {"detail": ...} yapiyordu. Boyle bir govdede "error" anahtari
    # bulunmadigi icin tuketici tarafinda ARIZA, sessizce "olculdu" sayilirdi.
    # Artik ariza ACIKCA "error" ile bildirilir.
    sonuclar = result.get("results") or []
    if not sonuclar:
        return {"text": input.text, "error": "FinBERT bos sonuc dondu"}
    r = sonuclar[0]
    if "label" not in r or "score" not in r:
        return {"text": input.text,
                "error": f"FinBERT beklenmeyen govde: {sorted(r)}"}
    return {"text": input.text, "sentiment": {"label": r["label"], "score": r["score"]}}


def _olculemedi(ticker: str, neden: str, haber_sayisi: int = 0) -> dict:
    """OLCULEMEDI durumu — GERCEK NOTR DUYGUDAN AYRI bir durumdur.

    =====================================================================
    NEDEN GEREKLI (olculen karar-butunlugu hatasi, 01.09.2026)
    =====================================================================
    Bu ucun DORT ariza yolu vardi (haber cekilemedi / haber yok / baslik
    yok / FinBERT hatasi) ve DORDU DE su ayni ciktiyi uretiyordu:

        {"news_count": 0, "average_score": 0.0, "overall": "neutral", ...}

    Yani "olcmedik" ile "olctuk ve notr cikti" AYIRT EDILEMIYORDU.
    MAA'nin okudugu alan `overall`'dur (maa/src/main.py:509) ve iki durumda
    da "neutral" geldigi icin score_saa her ikisinde de 0 donuyordu.

    OLCULEN KANIT (FinBERT erisilemez yapilarak):
        SAA ciktisi      -> overall="neutral", 'error' anahtari: YOK
        MAA score_saa    -> arizali: 0 | gercek notr: 0  (AYIRT EDILEMIYOR)

    Sonuc: olculmemis bir notr, olculmus bir notr gibi karar skoruna
    giriyordu. Dahasi MAA'nin "Confluence over Confidence" kapisi
    (layers_available >= 3) bu SAHTE katmanla gecilebiliyordu — yani
    BEKLE demesi gereken sistem TUT/EKLE diyebiliyordu.

    =====================================================================
    COZUM: MAA'NIN ZATEN VAR OLAN DOGRU KAPISINI TETIKLEMEK
    =====================================================================
    MAA korunan bir dosyadir ve DEGISTIRILMEDI. Gerek de yoktu: score_saa
    ilk satirinda zaten dogru kontrolu yapiyor —

        if not data or "error" in data:
            return None

    Ama SAA hicbir zaman "error" anahtari DONDURMUYORDU; sozlesme
    uyusmazligi yuzunden MAA'nin dogru mantigi hic tetiklenmiyordu.
    Artik ariza yollari "error" tasiyor, MAA kendiliginde None doner ve
    katman "yanit vermedi" sayilir — konfluans kapisi dogru calisir.

    `overall` da "neutral" yerine "veri_yok" dondurulur: yanlislikla o
    alani okuyan biri, olculmemis bir seyi notr sanmasin. `average_score`
    0.0 degil None'dir — 0.0 "olctuk, sifir cikti" demektir; oysa
    olcmedik.
    """
    return {
        "ticker": ticker.upper(),
        "news_count": haber_sayisi,
        "average_score": None,
        "overall": "veri_yok",
        # MAA score_saa (maa/src/main.py:507) bu anahtari gorup None doner.
        "error": neden,
        "olculemedi": True,
        "data_status": f"sentiment_atlandi: {neden}",
    }


@app.get("/analyze/{ticker}")
def analyze_ticker(ticker: str, max_news: int = 10):
    """
    Bir hisse icin haber-tabanli sentiment analizi.
    MAA kaskadinin cagirdigi ana endpoint - cikti formati korunmustur.

    ARIZA YONU: olculemeyen her durum _olculemedi() ile DONER ve gercek
    notr duygudan ayrilir (bkz. o fonksiyonun notu).
    """
    # 1. Haber cek (Finnhub, cok-anahtarli)
    news_result = fetch_finnhub_news(ticker, max_news)
    if "error" in news_result:
        # DURUST BOSLUK: veri yoksa uydurma yapma, atla
        return _olculemedi(ticker, news_result["error"])

    news_items = news_result["news"]

    # 2. KALITE KONTROLU: haber yoksa durust bosluk
    if not news_items:
        return _olculemedi(ticker, "son 7 gunde haber yok")

    # 3. Basliklari topla
    titles = []
    for item in news_items:
        title = item.get("headline", "")
        if title:
            titles.append(title)

    if not titles:
        return _olculemedi(ticker, "baslik bulunamadi")

    # 4. FinBERT ile skorla
    finbert_result = score_with_finbert(titles)
    if "error" in finbert_result:
        # haber_sayisi GERCEK deger: haberler CEKILDI ama skorlanamadi.
        # "0 haber" demek burada yanlis olurdu.
        return _olculemedi(ticker, finbert_result["error"], len(titles))

    # 5. Skorlama mantigi (eski koddan korundu: signed_score, ortalama, +-0.15 esik)
    #
    # SAVUNMALI AYRISTIRMA (01.09.2026 supheci turu): bu dongu eskiden
    # finbert_result["results"] ve r["label"]/r["score"]/r["text"] alanlarini
    # KORUMASIZ indeksliyordu. FinBERT HTTP 200 dondurup beklenmedik bir govde
    # verirse KeyError/TypeError firliyor, FastAPI bunu HTTP 500 +
    # {"detail": "Internal Server Error"} yapiyordu. O govdede "error" anahtari
    # OLMADIGI icin MAA'nin score_saa'si onu 0 sayip SAHTE NOTR KATMAN
    # uretiyordu - yani _olculemedi()'nin kapattigi hatanin ta kendisi baska
    # bir kapidan geri geliyordu. Artik bozuk govde de OLCULEMEDI'dir.
    sonuclar = finbert_result.get("results")
    if not isinstance(sonuclar, list) or not sonuclar:
        return _olculemedi(ticker, "FinBERT bos veya gecersiz sonuc dondu", len(titles))

    scores = []
    details = []
    for r in sonuclar:
        if not isinstance(r, dict) or "label" not in r or "score" not in r:
            return _olculemedi(
                ticker,
                f"FinBERT beklenmeyen govde: {sorted(r) if isinstance(r, dict) else type(r).__name__}",
                len(titles))
        label = str(r["label"]).lower()
        try:
            score = float(r["score"])
        except (TypeError, ValueError):
            return _olculemedi(ticker, f"FinBERT sayisal olmayan skor: {r['score']!r}", len(titles))
        signed_score = score if label == "positive" else (-score if label == "negative" else 0.0)
        scores.append(signed_score)
        details.append({"title": r.get("text", ""), "label": label, "score": round(score, 4)})

    avg_score = sum(scores) / len(scores) if scores else 0.0

    if avg_score > 0.15:
        overall = "positive"
    elif avg_score < -0.15:
        overall = "negative"
    else:
        overall = "neutral"

    return {
        "ticker": ticker.upper(),
        "news_count": len(details),
        "average_score": round(avg_score, 4),
        "overall": overall,
        "details": details,
        "data_status": "ok",
    }
