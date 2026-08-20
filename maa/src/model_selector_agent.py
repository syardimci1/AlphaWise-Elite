"""
ALPHAWISE - AJAN TABANLI MODEL SECICI (18.08.2026)
Ucretsiz guclu bir MoE modeli (Nemotron Ultra), OpenRouter'in guncel
listesini inceleyip her kaskad katmani icin en uygun modeli SECER.
5 KATMANLI SAVUNMA: her asamada basarisizlik bir alt katmana duser,
sistem HICBIR kosulda cokmez.
"""
import json, os, urllib.request, urllib.error
import model_registry

SELECTOR_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3.5-lightning:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
]

KATMAN_TANIMLARI = """
1. ANALYST: Ham finansal veri + bilgi tabani baglamindan SIFIRDAN uzun,
   detayli bir hisse analizi yazar. En uzun cikti, en yuksek yaratici
   muhakeme. Kalitesi tum zinciri belirler. AGIR IS.
2. CRITIC: Hazir bir taslagi 4 net maddeye gore denetler (halusinasyon,
   yasakli kelime, karar kodu netligi, ciplak rakam). Kisa cikti,
   kural-eslestirme isi. HAFIF IS.
3. MASTER: Taslak + elestiriyi birlestirip NIHAI, mevzuata tam uyumlu
   metni uretir. Kullaniciya giden son metin. Uyum ihlali riski burada.
   AGIR IS.
"""

def _openrouter_call(model: str, prompt: str, timeout: int = 120) -> str:
    key = os.getenv("OPENROUTER_API_KEY", "")
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    if "choices" not in data:
        hata_mesaji = data.get("error", {}).get("message", str(data)[:200])
        raise RuntimeError(f"OpenRouter hata dondurdu: {hata_mesaji}")
    return data["choices"][0]["message"]["content"]

def _gercek_model_listesi() -> list:
    d = json.loads(urllib.request.urlopen("https://openrouter.ai/api/v1/models", timeout=30).read())["data"]
    return d

# Havuz, filtreleri gecen modelleri OpenRouter'in dondurdugu SABIT sirayla
# ilk 120'ye kesiyor (asagida). Bu siralama fiyat/kaliteye gore degil, API'nin
# katalog sirasina gore; iyi bir model sirf listede geriden geldigi icin
# kesimin disinda kalabilir (orn. nousresearch/hermes-4-70b: filtreleri
# GECIYOR ama 327 aday icinde 222. sirada, kesim disinda kaliyor).
# Genel kesim mantigini degistirmek TUM havuzu etkiler (riskli); bunun yerine
# secilen modeller, filtreyi hala GECMEK sartiyla, kesimden BAGIMSIZ eklenir.
SABIT_ADAYLAR = [
    "nousresearch/hermes-4-70b",
]


def _aday_havuzu(models: list) -> str:
    """Secici ajana sunulacak, makul boyutta bir aday listesi hazirlar."""
    by_id = {m.get("id", ""): m for m in models}
    satirlar = []
    gorulen = set()
    for m in models:
        mid = m.get("id", "")
        if mid.startswith("~") or "/" not in mid:
            continue
        ctx = m.get("context_length", 0)
        if ctx < 100000:
            continue
        try:
            fiyat = float(m.get("pricing", {}).get("prompt", "999")) * 1_000_000
        except (ValueError, TypeError):
            continue
        if fiyat > 3.0:
            continue
        satirlar.append(f"{mid} | baglam:{ctx} | 1M-token-fiyat:${fiyat:.3f}")
        gorulen.add(mid)
    kesilmis = satirlar[:120]
    kesilmis_id = set(satirlar[i].split(" | ")[0] for i in range(len(kesilmis)))

    # Sabit adaylar: filtreyi GECEN ama kesimde YER ALMAYAN varsa ekle.
    # Model kataloktan kalkarsa (id artik yoksa) ya da artik filtreyi
    # gecmiyorsa sessizce atlanir — asla uydurma bir satir eklenmez.
    for aday_id in SABIT_ADAYLAR:
        if aday_id in kesilmis_id:
            continue
        m = by_id.get(aday_id)
        if not m:
            continue
        ctx = m.get("context_length", 0)
        if ctx < 100000:
            continue
        try:
            fiyat = float(m.get("pricing", {}).get("prompt", "999")) * 1_000_000
        except (ValueError, TypeError):
            continue
        if fiyat > 3.0:
            continue
        kesilmis.append(f"{aday_id} | baglam:{ctx} | 1M-token-fiyat:${fiyat:.3f}")

    return "\n".join(kesilmis)

