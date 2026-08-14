import qlib
from qlib.constant import REG_US

qlib.init(provider_uri='/app/qlib_bin_data/us_data', region=REG_US)

from qlib.data import D

instruments = D.instruments(market='all')
tickers = D.list_instruments(instruments=instruments, as_list=True)
print(f"Toplam hisse: {len(tickers)}")

for i, ticker in enumerate(tickers):
    try:
        df = D.features([ticker], ["$close"], start_time="2020-01-01", end_time="2026-08-13")
    except Exception as e:
        print(f"HATA BULUNDU: {ticker} -> {type(e).__name__}: {e}")
        break
    if (i + 1) % 500 == 0:
        print(f"{i+1}/{len(tickers)} kontrol edildi, sorun yok...")
else:
    print("Hicbir hisse tek basina hata vermedi")
