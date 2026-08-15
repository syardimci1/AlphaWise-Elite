"""
ALPHAWISE - Cikti Koruyucu (15.08.2026)
Anayasa v4.4'u URETIM ANINDA zorlar. Onceden ihlaller ancak
uretildikten SONRA yakalanabiliyordu ('IZLE' vakasi gibi).
"""
import re
from typing import Literal, Optional, List
from pydantic import BaseModel, field_validator

ALLOWED = ["EKLE", "TUT", "BEKLE", "DIKKAT ET"]
BANNED = ["al", "sat", "tavsiye", "koru", "kar realize et", "firsat", "ralli", "roket"]


class KararCiktisi(BaseModel):
    ticker: str
    karar: Literal["EKLE", "TUT", "BEKLE", "DIKKAT ET"]  # genel/varsayilan
    kisa_vade_karar: Literal["EKLE", "TUT", "BEKLE", "DIKKAT ET"]
    uzun_vade_karar: Literal["EKLE", "TUT", "BEKLE", "DIKKAT ET"]
    gerekce: str
    skor: Optional[int] = None

    @field_validator("gerekce")
    @classmethod
    def yasakli_kelime_yok(cls, v: str) -> str:
        bulunan = [w for w in BANNED if re.search(r"\b" + re.escape(w) + r"\b", v.lower())]
        if bulunan:
            raise ValueError(f"Yasakli kelime: {', '.join(bulunan)}")
        return v

    @field_validator("skor")
    @classmethod
    def skor_araligi(cls, v):
        if v is not None and not -10 <= v <= 10:
            raise ValueError("skor -10..10 araliginda olmali")
        return v


def sema_talimati_vadeli() -> str:
    """Kisa/uzun vade ayrimini dayatan, AL/SAT icermeyen talimat."""
    return (
        "\n\nVADE-AYRIMLI DEGERLENDIRME (Anayasa v4.4):\n"
        "Metinde IKI AYRI karar belirt (AL/SAT KELIMELERI KULLANMA):\n"
        "  KISA VADE: [EKLE|TUT|BEKLE|DIKKAT ET] - 1-3 aylik gorunum\n"
        "  UZUN VADE: [EKLE|TUT|BEKLE|DIKKAT ET] - 6+ aylik gorunum\n"
        "Ornek: 'KISA VADE: DIKKAT ET (kisa vadeli oynaklik yuksek). "
        "UZUN VADE: EKLE (temel gorunum guclu).'\n"
        "Bu iki kod FARKLI olabilir - bu normal ve beklenen bir durumdur.\n"
    )


def sema_talimati() -> str:
    """LLM prompt'una eklenecek, semayi acikca dayatan talimat."""
    return (
        "\n\nZORUNLU CIKTI KURALLARI (Anayasa v4.4):\n"
        f"1. Karar kodu SADECE sunlardan biri: {' | '.join(ALLOWED)}\n"
        f"2. Su kelimeler YASAK: {', '.join(BANNED)}\n"
        "3. Metinde TEK bir karar kodu bulunmali.\n"
    )


def dogrula(ticker: str, karar: str, gerekce: str, skor=None,
            kisa_vade_karar: str = None, uzun_vade_karar: str = None):
    """(gecerli_mi, nesne_veya_None, hata_mesaji) doner."""
    try:
        return True, KararCiktisi(
            ticker=ticker, karar=karar, gerekce=gerekce, skor=skor,
            kisa_vade_karar=kisa_vade_karar or karar,
            uzun_vade_karar=uzun_vade_karar or karar,
        ), None
    except Exception as e:
        return False, None, str(e)
