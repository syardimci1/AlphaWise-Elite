"""
ALPHAWISE 3 Asamali Kaskad: Analyst -> Critic -> Master
Anayasa v4.4'e uygunlugu her asamada kontrol eder.
Her rol icin birden fazla model adayi var (fallback zinciri).
"""
import os
import json
import httpx
from constitution import constitution_check, ensure_disclaimer

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Her rol icin, sirayla denenecek model adaylari (ilki basarisiz olursa digeri denenir)
ANALYST_MODELS = [
    "deepseek/deepseek-chat",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
]
CRITIC_MODELS = [
    "deepseek/deepseek-chat",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
]
MASTER_MODELS = [
    "anthropic/claude-sonnet-4",
    "deepseek/deepseek-chat",
]


async def get_rag_context(query: str, n_results: int = 3):
    """RAG servisinden ilgili finans metodolojisini ceker."""
    rag_url = os.getenv("RAG_URL", "http://rag:8000")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{rag_url}/query", params={"q": query, "n_results": n_results})
            data = resp.json()
            results = data.get("results", [])
            if not results:
                return "Ilgili metodoloji bulunamadi."
            return "\n---\n".join([r.get("content", "")[:600] for r in results])
    except Exception as e:
        return f"RAG servisi su an erisilemiyor: {e}"


async def _call_llm(model: str, prompt: str, timeout: float = 30.0):
    if not OPENROUTER_API_KEY:
        return None, "OPENROUTER_API_KEY tanimli degil"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"model": model, "messages": [{"role": "user", "content": prompt}]},
            )
            result = resp.json()
        if "choices" not in result:
            return None, f"Model yanit vermedi: {result}"
        return result["choices"][0]["message"]["content"], None
    except Exception as e:
        return None, str(e)


async def _call_with_fallback(models: list, prompt: str):
    last_error = None
    for model in models:
        content, error = await _call_llm(model, prompt)
        if content:
            return content, model
        last_error = f"{model}: {error}"
    return None, last_error


def _build_context_block(ticker, raw, macro, llmquant_data, is_in_portfolio):
    saa_data = raw.get("saa", {})
    news_details = saa_data.get("details", [])
    news_summary = "\n".join([
        f"- \"{n.get('title', '')}\" (etiket: {n.get('label', '')}, skor: {n.get('score', '')})"
        for n in news_details
    ]) if news_details else "Haber verisi yok."

    macro_summary = (
        f"Fed Faiz Orani: %{macro.get('fed_funds_rate_pct', 'N/A')}, "
        f"10 Yillik Tahvil Getirisi: %{macro.get('treasury_10y_yield_pct', 'N/A')}, "
        f"Yillik Enflasyon (TUFE): %{macro.get('cpi_yoy_inflation_pct', 'N/A')}, "
        f"Issizlik Orani: %{macro.get('unemployment_rate_pct', 'N/A')}"
    ) if not macro.get("error") else "Makro veri su an alinamadi."

    llmquant_summary = json.dumps(llmquant_data, ensure_ascii=False) if llmquant_data else "LLMQuant verisi yok."

    return f"""
TEKNIK ANALIZ (TAA): {json.dumps(raw.get('taa', {}), ensure_ascii=False)}
TEMEL ANALIZ (FAA): {json.dumps(raw.get('faa', {}), ensure_ascii=False)}
RISK ANALIZI (RAA): {json.dumps(raw.get('raa', {}), ensure_ascii=False)}
DUYGU ANALIZI (SAA) - SKOR: {json.dumps({k: v for k, v in saa_data.items() if k != 'details'}, ensure_ascii=False)}
DUYGU ANALIZI - GERCEK HABER BASLIKLARI:
{news_summary}

GUNCEL MAKRO EKONOMIK DURUM: {macro_summary}

KURUMSAL SAHIPLIK / LIKIDITE VERISI (LLMQuant): {llmquant_summary}

Bu hisse kullanicinin portfoyunde mi: {is_in_portfolio}
"""


ANALYST_INSTRUCTIONS = """
KRITIK KURAL: Her teknik/finansal terimi veya rakami kullandiginda, HEMEN ARKASINDAN parantez icinde
"yani..." diye baslayan bir cumleyle sade Turkce'de ne anlama geldigini acikla. Ciplak rakam/terim birakma.

Cikti KESINLIKLE su karar kodlarindan SADECE BIRINI icermeli: EKLE, TUT, BEKLE, DIKKAT ET.
"al", "sat", "tavsiye" gibi emir bildiren kelimeleri KULLANMA.

Asagidaki basliklarla, TURKCE, iki ana bolum halinde yaz:

## SADE OZET
(Simdi Ne Durumda / Guncel Haberler Ne Diyor / Uzmanlar Ne Diyor / Riski Ne Kadar / Ne Yapmali / Karar)

## DETAYLI TEKNIK RAPOR
(1. Confluence Skoru ve Karar Kodu, 2. Vadeye Bazli Analiz, 3. Senaryo Analizi (Bull/Base/Bear),
4. Portfoy Baglami (varsa), 5. Risk Skor Karti)

Sadece verilen sayisal veriye dayan, spekulasyon yapma.
"""


