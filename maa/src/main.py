from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
import json
import asyncio
import psycopg2
import redis
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ALPHAWISE - MAA (Master Analysis Agent)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        dbname=os.getenv("DB_NAME"),
    )

def get_redis_connection():
    return redis.Redis(
        host=os.getenv("REDIS_HOST"),
        port=os.getenv("REDIS_PORT"),
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True,
    )

AGENTS = {
    "taa": os.getenv("TAA_URL"),
    "faa": os.getenv("FAA_URL"),
    "raa": os.getenv("RAA_URL"),
    "saa": os.getenv("SAA_URL"),
}

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

PORTFOLIO_TICKERS_DEFAULT = ["JEPI", "SCHD", "O", "NVDA", "ASML", "TSM", "WDC", "GOOGL", "LLY", "CAT"]


def get_saved_portfolio_tickers():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT ticker FROM user_portfolio ORDER BY added_at ASC")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [r[0] for r in rows]
    except Exception:
        return []


@app.get("/portfolio/tickers")
def get_portfolio_tickers():
    """Kayitli portfoy listesini dondurur. Bos ise, hic secim yapilmamis demektir."""
    tickers = get_saved_portfolio_tickers()
    return {"tickers": tickers, "is_empty": len(tickers) == 0}


@app.post("/portfolio/tickers")
def save_portfolio_tickers(payload: dict):
    """Portfoy listesini komple degistirir. payload: {"tickers": ["AAPL", "NVDA", ...]}"""
    tickers = payload.get("tickers", [])
    tickers = [t.strip().upper() for t in tickers if t.strip()]

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM user_portfolio")
        for t in tickers:
            cur.execute("INSERT INTO user_portfolio (ticker) VALUES (%s) ON CONFLICT (ticker) DO NOTHING", (t,))
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "ok", "tickers": tickers}
    except Exception as e:
        return {"status": "error", "error": str(e)}


PORTFOLIO_TICKERS = PORTFOLIO_TICKERS_DEFAULT

LEGAL_DISCLAIMER = (
    "YASAL UYARI: Bu icerik yatirim danismanligi degildir, ALPHAWISE lisansli bir "
    "yatirim danismani/araci kurum degildir. Burada sunulan tum sayilar gecmis verilere "
    "dayali istatistiksel bir tahmindir; gelecekteki gercek sonuclar farkli olabilir, "
    "sermaye kaybi dahil. Yatirim kararlarinizi vermeden once lisansli bir finansal "
    "danismana danisin. Gecmis performans gelecegin garantisi degildir."
)


def calculate_scenario_range(annual_return, annual_volatility, years, allocation):
    import math
    if annual_return is None or annual_volatility is None or years <= 0 or allocation <= 0:
        return None
    mu = annual_return
    sigma = max(annual_volatility, 0.01)
    log_mean_annual = math.log(1 + mu) - 0.5 * (sigma ** 2)
    mean_t = years * log_mean_annual
    sd_t = sigma * math.sqrt(years)
    z10, z50, z90 = -1.2816, 0.0, 1.2816
    bad = allocation * math.exp(mean_t + z10 * sd_t)
    median = allocation * math.exp(mean_t + z50 * sd_t)
    good = allocation * math.exp(mean_t + z90 * sd_t)
    return {
        "bad_case": round(bad, 2),
        "median_case": round(median, 2),
        "good_case": round(good, 2),
    }

