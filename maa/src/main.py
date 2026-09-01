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

CHRONOS_URL = "http://chronos:8000"
MARKET_DATA_URL_MAA = "http://market-data:8000"


async def fetch_chronos_forecast(ticker: str):
    """Chronos'tan 5 gunluk fiyat tahmini alir. Fiyat gecmisini merkezi
    market-data servisinden ceker (Fatih Bora onerisi geregi kurulan
    merkezi kaynak - burada da tekrar kullaniliyor)."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            price_resp = await client.get(f"{MARKET_DATA_URL_MAA}/price/{ticker}", params={"limit": 60})
            price_data = price_resp.json()
            rows = price_data.get("data", [])
            if len(rows) < 10:
                return {"error": "yetersiz fiyat gecmisi"}
            closes = [float(r["close"]) for r in rows]

            forecast_resp = await client.post(
                f"{CHRONOS_URL}/forecast",
                json={"prices": closes, "prediction_length": 5},
            )
            return forecast_resp.json()
    except Exception as e:
        return {"error": str(e)}


def score_chronos(data):
    """Chronos'un 5-gunluk ortalama tahminini skora cevirir.
    Beklenen degisim %1'in ustundeyse anlamli sayilir."""
    if not data or "error" in data:
        return None
    mean_forecast = data.get("mean_forecast")
    if not mean_forecast or len(mean_forecast) < 1:
        return None
    current = mean_forecast[0]
    future = mean_forecast[-1]
    if not current:
        return None
    pct_change = (future - current) / current
    if pct_change > 0.01:
        return 1
    elif pct_change < -0.01:
        return -1
    return 0


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

FRED_API_KEY = os.getenv("FRED_API_KEY")
FRED_SERIES = {
    "fed_funds_rate": "FEDFUNDS",
    "treasury_10y_yield": "DGS10",
    "cpi_index": "CPIAUCSL",
    "unemployment_rate": "UNRATE",
}


async def _fetch_fred_series(series_id: str):
    if not FRED_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={
                    "series_id": series_id,
                    "api_key": FRED_API_KEY,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 13,
                },
            )
            data = resp.json()
            obs = data.get("observations", [])
            return obs
    except Exception:
        return None


async def get_macro_context():
    """
    FRED'den makro ekonomik gostergeleri ceker. Redis'te 24 saat onbellekler
    (bu veriler gunluk degismiyor, gereksiz API cagrisi onlenir).
    """
    cache_key = "macro_context_fred"
    try:
        r = get_redis_connection()
        cached = r.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    if not FRED_API_KEY:
        return {"error": "FRED_API_KEY tanimli degil"}

    result = {}

    fed_obs = await _fetch_fred_series(FRED_SERIES["fed_funds_rate"])
    if fed_obs:
        result["fed_funds_rate_pct"] = float(fed_obs[0]["value"])

    treasury_obs = await _fetch_fred_series(FRED_SERIES["treasury_10y_yield"])
    if treasury_obs:
        for o in treasury_obs:
            if o["value"] != ".":
                result["treasury_10y_yield_pct"] = float(o["value"])
                break

    cpi_obs = await _fetch_fred_series(FRED_SERIES["cpi_index"])
    if cpi_obs and len(cpi_obs) >= 13:
        try:
            latest = float(cpi_obs[0]["value"])
            year_ago = float(cpi_obs[12]["value"])
            result["cpi_yoy_inflation_pct"] = round(((latest - year_ago) / year_ago) * 100, 2)
        except Exception:
            pass

    unemployment_obs = await _fetch_fred_series(FRED_SERIES["unemployment_rate"])
    if unemployment_obs:
        result["unemployment_rate_pct"] = float(unemployment_obs[0]["value"])

    result["source"] = "FRED (Federal Reserve Economic Data)"
    result["note"] = "Aylik guncellenen resmi ABD makroekonomik gostergeleri"

    try:
        r = get_redis_connection()
        r.setex(cache_key, 86400, json.dumps(result))
    except Exception:
        pass

    return result


@app.get("/macro-context")
async def macro_context_endpoint():
    """Guncel makro ekonomik baglami dondurur (Fed faizi, tahvil getirisi, enflasyon, issizlik)."""
    return await get_macro_context()

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
    sentiment = data.get("overall")
    if sentiment == "positive":
        return 1
    elif sentiment == "negative":
        return -1
    return 0