def _prompt_olustur(havuz: str, paket: str = "premium") -> str:
    if paket == "basic":
        paket_kurali = """
PAKET: BASIC (ekonomik plan)
- SADECE ucretsiz (:free) ve UCUZ modeller kullan.
- HICBIR model icin 1M-token fiyati $0.50'yi GECMESIN.
- Premium model KESINLIKLE KULLANMA (yedek olarak bile).
- Mumkun oldugunca :free modelleri tercih et."""
    else:
        paket_kurali = """
PAKET: PREMIUM (kalite plani)
- Birincil modeller F/P optimize olmali ($1.00 tavan).
- Kalite kritik katmanlarda (ANALYST, MASTER) daha guclu modeller secebilirsin.
- Premium model SADECE son yedek (3. sira) olarak kullanilabilir."""
    return f"""Sen bir AI altyapi mimarisin.{paket_kurali} Asagida OpenRouter'da SU AN mevcut modeller var.

MEVCUT MODELLER:
{havuz}

Bir finansal analiz sisteminin 3 katmani icin model secmen gerekiyor:
{KATMAN_TANIMLARI}

KURALLAR (SIKI SEKILDE UY):
- Her katman icin 1 BIRINCIL + 2 YEDEK model sec (toplam 3).
- ANA ILKE: FIYAT/PERFORMANS. Isi yapabilecek EN UCUZ modeli sec.
  Premium (1M-token fiyati $2 uzeri) modeller VARSAYILAN OLARAK KULLANILMAZ.
- BIRINCIL modeller icin 1M-token fiyati $1.00'i GECMEMELI.
- Premium bir modeli sadece SON YEDEK (3. sira) olarak koyabilirsin;
  birincil veya 2. yedek olarak ASLA premium secme.
- CRITIC katmani: BIRINCIL mutlaka UCRETSIZ (:free) bir model olmali.
  Yedekleri de ucuz F/P modeller olsun.
- Qwen ailesini (qwen/*) HIC KULLANMA - altyapimizla uyumlu degil.
- Hepsi HIZLI yanit vermeli (dusuk gecikme onemli).
- SADECE yukaridaki listede GERCEKTEN VAR OLAN model kimliklerini kullan.
- Model kimligini birebir, degistirmeden yaz.

SADECE su JSON formatinda yanit ver, baska HICBIR metin yazma:
{{"analyst": ["model1", "model2", "model3"], "critic": ["model1", "model2", "model3"], "master": ["model1", "model2", "model3"], "gerekce": "kisa aciklama"}}"""

def _json_ayikla(text: str) -> dict:
    """LLM ciktisindan JSON'u guvenli sekilde cikarir (markdown fence vb. temizler)."""
    t = text.strip()
    if "```" in t:
        parts = t.split("```")
        for p in parts:
            p = p.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                t = p
                break
    ilk = t.find("{")
    son = t.rfind("}")
    if ilk == -1 or son == -1:
        raise ValueError("JSON bulunamadi")
    return json.loads(t[ilk:son+1])

PREMIUM_ESIK = 2.0     # 1M-token fiyati bu ustundeyse "premium" sayilir
BIRINCIL_TAVAN = 1.00  # birincil model bu fiyati gecemez

def _fiyat_haritasi(models: list) -> dict:
    h = {}
    for m in models:
        try:
            h[m["id"]] = float(m.get("pricing", {}).get("prompt", "999")) * 1_000_000
        except (ValueError, TypeError, KeyError):
            h[m.get("id", "")] = 999.0
    return h

def _dogrula(oneri: dict, gercek_idler: set, fiyatlar: dict = None, paket: str = "premium") -> dict:
    """KALKAN: (1) model gercekten var mi, (2) Qwen degil mi,
    (3) F/P disiplini - premium model birincil olamaz."""
    fiyatlar = fiyatlar if isinstance(fiyatlar, dict) else {}
    temiz = {}
    for rol in ["analyst", "critic", "master"]:
        liste = oneri.get(rol, [])
        if not isinstance(liste, list):
            continue
        tavan = 0.50 if paket == "basic" else 999.0
        gecerli = [m for m in liste
                   if isinstance(m, str) and m in gercek_idler
                   and not m.startswith("qwen/")
                   and fiyatlar.get(m, 999) <= tavan]
        if not gecerli:
            continue
        # F/P KALKANI: premium modelleri listenin SONUNA it, ucuzu one al
        ucuz = [m for m in gecerli if fiyatlar.get(m, 999) <= BIRINCIL_TAVAN]
        orta = [m for m in gecerli if BIRINCIL_TAVAN < fiyatlar.get(m, 999) <= PREMIUM_ESIK]
        pahali = [m for m in gecerli if fiyatlar.get(m, 999) > PREMIUM_ESIK]
        sirali = ucuz + orta + pahali
        if len(sirali) >= 2:
            temiz[rol] = sirali[:3]
    return temiz

