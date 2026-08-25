import json
import os
import httpx
import redis as redis_lib
from datetime import datetime

REGISTRY_KEY = "alphawise:model_registry"  # eski, kural-tabanli sistem icin
PAKET_ANAHTAR_SABLONU = "alphawise:model_registry:{paket}"  # ajan-tabanli, paket-bazli
REGISTRY_TTL = 26 * 3600

ROLE_CRITERIA = {
    "analyst": {"max_input_price": 0.20, "min_context": 900000, "prefer_moe": True},
    "critic": {"max_input_price": 1.00, "min_context": 900000, "prefer_moe": True},
    "master": {"max_input_price": 0.20, "min_context": 900000, "prefer_moe": True},
}

FALLBACK_DEFAULTS = {
    "analyst": ["deepseek/deepseek-v4-flash", "deepseek/deepseek-chat", "nvidia/nemotron-3-super-120b-a12b:free"],
    "critic": ["google/gemini-2.5-flash", "deepseek/deepseek-v4-pro", "z-ai/glm-5.2", "deepseek/deepseek-v4-flash", "nvidia/nemotron-3-super-120b-a12b:free"],
    "master": ["deepseek/deepseek-v4-flash", "deepseek/deepseek-chat", "nvidia/nemotron-3-super-120b-a12b:free"],
}

MOE_HINTS = ["deepseek", "glm", "mixtral", "nemotron", "kimi", "grok", "llama-4"]  # qwen cikarildi: FP model sunmuyor (18.08.2026)


def _is_moe(model_id: str) -> bool:
    return any(hint in model_id.lower() for hint in MOE_HINTS)


def fetch_live_openrouter_models() -> list:
    resp = httpx.get("https://openrouter.ai/api/v1/models", timeout=20.0)
    resp.raise_for_status()
    return resp.json().get("data", [])


def build_registry() -> dict:
    live_models = fetch_live_openrouter_models()
    live_ids = {m["id"] for m in live_models}
    registry = {"updated_at": datetime.utcnow().isoformat(), "roles": {}, "live_model_count": len(live_models)}

    for role, criteria in ROLE_CRITERIA.items():
        scored = []
        for m in live_models:
            model_id = m.get("id", "")
            pricing = m.get("pricing", {})
            context_len = m.get("context_length", 0)
            try:
                input_price = float(pricing.get("prompt", "999")) * 1_000_000
            except (ValueError, TypeError):
                continue
            if input_price > criteria["max_input_price"]:
                continue
            if context_len < criteria["min_context"]:
                continue
            if criteria["prefer_moe"] and not _is_moe(model_id):
                continue
            if model_id.startswith("~") or "/" not in model_id:
                continue
            if ":free" in model_id:
                continue
            scored.append((input_price, model_id))

        scored.sort(key=lambda x: x[0])
        top_candidates = [mid for _, mid in scored[:4]]
        for fb in FALLBACK_DEFAULTS[role]:
            if fb in live_ids and fb not in top_candidates:
                top_candidates.append(fb)
        if not top_candidates:
            top_candidates = FALLBACK_DEFAULTS[role]
        registry["roles"][role] = top_candidates[:5]

    return registry


def save_registry(registry: dict):
    r = redis_lib.Redis(
        host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT", 6379)),
        password=os.getenv("REDIS_PASSWORD"), decode_responses=True,
    )
    r.setex(REGISTRY_KEY, REGISTRY_TTL, json.dumps(registry))


def load_registry() -> dict:
    try:
        r = redis_lib.Redis(
            host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD"), decode_responses=True,
        )
        raw = r.get(REGISTRY_KEY)
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return {"updated_at": None, "roles": FALLBACK_DEFAULTS, "live_model_count": 0}


def get_candidates_for_role(role: str) -> list:
    registry = load_registry()
    candidates = registry.get("roles", {}).get(role)
    if not candidates:
        candidates = FALLBACK_DEFAULTS.get(role, FALLBACK_DEFAULTS["analyst"])
    return candidates


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print("OpenRouter canli model listesi taraniyor...")
    reg = build_registry()
    save_registry(reg)
    print("Registry guncellendi:", reg["updated_at"])
    print("Canli model sayisi:", reg["live_model_count"])
    for role, models in reg["roles"].items():
        print(f"  {role}: {models}")

def load_paket_registry(paket: str = "premium") -> dict:
    """Ajan-tabanli, paket-bazli registry'yi okur. Yoksa eski sisteme duser."""
    try:
        r = redis_lib.Redis(
            host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD"), decode_responses=True,
        )
        raw = r.get(PAKET_ANAHTAR_SABLONU.format(paket=paket))
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


def _ham_adaylar(role: str, paket: str = "premium") -> list:
    """Cesitlendirme UYGULANMADAN onceki ham aday listesi."""
    reg = load_paket_registry(paket)
    if reg:
        candidates = reg.get("roles", {}).get(role)
        if candidates and isinstance(candidates, list) and len(candidates) > 0:
            return candidates
    return get_candidates_for_role(role)


