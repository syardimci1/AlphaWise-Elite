"""
ALPHAWISE - Qlib Arastirma Servisi
Microsoft Qlib'i (AI-odakli kantitatif arastirma platformu) sarmalayan servis.
Faz C - temel kurulum ve saglik kontrolu. Gercek model egitimi/faktor
tasarimi ayri bir asamada (Opus ile) ele alinacak.
"""
from fastapi import FastAPI

app = FastAPI(title="ALPHAWISE - Qlib Research Service")


@app.get("/health")
def health():
    return {"service": "Qlib", "status": "ok"}


@app.get("/qlib-version")
def qlib_version():
    """Qlib'in gercekten import edilip edilemedigini ve versiyonunu dogrular."""
    try:
        import qlib
        return {"qlib_installed": True, "version": qlib.__version__}
    except Exception as e:
        return {"qlib_installed": False, "error": str(e)}

@app.get("/bulk-fetch-status")
def bulk_fetch_status():
    """
    ABD hisse toplu veri cekme islemi ne durumda?
    Calisip calismadigini, ilerlemeyi, tahmini bitis suresini gosterir.
    """
    import json
    import os
    import time

    progress_file = "/app/csv_data/progress.json"
    universe_file = "/app/data_prep/us_stock_universe.txt"

    # Surec gercekten calisiyor mu (bulk_fetch.py islemi var mi)
    is_running = False
    try:
        for pid in os.listdir("/proc"):
            if not pid.isdigit():
                continue
            try:
                with open(f"/proc/{pid}/cmdline", "rb") as f:
                    cmdline = f.read().decode(errors="ignore")
                if "bulk_fetch.py" in cmdline:
                    is_running = True
                    break
            except Exception:
                continue
    except Exception:
        pass

    # Toplam hisse sayisi
    total = 0
    if os.path.exists(universe_file):
        with open(universe_file) as f:
            total = sum(1 for _ in f)

    # Ilerleme
    completed = failed = 0
    last_update = None
    if os.path.exists(progress_file):
        with open(progress_file) as f:
            progress = json.load(f)
        completed = len(progress.get("completed", []))
        failed = len(progress.get("failed", []))
        last_update = time.ctime(os.path.getmtime(progress_file))

    done = completed + failed
    remaining = total - done
    pct = round(done / total * 100, 2) if total else 0

    return {
        "process_running": is_running,
        "total_tickers": total,
        "completed": completed,
        "failed": failed,
        "remaining": remaining,
        "progress_percent": pct,
        "last_progress_save": last_update,
        "status_ozeti": (
            "CALISIYOR" if is_running else
            "DURMUS - yeniden baslatilmali" if remaining > 0 else
            "TAMAMLANDI"
        ),
    }


@app.get("/bist-fetch-status")
def bist_fetch_status():
    import json
    import os
    import time

    progress_file = "/app/csv_data/progress_bist.json"
    universe_file = "/app/data_prep/bist_universe.txt"

    is_running = False
    try:
        for pid in os.listdir("/proc"):
            if not pid.isdigit():
                continue
            try:
                with open(f"/proc/{pid}/cmdline", "rb") as fh:
                    cmdline = fh.read().decode(errors="ignore")
                if "bulk_fetch_bist.py" in cmdline:
                    is_running = True
                    break
            except Exception:
                continue
    except Exception:
        pass

    total = 0
    if os.path.exists(universe_file):
        with open(universe_file) as fh:
            total = sum(1 for _ in fh)

    completed = 0
    failed = 0
    last_update = None
    if os.path.exists(progress_file):
        with open(progress_file) as fh:
            progress = json.load(fh)
        completed = len(progress.get("completed", []))
        failed = len(progress.get("failed", []))
        last_update = time.ctime(os.path.getmtime(progress_file))

    done = completed + failed
    remaining = total - done
    pct = round(done / total * 100, 2) if total else 0

    if is_running:
        ozet = "CALISIYOR"
    elif remaining > 0:
        ozet = "DURMUS - yeniden baslatilmali"
    else:
        ozet = "TAMAMLANDI"

    return {
        "process_running": is_running,
        "total_tickers": total,
        "completed": completed,
        "failed": failed,
        "remaining": remaining,
        "progress_percent": pct,
        "last_progress_save": last_update,
        "status_ozeti": ozet,
    }
