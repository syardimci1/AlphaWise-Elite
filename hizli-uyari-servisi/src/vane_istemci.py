"""Vane (godmode-arastirma-servisi) icin ince HTTP istemcisi.

Bu modul Vane/api/search'u cagirir. God Mode'un karar_uret / AL-SAT
mantigina HICBIR baglantisi yoktur (Y4) - sadece Vane'in dondurdugu
serbest metni ve kaynaklari tasir.
"""
import os
import time
import httpx

VANE_URL = os.environ.get("VANE_URL", "http://vane:3000")
CHAT_PROVIDER_ID = "bfa67bd3-d864-4e4f-96e0-dfe33517c387"  # OpenRouter (butce vekili uzerinden)
CHAT_MODEL_KEY = "deepseek/deepseek-chat-v3.1"
EMBED_PROVIDER_ID = "ab519226-afe9-45d9-ac74-c5c4376204ca"  # God Mode Yerel Ollama
EMBED_MODEL_KEY = "nomic-embed-text:latest"

VANE_TIMEOUT_SN = float(os.environ.get("VANE_TIMEOUT_SN", "300"))

TARAMA_PROMPT_SABLONU = (
    "{sembol} hakkinda bugun icin onemli, dogrulanmis piyasa veya "
    "jeopolitik haber var mi? SADECE gerceklesmis olaylari ozetle. "
    "KESINLIKLE su kelimeleri veya benzerlerini KULLANMA: al, sat, tut, "
    "bekle, yatirim tavsiyesi, hedef fiyat, pozisyon, portfoy onerisi, "
    "yukselis/dusus potansiyeli, olumlu/olumsuz sinyal. Sadece 'ne oldu' "
    "sorusuna cevap ver, 'ne yapmali' sorusuna DEGIL. Eger onemli bir "
    "gelisme yoksa acikca 'bugun icin onemli bir gelisme bulunamadi' de."
)


class VaneHatasi(Exception):
    """Vane cagrisi basarisiz oldugunda firlatilir (Y5: sessizce yutulmaz)."""


def tara(sembol: str) -> dict:
    """Vane'e sembol icin bir arastirma sorgusu gonderir.

    Donen: {"mesaj": str, "kaynaklar": list, "sure_sn": float}
    Basarisizlikta VaneHatasi firlatir - bos sozluk DONDURMEZ (Y5).
    """
    sorgu = TARAMA_PROMPT_SABLONU.format(sembol=sembol)
    govde = {
        "optimizationMode": "speed",
        "sources": ["web"],
        "chatModel": {"providerId": CHAT_PROVIDER_ID, "key": CHAT_MODEL_KEY},
        "embeddingModel": {"providerId": EMBED_PROVIDER_ID, "key": EMBED_MODEL_KEY},
        "query": sorgu,
        "history": [],
        "stream": False,
    }
    baslangic = time.monotonic()
    try:
        yanit = httpx.post(
            f"{VANE_URL}/api/search",
            json=govde,
            timeout=VANE_TIMEOUT_SN,
        )
        yanit.raise_for_status()
        veri = yanit.json()
    except httpx.HTTPError as exc:
        raise VaneHatasi(f"Vane cagrisi basarisiz: {exc}") from exc
    except ValueError as exc:
        raise VaneHatasi(f"Vane yaniti JSON degil: {exc}") from exc

    if "message" not in veri:
        raise VaneHatasi(f"Vane yanit semasi beklenmedik: {list(veri.keys())}")

    return {
        "mesaj": veri.get("message", ""),
        "kaynaklar": veri.get("sources", []),
        "sure_sn": round(time.monotonic() - baslangic, 2),
    }
