"""
Watchlist hisselerinin gecmis verisini OpenBB/Tiingo'dan cekip
Qlib'in bekledigi CSV formatina (date,open,close,high,low,volume,factor) cevirir.
"""
import httpx
import csv
import os

WATCHLIST = ["ASML", "CAT", "GOOGL", "LLY", "NVDA", "RTX", "SCHD", "SOXL", "TSM", "WDC", "WMT"]
OUTPUT_DIR = "/app/csv_data/us_data"
OPENBB_URL = "http://openbb:8000"


def fetch_ticker_data(ticker: str):
    resp = httpx.get(
        f"{OPENBB_URL}/equity/price/{ticker}",
        params={"provider": "tiingo", "start_date": "2020-01-01"},
        timeout=90.0,
    )
    if resp.status_code != 200:
        print(f"HATA {ticker}: {resp.status_code}")
        return None
    data = resp.json()
    if not isinstance(data, list):
        print(f"HATA {ticker}: {data}")
        return None
    return data


def write_qlib_csv(ticker: str, data: list):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = f"{OUTPUT_DIR}/{ticker}.csv"
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "open", "close", "high", "low", "volume", "factor"])
        for row in data:
            adj_close = row.get("adj_close", row.get("close"))
            close = row.get("close")
            factor = round(adj_close / close, 8) if close else 1.0
            writer.writerow([
                row["date"],
                row.get("adj_open", row.get("open")),
                adj_close,
                row.get("adj_high", row.get("high")),
                row.get("adj_low", row.get("low")),
                row.get("adj_volume", row.get("volume")),
                factor,
            ])
    print(f"{ticker}: {len(data)} satir yazildi -> {path}")


if __name__ == "__main__":
    for ticker in WATCHLIST:
        data = fetch_ticker_data(ticker)
        if data:
            write_qlib_csv(ticker, data)