# decide_for_ticker'in arka plan (fire-and-forget) gorevleri icin guclu referans
# havuzu. asyncio.create_task yalnizca ZAYIF referans tutar; havuz olmazsa gorev
# tamamlanmadan cop toplayiciya gidebilir. Gorev bitince kendini havuzdan siler.
_ARKA_PLAN_GOREVLERI: set = set()


async def gather_agent_data(ticker: str):
    async def _fetch_one(name):
        url = AGENTS[name]
        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                if name == "saa":
                    resp = await client.get(f"{url}/analyze/{ticker}", params={"max_news": 5})
                else:
                    resp = await client.get(f"{url}/analyze/{ticker}")
                return name, resp.json()
            except Exception as e:
                return name, {"error": str(e)}

    # Chronos'un API sekli farklidir (ticker degil fiyat listesi ister), bu yuzden
    # ayri bir sarmalayici gerekir — ama BEKLEMESI gerekmez. Eskiden gather'dan
    # SONRA await ediliyordu ve olculen ~6 sn'yi (market-data 0.4 + chronos 5.6)
    # dogrudan toplam sureye ekliyordu. Artik digerleriyle AYNI ANDA calisiyor.
    async def _fetch_chronos():
        return "chronos", await fetch_chronos_forecast(ticker)

    results = await asyncio.gather(
        *[_fetch_one(n) for n in ["taa", "faa", "raa", "saa"]],
        _fetch_chronos(),
    )
    return {name: data for name, data in results}


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
        "chronos": score_chronos(raw.get("chronos")),
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

    # --- KARAR GUNLUGU: her karari decision_log tablosuna kaydet ---
    try:
        price_at_decision = None
        taa_data = raw.get("taa", {})
        if isinstance(taa_data, dict):
            price_at_decision = taa_data.get("last_close")

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO decision_log (ticker, decision, total_score, layer_scores, price_at_decision, source) VALUES (%s, %s, %s, %s, %s, %s)",
            (ticker, decision, total_score, json.dumps(scores), price_at_decision, "god_mode"),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as log_error:
        print(f"[decision_log] kayit hatasi (yanit etkilenmedi): {log_error}")

    # --- COGNEE: uzun-vadeli hafizaya kaydet (ARKA PLANDA) ---
    # Bu cagri yalnizca hafiza yazar; sonucu YANITA GIRMEZ ve hatasi zaten
    # yutuluyordu. Buna ragmen await edildigi icin her /decide cagrisini
    # bekletiyordu: olculen sure 3.1 - 15.0 sn arasi degisiyor (cognee soguk
    # baslangicta 15 sn timeout'a kadar cikiyor, sonra 3-5 sn'ye iniyor).
    # Yaniti hicbir sekilde etkilemeyen bir yan etki icin kullaniciyi
    # bekletmenin gerekcesi yok — arka plan gorevine tasindi.
    async def _cognee_kaydet():
        try:
            async with httpx.AsyncClient(timeout=15.0) as cognee_client:
                faa_data = raw.get("faa", {}) if isinstance(raw.get("faa"), dict) else {}
                company_name = faa_data.get("company_name") or "bilinmeyen sirket"
                sector = faa_data.get("sector") or ""
                memory_text = (
                    f"Hisse senedi sembolu {ticker} ({company_name}, sektor: {sector}) "
                    f"icin {decision} karari verildi (skor: {total_score}). "
                    f"Katman skorlari: {scores}."
                )
                await cognee_client.post(
                    "http://cognee:8000/remember",
                    json={"text": memory_text, "dataset": "alphawise_decisions"},
                )
        except Exception as cognee_error:
            print(f"[cognee] kayit hatasi (yanit etkilenmedi): {cognee_error}", flush=True)

    # Goreve GUCLU referans tutulur: asyncio yalnizca zayif referans tuttugu icin
    # referanssiz birakilan gorev calisma ortasinda cop toplayiciya gidebilir.
    _gorev = asyncio.create_task(_cognee_kaydet())
    _ARKA_PLAN_GOREVLERI.add(_gorev)
    _gorev.add_done_callback(_ARKA_PLAN_GOREVLERI.discard)

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
    macro = await get_macro_context()

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

GUNCEL MAKRO EKONOMIK DURUM (ABD, FRED kaynakli):
{macro_summary}
(Bu makro veriyi analizine dahil et: yuksek faiz ortami buyume hisselerini ve REIT'leri
baskilar, yuksek enflasyon tuketici harcamalarini etkiler, vs. - ilgili oldugu yerde belirt.)

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