# ===========================================================================
# ROL CESITLENDIRMESI (25.08.2026) — "kaskad tek modele cokmus" duzeltmesi
# ===========================================================================
# TESPIT (canli olcum, varsayim degil): kayit defteri UC ROLUN DE ilk adayini
# ayni model olarak donduruyordu:
#     analyst -> ['nvidia/nemotron-3-super-120b-a12b', 'deepseek/deepseek-v4-flash', ...]
#     critic  -> ['nvidia/nemotron-3-super-120b-a12b', 'deepseek/deepseek-v4-flash', ...]
#     master  -> ['nvidia/nemotron-3-super-120b-a12b', 'deepseek/deepseek-v4-flash', ...]
# cascade.py:83-92'deki _call_with_fallback ILK BASARILI modelde donduğu icin
# pratikte Analist, Elestirmen ve Usta AYNI MODEL oluyordu. Yani "3 asamali
# cok modelli kaskad" uretimde tek modelin kendi taslagini kendisinin
# elestirmesine cokmustu.
#
# NEDEN COKTU: ROLE_CRITERIA'daki uc rolun olcutleri birbirine cok yakin
# (analyst/master max_input_price 0.20, critic 1.00; ucu de min_context
# 900000 ve prefer_moe True). Ayni siralama olcutu -> ayni tepe model.
# Statik FALLBACK_DEFAULTS bunu ZATEN istememisti: orada critic listesi
# 'google/gemini-2.5-flash' ile basliyordu. Dinamik katman bu ayrimi
# eziyordu.
#
# NEDEN ONEMLI (karpathy/llm-council'dan alinan asil ders): LLM Council'in
# tum varsayimi, cevabi YAZAN model ile DEGERLENDIREN modelin FARKLI olmasi.
# Ayni model kendi uretim tarzini makul bulmaya egilimlidir; cagrilar
# durumsuz olsa (cascade.py:66, tek 'user' mesaji, gecmis yok) ve model
# "bunu ben yazdim" diye BILMESE bile ayni agirliklar ayni koru noktalari
# tasir. Anonimlestirme bu sorunu cozmez — model CESITLILIGI cozer.
#
# EK MALIYET: SIFIR. Cagri sayisi degismiyor (yine 3). Dahasi OpenRouter
# canli fiyatlarina gore elestirmeni 2. sıradaki modele almak DAHA UCUZ:
#     nvidia/nemotron-3-super-120b-a12b : cikis $0.40 / 1M token
#     deepseek/deepseek-v4-flash        : cikis $0.177 / 1M token
#
# GUVENLIK: liste ASLA kisaltilmiyor, yalnizca SIRASI degistiriliyor. Yani
# fallback zinciri aynen korunuyor; farkli model cevap vermezse eski tepe
# model yine sirada ve devreye giriyor. Tek aday varsa hicbir sey yapilmaz.

# Hangi rol, hangi rolden FARKLI bir tepe model kullanmali.
CESITLENDIRME = {
    "critic": "analyst",   # elestirmen, taslagi yazanla ayni model olmasin
}


def _farklilastir(adaylar: list, kacinilacak: str) -> list:
    """
    `kacinilacak` modeli listenin BASINDAN alir, arkaya tasir.

    Liste kisalmaz: eleman sayisi ve tum adaylar korunur, yalnizca sira
    degisir. Boylece fallback dayanikliligi birebir ayni kalir.
    """
    if not adaylar or len(adaylar) < 2 or not kacinilacak:
        return adaylar
    if adaylar[0] != kacinilacak:
        return adaylar                      # zaten farkli, dokunma
    farkli = [m for m in adaylar if m != kacinilacak]
    if not farkli:
        return adaylar                      # hepsi ayni model, yapacak sey yok
    return farkli + [m for m in adaylar if m == kacinilacak]


def get_candidates_for_role_paketli(role: str, paket: str = "premium") -> list:
    """
    Rol icin aday model listesi.

    Elestirmen rolunde, analistin tepe modeli listenin basindan alinip arkaya
    tasinir (bkz. yukaridaki ROL CESITLENDIRMESI notu). Herhangi bir sorunda
    ham liste oldugu gibi dondurulur — mevcut davranis hicbir kosulda bozulmaz.
    """
    adaylar = _ham_adaylar(role, paket)
    hedef = CESITLENDIRME.get(role)
    if not hedef:
        return adaylar
    try:
        digerinin_adaylari = _ham_adaylar(hedef, paket)
        if not digerinin_adaylari:
            return adaylar
        return _farklilastir(adaylar, digerinin_adaylari[0])
    except Exception as e:
        print(f"[model_registry] cesitlendirme basarisiz, ham liste kullanilyor: {e}",
              flush=True)
        return adaylar
