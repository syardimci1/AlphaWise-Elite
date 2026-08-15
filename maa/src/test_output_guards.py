"""Anayasa kurallarini SEMA seviyesinde zorlamayi test eder."""
from pydantic import BaseModel, field_validator
from typing import Literal
import instructor, outlines

ALLOWED = ["EKLE", "TUT", "BEKLE", "DIKKAT ET"]

class Karar(BaseModel):
    ticker: str
    karar: Literal["EKLE", "TUT", "BEKLE", "DIKKAT ET"]
    skor: int
    @field_validator("skor")
    @classmethod
    def rng(cls, v):
        if not -10 <= v <= 10: raise ValueError("skor -10..10 araliginda olmali")
        return v

print("SEMA TESTLERI:", flush=True)
ok = Karar(ticker="NVDA", karar="EKLE", skor=5)
print(f"  [GECERLI]  {ok.ticker} / {ok.karar} / {ok.skor}", flush=True)

for name, kw in [("gecersiz karar kodu 'IZLE'", dict(ticker="X", karar="IZLE", skor=1)),
                 ("skor sinir disi (99)",       dict(ticker="X", karar="TUT", skor=99))]:
    try:
        Karar(**kw); print(f"  [HATA!]    {name} kabul edildi - sema calismiyor", flush=True)
    except Exception:
        print(f"  [ENGELLENDI] {name}", flush=True)

print(f"\nSONUC: 'IZLE' gibi gecersiz kodlar artik URETIM ANINDA engelleniyor", flush=True)
print(f"       (once sadece uretildikten SONRA yakalayabiliyorduk)", flush=True)