@app.post("/evaluate-decisions")
async def evaluate_decisions(days_old: int = 30):
    """
    decision_log tablosunda en az `days_old` gun once verilmis ve henuz
    degerlendirilmemis kararlari bulur, guncel fiyatla karsilastirip
    was_correct/pct_change alanlarini doldurur.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, ticker, decision, price_at_decision
            FROM decision_log
            WHERE evaluated_at IS NULL
              AND price_at_decision IS NOT NULL
              AND decided_at <= NOW() - INTERVAL '%s days'
            """,
            (days_old,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        return {"error": f"veritabani okuma hatasi: {e}"}

    if not rows:
        return {"evaluated_count": 0, "message": "Degerlendirilecek yeterlilikte eski karar yok."}

    unique_tickers = list(set(r[1] for r in rows))
    current_prices = {}
    async with httpx.AsyncClient(timeout=20.0) as client:
        for t in unique_tickers:
            try:
                resp = await client.get(f"{AGENTS['taa']}/analyze/{t}")
                data = resp.json()
                current_prices[t] = data.get("last_close")
            except Exception:
                current_prices[t] = None

    updated = 0
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        for (row_id, ticker, decision, price_before) in rows:
            price_now = current_prices.get(ticker)
            if price_now is None or price_before is None or price_before == 0:
                continue
            pct_change = (float(price_now) - float(price_before)) / float(price_before)

            if decision == "EKLE":
                was_correct = pct_change > 0
            elif decision == "DIKKAT ET":
                was_correct = pct_change < 0
            elif decision == "TUT":
                was_correct = abs(pct_change) < 0.15
            else:
                was_correct = None

            cur.execute(
                """
                UPDATE decision_log
                SET price_after = %s, pct_change = %s, was_correct = %s, evaluated_at = NOW()
                WHERE id = %s
                """,
                (price_now, round(pct_change, 4), was_correct, row_id),
            )
            updated += 1
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return {"error": f"veritabani yazma hatasi: {e}", "partial_updated": updated}

    return {"evaluated_count": updated, "days_old_threshold": days_old}


@app.get("/performance-report")
def performance_report():
    """Degerlendirilmis kararlarin karara gore isabet oranini ozetler."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT decision,
                   COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE was_correct = TRUE) AS correct_count,
                   AVG(pct_change) AS avg_pct_change
            FROM decision_log
            WHERE evaluated_at IS NOT NULL AND was_correct IS NOT NULL
            GROUP BY decision
            """
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        return {"error": str(e)}

    report = {}
    for (decision, total, correct_count, avg_pct) in rows:
        accuracy = round((correct_count / total) * 100, 1) if total > 0 else None
        report[decision] = {
            "total_evaluated": total,
            "correct_count": correct_count,
            "accuracy_pct": accuracy,
            "avg_pct_change": round(float(avg_pct), 4) if avg_pct is not None else None,
        }

    return {"performance_by_decision": report}


@app.get("/narrative-verified/{ticker}")
async def narrative_verified(ticker: str, paket: str = "premium"):
    """
    3 asamali kaskad (Analyst->Critic->Master) + Anayasa v4.4 filtresi +
    LLMQuant (13F kurumsal sahiplik + likidite) ile zenginlestirilmis analiz.
    """
    import sys as _sys
    import os as _os
    _sys.path.insert(0, _os.path.dirname(__file__))
    from llmquant_client import get_13f_holders, get_liquidity_context
    from cascade import run_cascade

    is_in_portfolio = ticker.upper() in PORTFOLIO_TICKERS

    raw, macro, holders, liquidity = await asyncio.gather(
        gather_agent_data(ticker),
        get_macro_context(),
        get_13f_holders(ticker),
        get_liquidity_context(),
    )
    llmquant_data = {"institutional_holders": holders, "liquidity": liquidity}

    result = await run_cascade(ticker, raw, macro, llmquant_data, is_in_portfolio, paket)
    # --- KARAR GUNLUGU: KISA VADE karari decision_log'a kaydet (source='llm_cascade') ---
    try:
        import re as _re
        narrative_text = result.get("narrative", "")
        m = _re.search(r"[Kk][İIıi]sa [Vv]ade:?\**\s*(EKLE|TUT|BEKLE|DIKKAT ET)", narrative_text)
        if not m:
            m = _re.search(r"UZUN VADE:\s*(EKLE|TUT|BEKLE|DIKKAT ET)", narrative_text)
        if m:
            karar_kodu = m.group(1)
            taa_data = raw.get("taa", {}) if isinstance(raw.get("taa"), dict) else {}
            fiyat = taa_data.get("last_close")
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO decision_log (ticker, decision, total_score, layer_scores, price_at_decision, source) VALUES (%s, %s, %s, %s, %s, %s)",
                (ticker, karar_kodu, None, __import__("json").dumps(result.get("cascade_meta", {})), fiyat, "llm_cascade"),
            )
            conn.commit()
            cur.close()
            conn.close()
    except Exception as log_error:
        print(f"[decision_log/llm_cascade] kayit hatasi (yanit etkilenmedi): {log_error}", flush=True)
    return result


