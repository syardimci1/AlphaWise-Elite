"""
ALPHAWISE - Piyasa Takvimi Servisi
NYSE/NASDAQ (ABD) ve Borsa Istanbul (BIST) icin gercek zamanli
acik/kapali durumu, seans turu ve 2026 resmi tatil takvimi.
Kaynaklar: NYSE Group resmi basin acaiklamasi, Borsa Istanbul resmi PDF'i (14.08.2026 dogrulandi).
"""
from datetime import datetime, time, date
from fastapi import FastAPI
import pytz

app = FastAPI(title="ALPHAWISE - Market Hours Service")

# --- ABD (NYSE/NASDAQ) - Eastern Time ---
US_TZ = pytz.timezone("America/New_York")

US_HOLIDAYS_2026 = {
    date(2026, 1, 1): "Yılbaşı",
    date(2026, 1, 19): "Martin Luther King Jr. Günü",
    date(2026, 2, 16): "Washington's Birthday",
    date(2026, 4, 3): "Good Friday",
    date(2026, 5, 25): "Memorial Day",
    date(2026, 6, 19): "Juneteenth",
    date(2026, 7, 3): "Bağımsızlık Günü (gözlemlenen, 4 Temmuz Cumartesi)",
    date(2026, 9, 7): "Emek Günü (Labor Day)",
    date(2026, 11, 26): "Şükran Günü",
    date(2026, 12, 25): "Noel",
}
US_EARLY_CLOSE_2026 = {
    date(2026, 11, 27): "Şükran Günü sonrası (13:00 kapanış)",
    date(2026, 12, 24): "Noel arifesi (13:00 kapanış)",
}

US_PREMARKET = (time(4, 0), time(9, 30))
US_REGULAR = (time(9, 30), time(16, 0))
US_REGULAR_EARLY = (time(9, 30), time(13, 0))
US_AFTERHOURS = (time(16, 0), time(20, 0))

# --- BIST (Borsa Istanbul) - Turkey Time ---
TR_TZ = pytz.timezone("Europe/Istanbul")

TR_HOLIDAYS_2026 = {
    date(2026, 1, 1): "Yılbaşı",
    date(2026, 3, 20): "Ramazan Bayramı 1. Gün",
    date(2026, 3, 21): "Ramazan Bayramı 2. Gün",
    date(2026, 3, 22): "Ramazan Bayramı 3. Gün",
    date(2026, 4, 23): "23 Nisan Ulusal Egemenlik ve Çocuk Bayramı",
    date(2026, 5, 1): "1 Mayıs Emek ve Dayanışma Günü",
    date(2026, 5, 19): "19 Mayıs Atatürk'ü Anma Gençlik ve Spor Bayramı",
    date(2026, 5, 27): "Kurban Bayramı 1. Gün",
    date(2026, 5, 28): "Kurban Bayramı 2. Gün",
    date(2026, 5, 29): "Kurban Bayramı 3. Gün",
    date(2026, 5, 30): "Kurban Bayramı 4. Gün",
    date(2026, 8, 30): "30 Ağustos Zafer Bayramı",
    date(2026, 10, 29): "29 Ekim Cumhuriyet Bayramı",
}
TR_HALF_DAYS_2026 = {
    date(2026, 3, 19): "Ramazan Bayramı Arifesi (12:30'da kapanış)",
    date(2026, 5, 26): "Kurban Bayramı Arifesi (12:30'da kapanış)",
    date(2026, 10, 28): "Cumhuriyet Bayramı Arifesi (12:30'da kapanış)",
}

TR_REGULAR = (time(10, 0), time(18, 0))
TR_HALF_DAY = (time(10, 0), time(12, 30))


def _check_market(tz, holidays, half_days, regular_hours, half_day_hours, extra_sessions=None):
    now = datetime.now(tz)
    today = now.date()
    now_time = now.time()

    if today.weekday() >= 5:  # Cumartesi/Pazar
        return {"is_open": False, "session": "KAPALI", "reason": "hafta sonu", "local_time": now.strftime("%Y-%m-%d %H:%M:%S %Z")}

    if today in holidays:
        return {"is_open": False, "session": "KAPALI", "reason": holidays[today], "local_time": now.strftime("%Y-%m-%d %H:%M:%S %Z")}

    if today in half_days:
        start, end = half_day_hours
        is_open = start <= now_time <= end
        return {
            "is_open": is_open,
            "session": "YARIM_GUN_ACIK" if is_open else "KAPALI",
            "reason": half_days[today],
            "local_time": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        }

    if extra_sessions:
        for name, (start, end) in extra_sessions.items():
            if start <= now_time <= end:
                return {"is_open": name == "REGULAR", "session": name, "reason": None, "local_time": now.strftime("%Y-%m-%d %H:%M:%S %Z")}
        return {"is_open": False, "session": "KAPALI", "reason": "seans disi", "local_time": now.strftime("%Y-%m-%d %H:%M:%S %Z")}

    start, end = regular_hours
    is_open = start <= now_time <= end
    return {
        "is_open": is_open,
        "session": "ACIK" if is_open else "KAPALI",
        "reason": None,
        "local_time": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
    }


@app.get("/health")
def health():
    return {"service": "Market Hours Service", "status": "ok"}


@app.get("/market-status/us")
def us_status():
    today = datetime.now(US_TZ).date()
    hours = US_REGULAR_EARLY if today in US_EARLY_CLOSE_2026 else US_REGULAR
    result = _check_market(
        US_TZ, US_HOLIDAYS_2026, US_EARLY_CLOSE_2026, hours, US_REGULAR_EARLY,
        extra_sessions={"PREMARKET": US_PREMARKET, "REGULAR": hours, "AFTERHOURS": US_AFTERHOURS},
    )
    result["market"] = "NYSE/NASDAQ"
    return result


@app.get("/market-status/bist")
def bist_status():
    result = _check_market(TR_TZ, TR_HOLIDAYS_2026, TR_HALF_DAYS_2026, TR_REGULAR, TR_HALF_DAY)
    result["market"] = "Borsa Istanbul (BIST)"
    return result


@app.get("/holidays/us")
def us_holidays():
    return {"market": "NYSE/NASDAQ", "year": 2026,
            "full_holidays": {str(k): v for k, v in US_HOLIDAYS_2026.items()},
            "early_close_days": {str(k): v for k, v in US_EARLY_CLOSE_2026.items()}}


@app.get("/holidays/bist")
def bist_holidays():
    return {"market": "Borsa Istanbul", "year": 2026,
            "full_holidays": {str(k): v for k, v in TR_HOLIDAYS_2026.items()},
            "half_days": {str(k): v for k, v in TR_HALF_DAYS_2026.items()}}
