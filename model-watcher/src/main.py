"""
ALPHAWISE - OpenRouter Model Izleme Servisi
Her 3 gunde bir OpenRouter'in tum model katalogunu tarar, onceki
taramayla karsilastirir: yeni/kaldirilan/degisen (fiyat vb.) modelleri
tespit eder. Bizim kullandigimiz modelleri (deepseek/deepseek-chat vb.)
ozellikle izler - fiyat degisirse ya da kaldirilirsa uyari verir.
"""
import os
import json
import time
import threading
from datetime import datetime, timezone
import httpx
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ALPHAWISE - OpenRouter Model Watcher")

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
SNAPSHOT_FILE = "/app/data/last_snapshot.json"
SCAN_INTERVAL_SECONDS = 3 * 24 * 60 * 60  # 3 gun

# Sistemde kullandigimiz modeller - bunlarda degisiklik olursa ozel uyari
OUR_MODELS = ["deepseek/deepseek-chat"]

_last_scan_result = {"status": "henuz taranmadi"}


def fetch_models():
    resp = httpx.get(
        "https://openrouter.ai/api/v1/models",
        headers={"Authorization": f"Bearer {OPENROUTER_KEY}"} if OPENROUTER_KEY else {},
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()
    return {m["id"]: m for m in data.get("data", [])}


def load_snapshot():
    if os.path.exists(SNAPSHOT_FILE):
        with open(SNAPSHOT_FILE, "r") as f:
            return json.load(f)
    return None


def save_snapshot(models: dict):
    os.makedirs(os.path.dirname(SNAPSHOT_FILE), exist_ok=True)
    with open(SNAPSHOT_FILE, "w") as f:
        json.dump({"scanned_at": datetime.now(timezone.utc).isoformat(), "models": models}, f)


def compare_and_report(old_models: dict, new_models: dict):
    old_ids = set(old_models.keys())
    new_ids = set(new_models.keys())

    added = list(new_ids - old_ids)
    removed = list(old_ids - new_ids)

    price_changes = []
    for model_id in old_ids & new_ids:
        old_price = old_models[model_id].get("pricing", {})
        new_price = new_models[model_id].get("pricing", {})
        if old_price != new_price:
            price_changes.append({
                "model": model_id,
                "old_pricing": old_price,
                "new_pricing": new_price,
            })

    our_model_alerts = []
    for m in OUR_MODELS:
        if m in removed:
            our_model_alerts.append(f"UYARI: Kullandigimiz model '{m}' OpenRouter'dan kaldirilmis!")
        elif any(pc["model"] == m for pc in price_changes):
            our_model_alerts.append(f"NOT: Kullandigimiz model '{m}' fiyati degismis.")

    return {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "total_models": len(new_models),
        "added_count": len(added),
        "added_models": added[:20],
        "removed_count": len(removed),
        "removed_models": removed[:20],
        "price_changes_count": len(price_changes),
        "our_model_alerts": our_model_alerts,
    }


def scan_loop():
    global _last_scan_result
    while True:
        try:
            new_models = fetch_models()
            old_snapshot = load_snapshot()

            if old_snapshot is None:
                _last_scan_result = {
                    "scanned_at": datetime.now(timezone.utc).isoformat(),
                    "total_models": len(new_models),
                    "note": "Ilk tarama - karsilastirma icin referans olusturuldu",
                }
            else:
                _last_scan_result = compare_and_report(old_snapshot["models"], new_models)

            save_snapshot(new_models)
        except Exception as e:
            _last_scan_result = {"error": str(e), "scanned_at": datetime.now(timezone.utc).isoformat()}

        time.sleep(SCAN_INTERVAL_SECONDS)


@app.on_event("startup")
def start_background_scan():
    threading.Thread(target=scan_loop, daemon=True).start()


@app.get("/health")
def health():
    return {"service": "Model Watcher", "status": "ok", "scan_interval_days": 3}


@app.get("/last-scan")
def last_scan():
    return _last_scan_result


@app.post("/scan-now")
def scan_now():
    """Manuel olarak hemen tarama tetikler (3 gun beklemeden test icin)."""
    global _last_scan_result
    try:
        new_models = fetch_models()
        old_snapshot = load_snapshot()
        if old_snapshot is None:
            _last_scan_result = {
                "scanned_at": datetime.now(timezone.utc).isoformat(),
                "total_models": len(new_models),
                "note": "Ilk tarama - karsilastirma icin referans olusturuldu",
            }
        else:
            _last_scan_result = compare_and_report(old_snapshot["models"], new_models)
        save_snapshot(new_models)
        return _last_scan_result
    except Exception as e:
        return {"error": str(e)}