FINRL_SIGNAL_URL = "http://finrl-signal:8000"


@app.get("/portfolio-signal/{strategy}")
async def portfolio_signal(strategy: str):
    """
    FinRL-X'in portfoy-bazli (hisse-bazli degil) rotasyon sinyalini getirir.
    God Mode ilkesi: SADECE SINYAL, gercek islem yapmaz.
    """
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.get(f"{FINRL_SIGNAL_URL}/signal/{strategy}")
            data = resp.json()
    except Exception as e:
        return {"error": str(e), "strategy": strategy}

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO decision_log (ticker, decision, total_score, layer_scores, price_at_decision) VALUES (%s, %s, %s, %s, %s)",
            (
                f"PORTFOLIO_{strategy}",
                data.get("signal", {}).get("market_regime", "unknown"),
                None,
                json.dumps(data.get("signal", {})),
                None,
            ),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as log_error:
        print(f"[portfolio_signal log] kayit hatasi: {log_error}")

    return data


COGNEE_URL_MAA = "http://cognee:8000"


@app.get("/memory/{ticker}")
async def memory_query(ticker: str):
    """
    Bir hisse icin gecmis kararlarin hafizada ne dedigini getirir.
    Cognee'nin CHUNKS modu kullanilir (halusinasyon-dirençli, sadece
    gercekten kaydedilen metni dondurur, LLM yorumu katmaz).
    Ham Python-dict-repr yanitini frontend icin temiz metin listesine cevirir.
    """
    import re

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{COGNEE_URL_MAA}/recall",
                json={"query": ticker, "dataset": "alphawise_decisions"},
            )
            raw = resp.json()
    except Exception as e:
        return {"error": str(e), "ticker": ticker}

    clean_texts = []
    for item in raw.get("results", []):
        dataset_match = re.search(r"'dataset_name':\s*'([^']*)'", item)
        dataset_name = dataset_match.group(1) if dataset_match else "bilinmiyor"
        # 'text': '...' kaliplarini bul (tek/cift tirnak, kacis karakterleri dahil)
        text_matches = re.findall(r"'text':\s*(\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*')", item)
        for tm in text_matches:
            try:
                text = eval(tm)  # sadece string literal'i cozer, guvenli (regex zaten string'e sinirlandi)
                clean_texts.append({"dataset": dataset_name, "text": text})
            except Exception:
                continue

    return {"ticker": ticker, "memories": clean_texts}


MARKET_HOURS_URL = "http://market-hours:8000"


async def get_market_status(market: str):
    """market: 'us' ya da 'bist'. Piyasanin su an acik/kapali oldugunu getirir."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{MARKET_HOURS_URL}/market-status/{market}")
            return resp.json()
    except Exception as e:
        return {"error": str(e), "is_open": None}


@app.get("/market-status/{market}")
async def market_status_proxy(market: str):
    """Frontend'in dogrudan cagirabilecegi vekil endpoint."""
    return await get_market_status(market)



# ===== IZLEME & CIKTI KORUYUCU (15.08.2026) =====
import sys as _s, os as _o
_s.path.insert(0, _o.path.dirname(__file__))


@app.get("/tracing/summary")
def tracing_summary():
    """Kaskad asamalarinin performans ozeti (hangi asama ne kadar suruyor)."""
    from tracing import ozet, phoenix_ayakta
    return {"phoenix_ayakta": phoenix_ayakta(), "ozet": ozet()}


@app.get("/tracing/recent")
def tracing_recent(limit: int = 50):
    from tracing import son_izler
    return {"izler": son_izler(limit)}


@app.get("/guard/test/{ticker}")
def guard_test(ticker: str, karar: str = "EKLE", gerekce: str = "Coklu katmanda pozitif konfluans."):
    """Cikti koruyucusunu canli test eder."""
    from output_guard import dogrula, sema_talimati
    ok, nesne, hata = dogrula(ticker, karar, gerekce)
    return {"gecerli": ok, "cikti": nesne.model_dump() if nesne else None,
            "hata": hata, "sema_talimati": sema_talimati()}