def sec(paket: str = "premium") -> dict:
    """Ana fonksiyon. 5 katmanli savunma ile model secimi yapar."""
    rapor = {"paket": paket, "yontem": None, "gerekce": None, "roller": None, "uyarilar": []}

    # --- Gercek model listesi (bu olmadan hicbir sey yapilamaz) ---
    try:
        models = _gercek_model_listesi()
        gercek_idler = {m["id"] for m in models}
    except Exception as e:
        rapor["yontem"] = "FALLBACK_DEFAULTS (model listesi cekilemedi)"
        rapor["uyarilar"].append(f"OpenRouter listesi alinamadi: {e}")
        rapor["roller"] = model_registry.FALLBACK_DEFAULTS
        return rapor

    havuz = _aday_havuzu(models)
    prompt = _prompt_olustur(havuz, paket)

    # --- KATMAN 1-2: LLM secici (birden fazla ucretsiz model denenir) ---
    for secici in SELECTOR_MODELS:
        try:
            cevap = _openrouter_call(secici, prompt)
            oneri = _json_ayikla(cevap)
            temiz = _dogrula(oneri, gercek_idler, _fiyat_haritasi(models), paket)
            if len(temiz) == 3:      # ucu de gecerliyse kabul
                rapor["yontem"] = f"LLM_SECICI ({secici})"
                rapor["gerekce"] = str(oneri.get("gerekce", ""))[:500]
                rapor["roller"] = temiz
                return rapor
            rapor["uyarilar"].append(f"{secici}: dogrulamayi gecen rol sayisi {len(temiz)}/3")
        except Exception as e:
            import traceback
            rapor["uyarilar"].append(f"{secici} basarisiz: {type(e).__name__}: {e} | {traceback.format_exc().splitlines()[-3:]}")

    # --- KATMAN 3: Sabit kural motoru (mevcut, kanitli sistem) ---
    try:
        reg = model_registry.build_registry()
        roller = reg.get("roles", {})
        if all(roller.get(r) for r in ["analyst", "critic", "master"]):
            rapor["yontem"] = "SABIT_KURAL_MOTORU (LLM secici basarisiz)"
            rapor["roller"] = roller
            return rapor
    except Exception as e:
        rapor["uyarilar"].append(f"Sabit kural motoru basarisiz: {e}")

    # --- KATMAN 4: Son savunma ---
    rapor["yontem"] = "FALLBACK_DEFAULTS (tum katmanlar basarisiz)"
    rapor["roller"] = model_registry.FALLBACK_DEFAULTS
    return rapor

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    import sys
    paket = sys.argv[1] if len(sys.argv) > 1 else 'premium'
    r = sec(paket)
    print('PAKET:', paket.upper())
    print("=" * 60)
    print("YONTEM:", r["yontem"])
    if r.get("gerekce"):
        print("GEREKCE:", r["gerekce"])
    print("-" * 60)
    for rol, modeller in (r["roller"] or {}).items():
        print(f"{rol.upper():10}: {modeller}")
    if r["uyarilar"]:
        print("-" * 60)
        for u in r["uyarilar"]:
            print("UYARI:", u)
    print("=" * 60)
    # Secimi Redis'e yaz (kaskad bunu okuyacak)
    try:
        import redis as _redis_lib, os as _os, json as _json
        reg = {"updated_at": __import__("datetime").datetime.now().isoformat(),
               "roles": r["roller"], "live_model_count": 0, "yontem": r["yontem"],
               "paket": paket}
        _r = _redis_lib.Redis(
            host=_os.getenv("REDIS_HOST"), port=int(_os.getenv("REDIS_PORT", 6379)),
            password=_os.getenv("REDIS_PASSWORD"), decode_responses=True,
        )
        _r.setex(model_registry.PAKET_ANAHTAR_SABLONU.format(paket=paket), 26*3600, _json.dumps(reg))
        print(f"Redis'e yazildi (paket: {paket}).")
    except Exception as e:
        print("Redis yazma hatasi:", e)
