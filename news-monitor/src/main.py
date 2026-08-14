"""
ALPHAWISE - Anlik Haber/Fiyat Izleme Servisi
Iki kanal birlesik calisir:
1. Finnhub WebSocket: gercek zamanli fiyat hareketleri (watchlist icin)
2. Periyodik REST kontrolu: yeni haber basliklari -> FinBERT ile aninda skorlanir
Amac: gece/acilis oncesi erken farkindalik (dakikalar seviyesinde, milisaniye degil).
"""
import os
import json
import time
import threading
import httpx
import websocket
from datetime import datetime, timezone
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ALPHAWISE - News/Price Monitor")

FINNHUB_KEYS = [os.getenv(f"FINNHUB_API_KEY_{i}") for i in range(1, 5) if os.getenv(f"FINNHUB_API_KEY_{i}")]
FINBERT_URL = os.getenv("FINBERT_URL", "http://finbert:8000")
WATCHLIST = ["ASML", "CAT", "GOOGL", "LLY", "NVDA", "RTX", "SCHD", "SOXL", "TSM", "WDC", "WMT"]

# Bellek-ici durum (basit, ileride DB'ye tasinabilir)
_seen_news_ids = set()
_recent_alerts = []  # son N olay, en yeni basta
_last_prices = {}
MAX_ALERTS = 100


def add_alert(alert: dict):
    alert["logged_at"] = datetime.now(timezone.utc).isoformat()
    _recent_alerts.insert(0, alert)
    if len(_recent_alerts) > MAX_ALERTS:
        _recent_alerts.pop()


def check_news_loop():
    """Her 60 saniyede bir watchlist'teki YENI haberleri kontrol eder, FinBERT ile skorlar."""
    if not FINNHUB_KEYS:
        return
    while True:
        for ticker in WATCHLIST:
            try:
                resp = httpx.get(
                    "https://finnhub.io/api/v1/company-news",
                    params={
                        "symbol": ticker,
                        "from": datetime.now(timezone.utc).date().isoformat(),
                        "to": datetime.now(timezone.utc).date().isoformat(),
                        "token": FINNHUB_KEYS[0],
                    },
                    timeout=15.0,
                )
                if resp.status_code != 200:
                    continue
                for item in resp.json():
                    news_id = item.get("id")
                    if news_id in _seen_news_ids:
                        continue
                    _seen_news_ids.add(news_id)

                    related = str(item.get("related", "")).upper().split(",")
                    if ticker not in [r.strip() for r in related]:
                        continue  # 1. filtre: related alaninda gecmeli

                    headline = item.get("headline", "")
                    if not headline:
                        continue

                    # 2. filtre (SIKILASTIRMA): ticker'in kendisi VEYA sirket adi
                    # baslikta gecmeli - "related listede var ama konu o degil"
                    # sorununu (orn. coklu-hisse listeleri) engeller.
                    company_hints = {
                        "NVDA": ["NVIDIA", "NVDA"], "ASML": ["ASML"], "CAT": ["CATERPILLAR", "CAT "],
                        "GOOGL": ["GOOGLE", "ALPHABET", "GOOGL"], "LLY": ["ELI LILLY", "LILLY"],
                        "RTX": ["RTX", "RAYTHEON"], "SCHD": ["SCHD"], "SOXL": ["SOXL"],
                        "TSM": ["TSMC", "TAIWAN SEMI"], "WDC": ["WESTERN DIGITAL"], "WMT": ["WALMART"],
                    }
                    hints = company_hints.get(ticker, [ticker])
                    headline_upper = headline.upper()
                    if not any(h in headline_upper for h in hints):
                        continue

                    # FinBERT ile aninda skorla
                    try:
                        fb = httpx.post(f"{FINBERT_URL}/sentiment", json={"text": headline}, timeout=15.0)
                        sentiment = fb.json() if fb.status_code == 200 else {"label": "unknown", "score": 0}
                    except Exception:
                        sentiment = {"label": "unknown", "score": 0}

                    add_alert({
                        "type": "news",
                        "ticker": ticker,
                        "headline": headline,
                        "sentiment": sentiment,
                        "source": item.get("source"),
                        "news_time": item.get("datetime"),
                    })
            except Exception as e:
                add_alert({"type": "error", "ticker": ticker, "error": str(e)})
        time.sleep(60)


def websocket_price_loop():
    """Finnhub WebSocket'e baglanip watchlist'teki anlik fiyat hareketlerini izler."""
    if not FINNHUB_KEYS:
        return

    def on_message(ws, message):
        try:
            data = json.loads(message)
            if data.get("type") == "trade":
                for t in data.get("data", []):
                    symbol = t.get("s")
                    price = t.get("p")
                    if symbol in WATCHLIST:
                        prev = _last_prices.get(symbol)
                        _last_prices[symbol] = price
                        if prev and abs(price - prev) / prev > 0.005:  # %0.5+ ani hareket
                            add_alert({
                                "type": "price_move",
                                "ticker": symbol,
                                "from_price": prev,
                                "to_price": price,
                                "change_pct": round((price - prev) / prev * 100, 3),
                            })
        except Exception:
            pass

    def on_open(ws):
        for ticker in WATCHLIST:
            ws.send(json.dumps({"type": "subscribe", "symbol": ticker}))

    while True:
        try:
            ws = websocket.WebSocketApp(
                f"wss://ws.finnhub.io?token={FINNHUB_KEYS[0]}",
                on_message=on_message,
                on_open=on_open,
            )
            ws.run_forever()
        except Exception:
            pass
        time.sleep(10)  # baglanti koparsa yeniden dene


@app.on_event("startup")
def start_background_tasks():
    threading.Thread(target=check_news_loop, daemon=True).start()
    threading.Thread(target=websocket_price_loop, daemon=True).start()


@app.get("/health")
def health():
    return {
        "service": "News/Price Monitor",
        "status": "ok",
        "watchlist": WATCHLIST,
        "finnhub_keys": len(FINNHUB_KEYS),
        "alerts_logged": len(_recent_alerts),
    }


@app.get("/alerts")
def get_alerts(limit: int = 20, ticker: str = None):
    results = _recent_alerts
    if ticker:
        results = [a for a in results if a.get("ticker") == ticker.upper()]
    return {"count": len(results[:limit]), "alerts": results[:limit]}
