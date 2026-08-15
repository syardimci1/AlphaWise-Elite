"""
ALPHAWISE - Izleme (15.08.2026, v2)
v1 sorunu: _spans bellek-ici listeydi; cascade.py ve main.py farkli modul
ornegi yukleyince kayitlar gorunmuyordu. v2 DOSYAYA yazar -> tek kaynak.
"""
import time, os, json, threading, urllib.request
from contextlib import contextmanager

PHOENIX_URL = os.getenv("PHOENIX_URL", "http://phoenix:6006")
TRACE_FILE = "/tmp/alphawise_traces.jsonl"
MAX_LINES = 2000
_lock = threading.Lock()


def _yaz(kayit):
    try:
        with _lock:
            with open(TRACE_FILE, "a") as f:
                f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
            if os.path.getsize(TRACE_FILE) > 2_000_000:
                lines = open(TRACE_FILE).readlines()[-MAX_LINES:]
                open(TRACE_FILE, "w").writelines(lines)
    except Exception as e:
        print(f"[IZLEME] yazma hatasi (akis etkilenmedi): {e}", flush=True)


def _oku():
    if not os.path.exists(TRACE_FILE):
        return []
    out = []
    for ln in open(TRACE_FILE):
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


@contextmanager
def izle(asama: str, **meta):
    t0, hata = time.time(), None
    try:
        yield
    except Exception as e:
        hata = f"{type(e).__name__}: {e}"
        raise
    finally:
        sure = round(time.time() - t0, 3)
        _yaz({"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "asama": asama,
              "sure_sn": sure, "hata": hata, **meta})
        print(f"[IZLEME] {asama}: {sure}sn" + (f" HATA={hata}" if hata else ""), flush=True)


def son_izler(n=50):
    return _oku()[-n:]


def ozet():
    kayitlar = _oku()
    if not kayitlar:
        return {"toplam_kayit": 0, "not": "henuz kaskad calismadi"}
    from collections import defaultdict
    g = defaultdict(list)
    for s in kayitlar:
        g[s["asama"]].append(s["sure_sn"])
    asamalar = {k: {"adet": len(v), "ort_sn": round(sum(v)/len(v), 2),
                    "min_sn": min(v), "max_sn": max(v), "toplam_sn": round(sum(v), 1)}
                for k, v in sorted(g.items(), key=lambda x: -sum(x[1]))}
    return {"toplam_kayit": len(kayitlar), "hatali_adim": sum(1 for s in kayitlar if s.get("hata")),
            "en_yavas_asama": max(asamalar, key=lambda k: asamalar[k]["ort_sn"]) if asamalar else None,
            "asamalar": asamalar}


def phoenix_ayakta():
    try:
        with urllib.request.urlopen(f"{PHOENIX_URL}/", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False