async def run_cascade(ticker: str, raw: dict, macro: dict, llmquant_data: dict, is_in_portfolio: bool):
    import time
    _t0 = time.time()
    context = _build_context_block(ticker, raw, macro, llmquant_data, is_in_portfolio)
    rag_context = await get_rag_context(f"{ticker} hisse degerleme DCF risk analizi metodolojisi")

    # --- ASAMA 1: ANALYST (taslak yazar) ---
    analyst_prompt = f"""Sen kidemli bir finansal analistsin. {ticker} hissesi icin asagidaki veriyle bir analiz yaz.

ILGILI METODOLOJI REFERANSI (dahili bilgi tabanindan):
{rag_context}

{context}

{ANALYST_INSTRUCTIONS}"""
    draft, analyst_model = await _call_with_fallback(ANALYST_MODELS, analyst_prompt)
    print(f"[TIMING] Analyst asamasi: {time.time()-_t0:.1f}s")
    if not draft:
        return {"ticker": ticker, "error": f"Analyst asamasi basarisiz: {analyst_model}"}

    # --- ASAMA 2: CRITIC (hallucinasyon + Anayasa kontrolu) ---
    critic_prompt = f"""Asagida bir finansal analiz taslagi var. Gorevin bunu ELESTIRMEK, HATA BULMAK:
1. Taslakta, verilen ham veride OLMAYAN bir iddia var mi? (halusinasyon kontrolu)
2. "al", "sat", "tavsiye" gibi emir bildiren kelime var mi?
3. Karar kodu (EKLE/TUT/BEKLE/DIKKAT ET) net ve tek mi?
4. Ciplak, aciklamasiz rakam/terim var mi?

HAM VERI: {context}

TASLAK: {draft}

Eger SORUN YOKSA sadece "SORUN YOK" yaz. Sorun varsa madde madde listele."""
    _t1 = time.time()
    critic_feedback, critic_model = await _call_with_fallback(CRITIC_MODELS, critic_prompt)
    print(f"[TIMING] Critic asamasi: {time.time()-_t1:.1f}s")
    if not critic_feedback:
        critic_feedback = "Critic asamasi basarisiz oldu, kontrolsuz devam ediliyor."

    all_checks_clear = "SORUN YOK" in critic_feedback.upper()

    # --- ASAMA 3: MASTER (nihai sentez) ---
    master_prompt = f"""Asagida bir analiz taslagi ve buna dair elestiri/geri bildirim var.
Gorevin: geri bildirimi dikkate alarak NIHAI, TEMIZ, Anayasa v4.4'e tam uyumlu metni uretmek.

TASLAK: {draft}

ELESTIRI/GERI BILDIRIM: {critic_feedback}

Nihai metni ayni iki bolumlu formatta (## SADE OZET / ## DETAYLI TEKNIK RAPOR) uret.
Elestiride belirtilen sorunlari mutlaka duzelt. "al"/"sat"/"tavsiye" kelimelerini kullanma."""
    _t2 = time.time()
    final_text, master_model = await _call_with_fallback(MASTER_MODELS, master_prompt)
    print(f"[TIMING] Master asamasi: {time.time()-_t2:.1f}s")
    print(f"[TIMING] TOPLAM kaskad: {time.time()-_t0:.1f}s")
    if not final_text:
        final_text = draft  # Master basarisiz olursa, en azindan Analyst taslagini don
        master_model = "FALLBACK: analyst_draft_used"

    # --- ANAYASA v4.4 SON KONTROL + HEDEFLI YENIDEN DENEME (13.08.2026) ---
    check = constitution_check(final_text)
    max_retries = 2
    retry_count = 0
    while not check["clear"] and retry_count < max_retries:
        retry_count += 1
        fix_prompt = (
            "Asagidaki metin Anayasa v4.4 kontrolunu GECEMEDI.\n"
            f"TESPIT EDILEN SORUNLAR: {', '.join(check['issues'])}\n"
            f"METIN: {final_text}\n"
            "Gorevin: SADECE bu spesifik sorunlari duzelt, metnin geri kalanini olabildigince koru. "
            "Karar kodu SADECE su 4 kelimeden biri olmali (baska hicbir kelime kullanma): "
            "EKLE, TUT, BEKLE, DIKKAT ET. "
            "al/sat/tavsiye/koru/kar realize et/firsat/ralli/roket kelimelerini KESINLIKLE kullanma."
        )
        retry_text, retry_model = await _call_with_fallback(MASTER_MODELS, fix_prompt)
        if retry_text:
            final_text = retry_text
            master_model = f"{master_model} (duzeltme denemesi {retry_count}: {retry_model})"
            check = constitution_check(final_text)

    final_text = ensure_disclaimer(final_text)

    return {
        "ticker": ticker,
        "narrative": final_text,
        "cascade_meta": {
            "analyst_model": analyst_model,
            "critic_model": critic_model,
            "master_model": master_model,
            "all_checks_clear": all_checks_clear,
            "critic_feedback": critic_feedback,
            "constitution_check": check,
            "retry_count": retry_count,
        },
    }
