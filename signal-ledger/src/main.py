"""
ALPHAWISE - Signal Ledger (Sinyal Gunlugu)
Her hisse icin 6 sinyali AYRI AYRI toplar, o anki fiyatla TimescaleDB'ye yazar.
Amac: hangi sinyalin gercek ongoru gucu var, zamanla veriyle olcmek.
Sinyaller BIRBIRINDEN HABERSIZ kaydedilir (cift-sayim analizi icin).
"""
import os
import json
import httpx
import psycopg2
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ALPHAWISE - Signal Ledger")

MAA_URL = os.getenv("MAA_URL", "http://maa:8000")

def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
        dbname=os.getenv("DB_NAME"),
    )


@app.get("/health")
def health():
    try:
        conn = get_db(); conn.close()
        return {"service": "SignalLedger", "status": "ok", "db": "connected"}
    except Exception as e:
        return {"service": "SignalLedger", "status": "degraded", "db": str(e)}


@app.post("/capture/{ticker}")
async def capture(ticker: str):
    """
    MAA'nin decide ciktisini ceker, 6 sinyali ayristirip signal_ledger'a yazar.
    Qlib/FinRL-X henuz sinyal uretmiyor -> NULL kaydedilir (kolon hazir).
    """
    ticker = ticker.upper()

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            resp = await client.get(f"{MAA_URL}/decide/{ticker}")
            data = resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"MAA'ya ulasilamadi: {e}")

    layer_scores = data.get("layer_scores", {})
    raw = data.get("raw_data", {})

    # Fiyat: TAA'nin last_close'undan
    price = None
    taa_raw = raw.get("taa", {})
    if isinstance(taa_raw, dict):
        price = taa_raw.get("last_close")

    # Sentiment skoru: SAA'nin ham average_score'undan (varsa)
    sentiment_score = None
    saa_raw = raw.get("saa", {})
    if isinstance(saa_raw, dict) and "average_score" in saa_raw:
        sentiment_score = saa_raw.get("average_score")

    row = {
        "ticker": ticker,
        "price_at_time": price,
        "taa_score": layer_scores.get("taa"),
        "faa_score": layer_scores.get("faa"),
        "raa_score": layer_scores.get("raa"),
        "sentiment_score": sentiment_score if sentiment_score is not None else layer_scores.get("saa"),
        "qlib_score": None,      # HAZIR-BEKLIYOR
        "finrlx_score": None,    # HAZIR-BEKLIYOR
        "total_score": data.get("total_score"),
        "decision": data.get("decision"),
        "raw_json": json.dumps(data),
    }

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO signal_ledger
            (ticker, price_at_time, taa_score, faa_score, raa_score,
             sentiment_score, qlib_score, finrlx_score, total_score, decision, raw_json)
            VALUES (%(ticker)s, %(price_at_time)s, %(taa_score)s, %(faa_score)s,
                    %(raa_score)s, %(sentiment_score)s, %(qlib_score)s, %(finrlx_score)s,
                    %(total_score)s, %(decision)s, %(raw_json)s)
        """, row)
        conn.commit()
        cur.close(); conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB yazma hatasi: {e}")

    return {
        "captured": True,
        "ticker": ticker,
        "price": price,
        "signals": {k: row[k] for k in ["taa_score","faa_score","raa_score","sentiment_score","qlib_score","finrlx_score"]},
        "decision": row["decision"],
    }


@app.post("/capture-batch")
async def capture_batch(tickers: list[str]):
    """Birden fazla hisseyi tek cagirida yakalar."""
    results = []
    for t in tickers:
        try:
            r = await capture(t)
            results.append(r)
        except Exception as e:
            results.append({"ticker": t, "captured": False, "error": str(e)})
    return {"count": len(results), "results": results}


@app.get("/history/{ticker}")
def history(ticker: str, limit: int = 50):
    """Bir hissenin sinyal gecmisini dondurur (analiz icin)."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT time, price_at_time, taa_score, faa_score, raa_score,
                   sentiment_score, qlib_score, finrlx_score, total_score, decision
            FROM signal_ledger WHERE ticker = %s ORDER BY time DESC LIMIT %s
        """, (ticker.upper(), limit))
        rows = cur.fetchall()
        cur.close(); conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    cols = ["time","price","taa","faa","raa","sentiment","qlib","finrlx","total","decision"]
    return {"ticker": ticker.upper(), "count": len(rows),
            "history": [dict(zip(cols, [str(r[0])]+list(r[1:]))) for r in rows]}