@app.post("/budget-scenario")
async def budget_scenario(payload: dict):
    import numpy as np
    import math
    if not OPENROUTER_API_KEY:
        return {"error": "OPENROUTER_API_KEY tanimli degil"}
    budget = payload.get("budget")
    years = payload.get("years", 5)
    tickers = payload.get("tickers")
    if not budget or budget <= 0:
        return {"error": "Gecerli bir butce belirtilmedi"}
    if not tickers:
        tickers = get_saved_portfolio_tickers() or PORTFOLIO_TICKERS_DEFAULT
    tickers = [t.strip().upper() for t in tickers if t.strip()]
    if not tickers:
        return {"error": "Gecerli hisse bulunamadi"}
        
    n_assets = len(tickers)
    allocation_per_ticker = budget / n_assets

    async def analyze_one(ticker):
        raw = await gather_agent_data(ticker)
        raa = raw.get("raa", {})
        annual_return = raa.get("long_term_cagr_5y_shrunk_estimate")
        if annual_return is None:
            annual_return = raa.get("annualized_return")
        annual_vol = raa.get("annualized_volatility")
        scenario = calculate_scenario_range(annual_return, annual_vol, years, allocation_per_ticker)
        return {
            "ticker": ticker,
            "allocation": round(allocation_per_ticker, 2),
            "annual_return_historical": annual_return,
            "annual_volatility_historical": annual_vol,
            "scenario": scenario,
        }

    ticker_results = await asyncio.gather(*[analyze_one(t) for t in tickers])
    
    returns_list = []
    vols_list = []
    valid_ticker_results = []
    for r in ticker_results:
        if r["scenario"] is not None and r["annual_return_historical"] is not None and r["annual_volatility_historical"] is not None:
            returns_list.append(r["annual_return_historical"])
            vols_list.append(r["annual_volatility_historical"])
            valid_ticker_results.append(r)
            
    n_valid = len(valid_ticker_results)
    if n_valid == 0:
        return {"error": "Simulasyon icin yeterli veri toplanamadi."}

    corr_matrix = np.full((n_valid, n_valid), 0.35)
    np.fill_diagonal(corr_matrix, 1.0)
    vols_array = np.array(vols_list)
    cov_matrix = corr_matrix * np.outer(vols_array, vols_array)
    
    n_simulations = 10000
    mean_zeros = np.zeros(n_valid)
    try:
        shocks = np.random.multivariate_normal(mean_zeros, cov_matrix, size=(n_simulations, years))
        total_shocks = np.sum(shocks, axis=1)
    except Exception:
        total_shocks = np.random.normal(0, 1, size=(n_simulations, n_valid)) * vols_array * math.sqrt(years)

    drifts = (np.array(returns_list) - 0.5 * (vols_array ** 2)) * years
    portfolio_final_values = np.zeros(n_simulations)
    
    for i in range(n_simulations):
        sim_asset_values = allocation_per_ticker * np.exp(drifts + total_shocks[i])
        portfolio_final_values[i] = np.sum(sim_asset_values)

    total_bad = float(np.percentile(portfolio_final_values, 10))
    total_median = float(np.percentile(portfolio_final_values, 50))
    total_good = float(np.percentile(portfolio_final_values, 90))

    portfolio_summary = "\n".join([
        f"{r['ticker']}: tahsis=${r['allocation']}, gecmis_yillik_getiri={r['annual_return_historical']}, "
        f"gecmis_yillik_oynaklik={r['annual_volatility_historical']}, "
        f"tekil_senaryo(kotu/medyan/iyi)={r['scenario']}"
        for r in valid_ticker_results
    ])

    prompt = f'''Sen kidemli bir finansal analistsin. Bir yatirimci ${budget} butcesini
asagidaki hisselere esit dagitmak ve {years} yil beklemek istiyor. Her hisse icin
GECMIS verilere dayali istatistiksel senaryo hesaplandi:

{portfolio_summary}

PORTFOY TOPLAMI ({years} yil sonunda, ${budget} baslangicla, varliklar arasi 0.35 korelasyon varsayimiyla 10.000 iterasyonlu Monte Carlo simulasyonu sonucunda):
- Kotu senaryo (%10 ihtimal bundan daha kotu): ${total_bad:.2f}
- Medyan senaryo (%50 ihtimal): ${total_median:.2f}
- Iyi senaryo (%10 ihtimal bundan daha iyi): ${total_good:.2f}

KRITIK KURALLAR:
1. Bu sayilar SADECE GECMIS verilere dayali istatistiksel bir tahmindir, GARANTI DEGILDIR.
2. Portfoy toplami hesaplamasi tekil hisseleri duz toplamak yerine, hisseler arasindaki gercekci bir korelasyon katsayisini (0.35) dikkate alan gelismis bir Monte Carlo simulasyonuna dayanmaktadir - bunu acikca belirt.
3. Her rakamin yaninda "yani..." aciklamasi ekle, ciplak rakam birakma.

TURKCE olarak IKI BOLUM uret:
## SADE OZET
Sokaktaki bir insan icin acikla.

## DETAYLI TEKNIK RAPOR
Korelasyonlu log-normal Monte Carlo varsayimini teknik detayla acikla.

Yaniti MUTLAKA su cumleyle BASLAT ve su cumleyle BITIR (aynen kullan):
{LEGAL_DISCLAIMER}'''

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
                json={"model": OPENROUTER_MODEL, "messages": [{"role": "user", "content": prompt}]},
            )
            result = resp.json()
        if "choices" not in result:
            return {"error": "LLM yanit vermedi"}
        return {
            "budget": budget,
            "years": years,
            "tickers": [r["ticker"] for r in valid_ticker_results],
            "ticker_breakdown": valid_ticker_results,
            "portfolio_total_scenario": {
                "bad_case": round(total_bad, 2),
                "median_case": round(total_median, 2),
                "good_case": round(total_good, 2),
            },
            "narrative": result["choices"][0]["message"]["content"],
            "legal_disclaimer": LEGAL_DISCLAIMER,
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/health")
def health():
    status = {"service": "MAA", "status": "ok", "checks": {}}
    try:
        conn = get_db_connection()
        conn.close()
        status["checks"]["database"] = "connected"
    except Exception as e:
        status["checks"]["database"] = f"error: {str(e)}"
        status["status"] = "degraded"
    try:
        r = get_redis_connection()
        r.ping()
        status["checks"]["redis"] = "connected"
    except Exception as e:
        status["checks"]["redis"] = f"error: {str(e)}"
        status["status"] = "degraded"
    status["checks"]["openrouter_key"] = "set" if OPENROUTER_API_KEY else "missing"
    return status

@app.get("/agents/health")
async def agents_health():
    results = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, url in AGENTS.items():
            try:
                resp = await client.get(f"{url}/health")
                results[name] = resp.json()
            except Exception as e:
                results[name] = {"status": "unreachable", "error": str(e)}
    return results


def score_taa(data):
    if not data or "error" in data:
        return None
    score = 0
    rsi = data.get("rsi_14")
    sma20 = data.get("sma_20")
    sma50 = data.get("sma_50")
    last_close = data.get("last_close")
    vol_ratio = data.get("volume_ratio")
    sr = data.get("support_resistance") or {}
    resistance = sr.get("resistance")
    support = sr.get("support")

    if rsi is not None:
        if rsi < 30:
            score += 1
        elif rsi > 70:
            score -= 1
    if sma20 is not None and sma50 is not None:
        score += 1 if sma20 > sma50 else -1
    if last_close is not None and resistance is not None and support is not None and resistance > support:
        position = (last_close - support) / (resistance - support)
        if position < 0.25:
            score += 1
        elif position > 0.85:
            score -= 1
    if vol_ratio is not None and vol_ratio > 1.5:
        score += 1 if score >= 0 else -1
    return score


def score_faa(data):
    if not data or "error" in data:
        return None
    score = 0
    pe = data.get("pe_ratio")
    roe = data.get("roe")
    div_yield = data.get("dividend_yield")
    consensus = data.get("analyst_consensus") or {}
    current_price = consensus.get("current_price")
    target_mean = consensus.get("target_mean_price")
    rec_mean = consensus.get("recommendation_mean")

    if pe is not None and 0 < pe < 25:
        score += 1
    if roe is not None and roe > 0.15:
        score += 1
    if div_yield is not None and div_yield > 0:
        score += 1
    if current_price is not None and target_mean is not None and current_price > 0:
        upside = (target_mean - current_price) / current_price
        if upside > 0.15:
            score += 1
        elif upside < -0.05:
            score -= 1
    if rec_mean is not None:
        if rec_mean <= 2.0:
            score += 1
        elif rec_mean >= 3.5:
            score -= 1
    return score


def score_raa(data):
    if not data or "error" in data:
        return None
    score = 0
    sharpe = data.get("sharpe_ratio")
    max_dd = data.get("max_drawdown")
    if sharpe is not None:
        if sharpe > 1:
            score += 1
        elif sharpe < 0:
            score -= 1
    if max_dd is not None and max_dd < -0.30:
        score -= 1
    return score


def score_saa(data):
    if not data or "error" in data:
        return None
    sentiment = data.get("overall_sentiment")
    if sentiment == "positive":
        return 1
    elif sentiment == "negative":
        return -1
    return 0


async def gather_agent_data(ticker: str):
    raw = {}
    async with httpx.AsyncClient(timeout=20.0) as client:
        for name in ["taa", "faa", "raa", "saa"]:
            url = AGENTS[name]
            try:
                if name == "saa":
                    resp = await client.get(f"{url}/analyze/{ticker}", params={"max_news": 5})
                else:
                    resp = await client.get(f"{url}/analyze/{ticker}")
                raw[name] = resp.json()
            except Exception as e:
                raw[name] = {"error": str(e)}
    return raw


SCORE_MEANINGS = {
    "EKLE": "Skor 4 ve uzeri: Coklu katmanlarda (Teknik/Temel/Risk/Duygu) guclu pozitif konfluans.",
    "TUT": "Skor -3 ile 3 arasi: Karisik veya notr sinyaller, net bir yon yok.",
    "DIKKAT ET": "Skor -3 ve altinda: Coklu katmanlarda negatif sinyal birikimi, risk artmis.",
    "BEKLE": "4 katmandan (TAA/FAA/RAA/SAA) 3'ten azi yanit verdi, Confluence over Confidence prensibi geregi karar verilemiyor.",
}


async def decide_for_ticker(ticker: str):
    raw = await gather_agent_data(ticker)

    scores = {
        "taa": score_taa(raw.get("taa")),
        "faa": score_faa(raw.get("faa")),
        "raa": score_raa(raw.get("raa")),
        "saa": score_saa(raw.get("saa")),
    }

    valid_scores = {k: v for k, v in scores.items() if v is not None}
    layers_available = len(valid_scores)

    if layers_available < 3:
        decision = "BEKLE"
        reason = f"Yetersiz veri katmani ({layers_available}/4) - Confluence over Confidence prensibi geregi karar verilemiyor"
        total_score = None
    else:
        total_score = sum(valid_scores.values())
        if total_score <= -3:
            decision = "DIKKAT ET"
            reason = f"Coklu katmanlarda negatif sinyal birikimi (skor: {total_score})"
        elif total_score >= 4:
            decision = "EKLE"
            reason = f"Coklu katmanlarda guclu pozitif konfluans (skor: {total_score})"
        else:
            decision = "TUT"
            reason = f"Karisik veya notr sinyaller (skor: {total_score})"

    return {
        "ticker": ticker,
        "decision": decision,
        "reason": reason,
        "score_meaning": SCORE_MEANINGS.get(decision, ""),
        "layers_available": layers_available,
        "total_score": total_score,
        "layer_scores": scores,
        "raw_data": raw,
    }


@app.get("/decide/{ticker}")
async def decide(ticker: str):
    return await decide_for_ticker(ticker)


@app.get("/narrative/{ticker}")
async def narrative(ticker: str):
    """
    TAA+FAA+RAA+SAA verisini toplayip, OpenRouter uzerinden ucretsiz
    nemotron modeline gonderip, gercek haber basliklarini isimlendiren,
    her teknik noktayi "ne demek + ne yapmali" seklinde aciklayan,
    portfoy baglaminda konumlandiran kapsamli bir analiz uretir.
    """
    if not OPENROUTER_API_KEY:
        return {"error": "OPENROUTER_API_KEY tanimli degil (.env dosyasini kontrol edin)"}

    raw = await gather_agent_data(ticker)

    saa_data = raw.get("saa", {})
    news_details = saa_data.get("details", [])
    news_summary = "\n".join([
        f"- \"{n.get('title', '')}\" (etiket: {n.get('label', '')}, skor: {n.get('score', '')})"
        for n in news_details
    ]) if news_details else "Haber verisi yok."

    is_in_portfolio = ticker.upper() in PORTFOLIO_TICKERS

    prompt = f"""Sen kidemli bir finansal analistsin ve uzun vadeli (5-6 yillik), aylik $4.000
temettu geliri hedefleyen bireysel bir yatirimciya danismanlik yapiyorsun. Asagida {ticker}
hissesi icin 4 farkli analiz katmanindan (Teknik, Temel, Risk, Duygu) toplanmis ham veri var.

TEKNIK ANALIZ (TAA): {json.dumps(raw.get('taa', {}), ensure_ascii=False)}
TEMEL ANALIZ (FAA): {json.dumps(raw.get('faa', {}), ensure_ascii=False)}
RISK ANALIZI (RAA): {json.dumps(raw.get('raa', {}), ensure_ascii=False)}
DUYGU ANALIZI (SAA) - SKOR: {json.dumps({k: v for k, v in saa_data.items() if k != 'details'}, ensure_ascii=False)}
DUYGU ANALIZI - GERCEK HABER BASLIKLARI:
{news_summary}

Bu hisse kullanicinin sabit 10 hisselik portfoyunde mi (JEPI, SCHD, O, NVDA, ASML, TSM, WDC, GOOGL, LLY, CAT): {is_in_portfolio}

KRITIK KURAL: Her teknik/finansal terimi veya rakami kullandiginda, HEMEN ARKASINDAN parantez icinde
"yani..." diye baslayan bir cumleyle sade Turkce'de ne anlama geldigini ve kullaniciyi ne yapmasi
gerektigi konusunda nasil etkiledigini acikla. Cikte hicbir zaman ciplak bir rakam/terim birakma.

Haber basliklarini degerlendirirken GENEL/BELIRSIZ ifadeler kullanma. HANGI HABERIN spesifik olarak
ne anlama geldigini, fiyati nasil etkileyebilecegini somut olarak acikla.

Bu veriye dayanarak TURKCE olarak IKI ANA BOLUM uret. Ciktiyi tam olarak asagidaki basliklarla ayir:

## SADE OZET

Bu bolum, borsa hakkinda hicbir teknik bilgisi olmayan sokaktaki sıradan bir insan icin yazilacak.
KESINLIKLE su terimleri ciplak KULLANMA (aciklamasiz): RSI, MACD, SMA, Fibonacci, Sharpe, Sortino,
Beta, ATR, VaR, P/E, ROE, EBITDA, volatilite - eger kullanacaksan HER ZAMAN yaninda sade aciklamasini ver.
Su sirayla, kisa paragraflar halinde yaz:
- Simdi Ne Durumda: hisse su an yukseliyor mu dusuyor mu, kisaca neden
- Guncel Haberler Ne Diyor: gercek haber basliklarindan 1-2 tanesini ismen belirt, ne anlama geldigini acikla
- Uzmanlar Ne Diyor: analistlerin genel gorusu ve fiyat beklentisi, sade sekilde
- Riski Ne Kadar: bu hisse "sakin" mi yoksa "inişli cikisli" mi, kime uygun
- Portfoydeki Rolu (sadece is_in_portfolio=True ise yaz): bu hisse 10'lu portfoyde hangi rolu
  oynuyor (temettu motoru mu / buyume motoru mu / risk dengeleyici mi)
- Ne Yapmali: uzun vadeli dusunen sıradan bir yatirimci icin somut, anlasilir bir tavsiye
- Karar: EKLE / TUT / BEKLE / DIKKAT ET karari 1 cumleyle, neden oldugunu sade dille aciklayarak

## DETAYLI TEKNIK RAPOR

Bu bolum profesyonel yatirimcilar icin ama YINE DE her rakamin/terimin "ne demek + ne yapmali"
aciklamasi olmali - CIPLAK RAKAM YASAK.

1. AKSIYON PLANI (Trend Yonu, Giris Araligi, Hedef Fiyat, Stop-Loss, Bekleme Suresi, Net Tavsiye - her biri icin kisa aciklama)
2. HABER VE PIYASA ANALIZI: Her haber basligini tek tek degerlendir
3. SWOT ANALIZI (her madde "rakam + ne anlama geldigi + etkisi" seklinde)
4. SENARYO ANALIZI (Boga/Temel/Ayi, olasilik toplam %100, her senaryo icin aksiyon notu)
5. UZUN VADELI PORTFOY STRATEJISI (sadece is_in_portfolio=True ise): agirlik ne zaman artirilmali/azaltilmali

Sadece verilen sayisal veriye dayan, spekulasyon yapma, veri yoksa "veri yetersiz" de. Net yaz
ama HICBIR ZAMAN aciklamasiz rakam/terim birakma."""

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            result = resp.json()

        if "choices" not in result:
            return {"ticker": ticker, "error": "LLM yanit vermedi", "raw_response": result}

        content = result["choices"][0]["message"]["content"]
        return {"ticker": ticker, "narrative": content}

    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


@app.get("/portfolio")
async def portfolio_analysis():
    """
    Sabit 10 hisseli portfoyu (JEPI, SCHD, O, NVDA, ASML, TSM, WDC, GOOGL, LLY, CAT)
    birlikte analiz eder, $4.000/ay temettu hedefine gore genel durumu degerlendirir.
    """
    if not OPENROUTER_API_KEY:
        return {"error": "OPENROUTER_API_KEY tanimli degil"}

    active_tickers = get_saved_portfolio_tickers() or PORTFOLIO_TICKERS_DEFAULT
    results = await asyncio.gather(*[decide_for_ticker(t) for t in active_tickers])
    portfolio_data = {r["ticker"]: r for r in results}

    summary_lines = []
    for t in PORTFOLIO_TICKERS:
        r = portfolio_data[t]
        faa = r.get("raw_data", {}).get("faa", {})
        div_yield = faa.get("dividend_yield")
        sector = faa.get("sector")
        summary_lines.append(
            f"{t}: karar={r['decision']}, skor={r['total_score']}, "
            f"temettu_verimi={div_yield}, sektor={sector}"
        )
    portfolio_summary = "\n".join(summary_lines)

    prompt = f"""Sen kidemli bir portfoy yoneticisisin. Asagida bir yatirimcinin sabit 10 hisselik
portfoyunun her biri icin ayri ayri yapilmis analiz sonuclari var:

{portfolio_summary}

YATIRIMCI PROFILI:
- Baslangic sermayesi: yaklasik $7.100
- Aylik katki plani: $750-1.000/ay + her 4 ayda bir ek $17.500
- Hedef: 5-6 yil icinde aylik $4.000 temettu geliri elde etmek
- Yatirimci uzun vadeli dusunuyor, kisa vadeli spekulasyon yapmiyor

KRITIK KURAL: Her terimi/rakami "yani..." aciklamasiyla birlikte ver, ciplak rakam/terim birakma.

TURKCE olarak IKI ANA BOLUM uret, basliklari AYNEN kullan:

## SADE OZET

Sokaktaki sıradan bir insan icin, jargon kullanmadan (kullanirsan aciklamasiyla):
- Genel Durum: portfoyun genel sagligi nasil (kac tanesi EKLE, kac tanesi TUT, kac tanesi DIKKAT ET)
- Gelir mi Buyume mi: portfoyde kac hisse temettu (gelir) motoru, kac tanesi buyume motoru - dengeli mi
- Hedefe Ne Kadar Yakinsiniz: bu katki planiyla 5-6 yilda $4.000/ay hedefine ulasma potansiyeli hakkinda
  genel bir degerlendirme (kesin sayi vermek zorunda degilsin ama yonelim yorumu yap)
- Dikkat Edilmesi Gerekenler: hangi hisse(ler) su an dikkat gerektiriyor, neden
- Ne Yapmali: bu ay/bu ceyrek icin somut, basit 2-3 aksiyon onerisi

## DETAYLI TEKNIK RAPOR

1. PORTFOY SAGLIGI: her hissenin durumu tek tek kisa yorumla (karar+skor+ne anlama geldigi)
2. CESITLENDIRME ANALIZI: sektor yogunlasmasi var mi, risk dagilimi nasil
3. GELIR VS BUYUME DENGESI: temettu getiren hisseler (JEPI/SCHD/O gibi) ile buyume hisseleri
   (NVDA/ASML/TSM gibi) arasindaki denge, $4000/ay hedefine uygunlugu
4. YENIDEN DENGELEME ONERILERI: hangi hissenin agirligi artirilmali/azaltilmali, neden
5. 5-6 YILLIK YOL HARITASI: bu portfoyle hedefe ulasma stratejisi, hangi asamada ne yapilmali

Sadece verilen veriye dayan, veri yetersizse belirt. Net ve eyleme donusturulebilir yaz."""

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            result = resp.json()

        if "choices" not in result:
            return {"tickers": portfolio_data, "error": "LLM yanit vermedi", "raw_response": result}

        content = result["choices"][0]["message"]["content"]
        return {"tickers": portfolio_data, "portfolio_narrative": content}

    except Exception as e:
        return {"tickers": portfolio_data, "error": str(e)}
