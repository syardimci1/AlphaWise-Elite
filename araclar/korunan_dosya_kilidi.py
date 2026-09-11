#!/usr/bin/env python3
"""Korunan dosyalarin icerik kilidini uretir.

CLAUDE.md ve otonom gorev kurali R1: bu dosyalara TEK SATIR dokunulamaz.
Kilit, dosyalarin o anki icerigini sha256 ile kaydeder; test sonraki her
koside yeniden hesaplayip karsilastirir.

ONEMLI DURUM NOTU: cascade.py ve llmquant_client.py, koruma kurali
konmadan ONCE (18.08.2026 tarihli, commit edilmemis) degisiklikler
tasiyor. Kilit bu gercegi GIZLEMEZ: her dosya icin "HEAD ile ayni mi"
bilgisi de kaydedilir. Kilit, dosyalari HEAD'e geri dondurmez; onlari
BUNDAN SONRAKI degisikliklere karsi dondurur.

Kullanim:  python3 araclar/korunan_dosya_kilidi.py [--guncelle]
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
KORUNAN = [
    "maa/src/main.py",
    "taa/src/main.py",
    "maa/src/cascade.py",
    "maa/src/llmquant_client.py",
]
KILIT = KOK / "araclar" / "korunan_dosya_kilidi.json"


def ozet(yol: Path) -> str:
    return hashlib.sha256(yol.read_bytes()).hexdigest()


def head_ile_ayni_mi(yol: str) -> bool:
    s = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", yol], cwd=KOK)
    return s.returncode == 0


def main() -> int:
    if KILIT.exists() and "--guncelle" not in sys.argv:
        print(f"kilit zaten var: {KILIT.relative_to(KOK)}\n"
              f"bilerek guncellemek icin --guncelle ver.", file=sys.stderr)
        return 2
    kayit = {}
    for yol in KORUNAN:
        p = KOK / yol
        if not p.exists():
            print(f"HATA: {yol} yok", file=sys.stderr)
            return 1
        temiz = head_ile_ayni_mi(yol)
        kayit[yol] = {"sha256": ozet(p), "bayt": p.stat().st_size,
                      "kilit_aninda_HEAD_ile_ayni": temiz}
        print(f"  {yol:28s} {kayit[yol]['sha256'][:16]} "
              f"{'HEAD ile ayni' if temiz else 'HEAD ile FARKLI (kilit oncesi)'}")
    KILIT.write_text(json.dumps({
        "aciklama": "Korunan dosyalarin icerik kilidi. Test her koside "
                    "yeniden hesaplayip karsilastirir. Kilit dosyalari "
                    "HEAD'e dondurmez; bundan sonraki degisikliklere karsi dondurur.",
        "dosyalar": kayit,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"yazildi: {KILIT.relative_to(KOK)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
