"""
Likidite factor engine — M2Quant metodolojisinin AlphaWise'a uyarlanmis hali.

Net_Liquidity = WALCL - TGA - RRP  (milyon USD, RRP milyar->milyon)

Ureilen faktorler:
  - Net likidite (seviye)
  - Z-skor (60g yuvarlanan)
  - YoY yuzde degisim (252 islem gunu)
  - Momentum (20g yuzde degisim)
  - Rejim (4 sinif): expansion/contraction × accelerating/decelerating

Scissors ve deviation her varlik icin ayrica hesaplanir.
"""
import math
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Sabit parametreler — M2Quant thresholds.json ile birebir
Z_WINDOW = 60
MOMENTUM_WINDOW = 20
YOY_PERIODS = 252
REGIME_SHORT = 20
REGIME_LONG = 60
SCISSORS_Z_THRESHOLD = 2.0  # +-2 sigma sinir


def gunluk_esik(baslangic: str, bitis: str) -> List[str]:
    """Hafta ici gunlerin sirali listesi (YYYY-MM-DD)."""
    d0 = datetime.strptime(baslangic, "%Y-%m-%d")
    d1 = datetime.strptime(bitis, "%Y-%m-%d")
    out = []
    while d0 <= d1:
        if d0.weekday() < 5:
            out.append(d0.strftime("%Y-%m-%d"))
        d0 += timedelta(days=1)
    return out


def _to_dict(pairs: List[Tuple[str, float]]) -> Dict[str, float]:
    return {d: v for d, v in pairs}


def ffill(gunler: List[str], seri: Dict[str, float]) -> List[Optional[float]]:
    """Son bilinen degeri ileriye tasi. Yoksa None."""
    keys = sorted(seri.keys())
    ki = 0
    son = None
    out = []
    for d in gunler:
        while ki < len(keys) and keys[ki] <= d:
            son = seri[keys[ki]]
            ki += 1
        out.append(son)
    return out


def zscore(seri: List[Optional[float]], pencere: int = Z_WINDOW) -> List[Optional[float]]:
    """Yuvarlanan z-skor. En az 5 veri gerekli."""
    out = []
    for i, v in enumerate(seri):
        lo = max(0, i - pencere + 1)
        vals = [x for x in seri[lo:i+1] if x is not None]
        if len(vals) < 5 or v is None:
            out.append(None); continue
        m = sum(vals) / len(vals)
        s = math.sqrt(sum((x - m) ** 2 for x in vals) / (len(vals) - 1))
        out.append((v - m) / s if s > 0 else None)
    return out


def yoy_pct(seri: List[Optional[float]], donem: int = YOY_PERIODS) -> List[Optional[float]]:
    out = []
    for i, v in enumerate(seri):
        if i < donem or v is None or seri[i - donem] is None or seri[i - donem] == 0:
            out.append(None); continue
        out.append((v / seri[i - donem] - 1) * 100)
    return out


def momentum(seri: List[Optional[float]], pencere: int = MOMENTUM_WINDOW) -> List[Optional[float]]:
    out = []
    for i, v in enumerate(seri):
        if i < pencere or v is None or seri[i - pencere] is None or seri[i - pencere] == 0:
            out.append(None); continue
        out.append((v / seri[i - pencere] - 1) * 100)
    return out


def rejim(i: int, net_liq: List[Optional[float]],
          mom: List[Optional[float]]) -> str:
    """Rejim: expansion/contraction × accelerating/decelerating."""
    if i < REGIME_LONG or net_liq[i] is None:
        return "belirsiz"
    short_vals = [x for x in net_liq[max(0, i - REGIME_SHORT + 1):i+1] if x is not None]
    long_vals = [x for x in net_liq[max(0, i - REGIME_LONG + 1):i+1] if x is not None]
    if not short_vals or not long_vals:
        return "belirsiz"
    short = statistics.mean(short_vals)
    long_ = statistics.mean(long_vals)
    if mom[i] is None or i < REGIME_SHORT + 1 or mom[i-1] is None:
        return "belirsiz"
    mom_delta = mom[i] - mom[i-1]
    trend = short - long_
    if trend > 0:
        return "genisleme_hizlaniyor" if mom_delta > 0 else "genisleme_yavasliyor"
    return "daralma_hizlaniyor" if mom_delta < 0 else "daralma_yavasliyor"


def net_likidite(walcl: List[Optional[float]], tga: List[Optional[float]],
                 rrp_milyar: List[Optional[float]]) -> List[Optional[float]]:
    """Net_Liquidity = WALCL - TGA - RRP. RRP milyardan milyona cevrilir."""
    out = []
    for w, t, r in zip(walcl, tga, rrp_milyar):
        if w is None or t is None or r is None:
            out.append(None); continue
        rr = r * 1000  # milyar -> milyon
        out.append(w - t - rr)
    return out


def scissors(liq_yoy: List[Optional[float]],
             ast_yoy: List[Optional[float]]) -> List[Optional[float]]:
    return [(a - b) if (a is not None and b is not None) else None
            for a, b in zip(liq_yoy, ast_yoy)]


def deviation(ast_z: List[Optional[float]],
              liq_z: List[Optional[float]]) -> List[Optional[float]]:
    return [(a - b) if (a is not None and b is not None) else None
            for a, b in zip(ast_z, liq_z)]


def composite_skor(rej: str, sci_z: Optional[float], dev: Optional[float],
                   liq_mom: Optional[float], ast_mom: Optional[float]) -> float:
    """
    M2Quant kompozit skoru: -2..+2 arasi.
    Agirlik: rejim %50, esik %30, momentum %20.
    """
    # Rejim + scissors zone -> sinyal
    def z_zone(z):
        if z is None: return "notr"
        if z >= SCISSORS_Z_THRESHOLD: return "pozitif"
        if z <= -SCISSORS_Z_THRESHOLD: return "negatif"
        return "notr"
    zone = z_zone(sci_z)
    matris = {
        "genisleme_hizlaniyor":  {"pozitif": 2, "notr": 1, "negatif": 0},
        "genisleme_yavasliyor":  {"pozitif": 0, "notr": -1, "negatif": -1},
        "daralma_hizlaniyor":    {"pozitif": 0, "notr": -1, "negatif": -2},
        "daralma_yavasliyor":    {"pozitif": 1, "notr": 0, "negatif": 0},
    }
    r_sig = matris.get(rej, {}).get(zone, 0)

    # Esik sinyali (deviation)
    if dev is None: t_sig = 0
    elif dev <= -2.0: t_sig = 2
    elif dev <= -1.5: t_sig = 1
    elif dev >= 2.0: t_sig = -2
    elif dev >= 1.5: t_sig = -1
    else: t_sig = 0

    # Momentum sinyali
    if liq_mom is None or ast_mom is None: m_sig = 0
    elif liq_mom > 0 and liq_mom > ast_mom: m_sig = 1
    elif liq_mom < 0 and liq_mom < ast_mom: m_sig = -1
    else: m_sig = 0

    return 0.5 * r_sig + 0.3 * t_sig + 0.2 * m_sig
