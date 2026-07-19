# ALPHAWISE SİSTEM ANAYASASI v4.4

### HEDGE FUND EDITION — GITHUB-NATIVE / AUTONOMOUS

### ABD + Türkiye (BIST) / Otonom Öz-Gelişen Ajan Ordusu

> "Confluence over Confidence — Self-Improving Intelligence"

Revizyon Notu v4.4 (TAM KAPASİTE): (1) 4-Katmanlı Model Kaskad sistemi (özelleşmiş → ücretsiz → ücretli → deterministik) her ajan rolü için. (2) Otonom öz-gelişen ajan ordusu: ajanlar birbiriyle haberleşir, hatadan öğrenir, denetçi ordusu tarafından geri gönderilip yeniden eğitilir. (3) Dark Pool + L2/L3 tarama servisi. (4) Ajan denetim matrisi + seçim yetkisi. (5) OpenBB geri eklendi (kişisel kullanım — AGPL viral riski dağıtımda ortaya çıkar, kişisel kullanımda serbest). (6) Alpaca + Alpha Vantage veri kaynakları. (7) Framework yedekliliği (CrewAI + OpenClaw ana, LangGraph yedek). Kişisel kullanım öncelikli, ticari faza hazır.

Durum: TASLAK — İnsan Sistem Mimarı onayı bekleniyor

Tarih: Temmuz 2026


---


## MADDE 1 — SİSTEMİN KİMLİĞİ, AMACI VE YATIRIM FELSEFESİ

**1.1. **ALPHAWISE, B2C uzun vadeli büyüme ve temettü odaklı kantitatif portföy analiz platformudur. Günlük al-sat (day-trading) tavsiyesi üretmek sistem dışıdır ve anayasaya aykırıdır.

**1.2. **Sistem yalnızca dört karar kodu üretir:

- EKLE — Yeni pozisyon alınması veya mevcut pozisyonun artırılması için objektif veri koşulları oluşmuştur
- TUT — Mevcut pozisyonu koruma; forward-looking veriler mevcut pozisyonu desteklemektedir
- BEKLE — Yeni giriş için objektif veri koşulları henüz oluşmamıştır; mevcut pozisyon korunur
- DİKKAT ET — Risk artışı tespit edilmiştir; kullanıcı kendi risk toleransı ve yatırım hedefleri çerçevesinde değerlendirme yapmalıdır
Sistem pozisyon büyüklüğü veya süresi konusunda talimat vermez.

**1.3. **Yasak dil listesi: Hiçbir çıktı "al", "sat", "kâr realize et", "zarar kes", "fırsat", "patlama", "kaçırma", "yükseliş rallisi", "çakılma", "roket", "ay'a", "dipleri topla", "trenin kaçıyor", "altın fırsat" gibi işlem emri, duygusal dil veya piyasa jargonu içeremez. Bu liste genişletilebilir ancak daraltılamaz.

**1.4. **Her rapor sonunda yasal sorumluluk reddi zorunludur:


> _"Bu analiz yatırım tavsiyesi değildir. Geçmiş performans geleceği garanti etmez. Kararlar tamamen kişisel sorumluluktadır. ALPHAWISE SEC, SPK (CMB) veya herhangi bir finansal düzenleyici kurum nezdinde kayıtlı yatırım danışmanı değildir. Sistem hiçbir pozisyon açma, kapama veya azaltma talimatı vermez. Tüm karar kodları (EKLE/TUT/BEKLE/DİKKAT ET) kantitatif veri durumunu ifade eder, işlem emri değildir."_

**1.5. **Kapsanan Piyasalar:

- Amerika (ABD): NYSE, NASDAQ, AMEX — ticker formatı: NVDA, AAPL, GOOGL, LLY
- Türkiye (BIST): Borsa İstanbul — ticker formatı: THYAO.IS, GARAN.IS, ASELS.IS
- ABD ETF ve Temettü araçları: SCHD, JEPI, VTI, VOO, O, MAIN
- NOT: Alman borsası (XETRA/DAX) bu versiyonda KAPSAM DIŞI — ileride v5.0'da eklenebilir
- Paralel analiz limiti: Kişisel kullanımda sınırsız; ticari modelde katman bazlı (Demo: 2, Starter: 5, Pro: 10, Elite: 20)
**1.6. **Yatırım felsefesi: "Confluence over Confidence" — Tek bir veri kaynağına güvenmek yasaktır; kararlar çok katmanlı veri kesişiminden doğar. Genel ilkeler:

- Hiçbir pozisyon tek göstergeye dayanamaz (min 3 katman)
- Sürü psikolojisi değil, kurumsal ayak izi takip edilir
- Düşen bıçak tutulmaz — momentum teyitsiz giriş yapılmaz
- Uzun vadeli yapısal değişim > kısa vadeli gürültü
- Risk yönetimi getiriden önce gelir
**1.7. **Kullanıcının maliyet bazı (cost basis) raporda bilgi amaçlı gösterilir. Cost basis, karar koduna asla etki etmez. Karar kodları yalnızca forward-looking kantitatif verilere dayanır. Anchor bias önlenir.

**1.8. [YENİ] **Karar Kodu Geçiş Kuralları (State Machine):

- EKLE → TUT: Giriş koşulları hâlâ pozitif, yeni pozisyon gerekmez
- EKLE → DİKKAT ET: Geçersiz. EKLE verilmişse aynı döngüde DİKKAT ET üretilemez.
- TUT → BEKLE: Forward-looking veriler nötrale döndü
- TUT → DİKKAT ET: Risk göstergeleri kötüleşti
- BEKLE → EKLE: Min 3 katman confluence ≥70 oluştu
- DİKKAT ET → TUT: Risk göstergeleri normalleşti (en az 5 iş günü bekleme)
- DİKKAT ET → BEKLE: Risk devam ediyor ama acil değil

> ⚠️ **Aynı hisse için aynı rapor döngüsünde kod değişikliği yapılamaz. Bir sonraki döngüyü beklemek zorunludur.**


---


## MADDE 2 — VERİ CONFLUENCE KANUNU VE KAYNAK MATRİSİ

**2.1. **Hiçbir ajan, hiçbir rapor, hiçbir karar kodu yalnızca tek bir veri katmanına dayanarak üretilemez. Geçerli karar için minimum 3 veri katmanı zorunludur. Bu kural çiğnenemez — Denetçi Ajan veto kullanır.


### 2.2. VERİ KATMANLARI VE ZORUNLU KAYNAKLAR


#### KATMAN A — MAKRO VERİ


| Kaynak | URL / Repo | Lisans | Kapsam |
|---|---|---|---|
| FRED API | fred.stlouisfed.org | Ücretsiz | Fed faizi, CPI, GDP, PMI, yield curve, USD/TRY (DEXTHUS) |
| pandas-market-calendars | github.com/rsheftel/pandas_market_calendars | Apache-2.0 | Tatil, piyasa saati (NYSE, BIST) |
| TCMB EVDS API | evds2.tcmb.gov.tr | Ücretsiz | TCMB faizi, TÜFE, GSYH, USD/TRY kur, BIST100 göstergeleri |
| BIST Veri | borsaistanbul.com/veriler | Ücretsiz | BIST100/30 endeks verileri, günlük kapanış |
| TradingView Scraper | github.com tabanlı | MIT | BIST hisse teknik verileri (ücretsiz alternatif) |


> 📝 NOT: ECB SDW kaldırıldı — Alman borsası kapsam dışı. Yerine TCMB EVDS API.


> 📝 NOT: USD/TRY kuru: FRED DEXTHUS serisi (günlük) + TCMB EVDS (anlık). İkisi çapraz doğrulama için kullanılır.


#### KATMAN B — TEMEL ANALİZ


| Kaynak | URL / Repo | Lisans | Kapsam |
|---|---|---|---|
| yFinance | github.com/ranaroussi/yfinance | Apache-2.0 | ABD + BIST temel finansallar, bilanço, temettü (.IS suffix) |
| Alpaca Market Data | alpaca.markets | Freemium (200/dk!) | ABD: Real-time websocket (IEX feed), bars, quotes, trades |
| Alpha Vantage | alphavantage.co | Freemium (25/gün) | ABD + global: fiyat, forex, temel (IEX Cloud yedeği) |
| Finance Toolkit | github.com/JerBouma/FinanceToolkit | MIT | 150+ finansal metrik, DCF modülü (ABD odaklı) |
| Microsoft Qlib | github.com/microsoft/qlib | MIT | ML tabanlı bilanço analizi, alpha mining |
| Tiingo API | tiingo.com | Freemium | ABD: Adjusted close, dividends, splits |
| SEC EDGAR | github.com/edgartools/edgartools | MIT | ABD: Form 4, 10-K, 10-Q, insider trading |
| Quiver Quant | quiverquant.com/api | Freemium | ABD: Kongre işlemleri, 13F kurumsal sahiplik |
| KAP API (gayri resmi) | github tabanlı wrapper | MIT | BIST: Kamuyu Aydınlatma Platformu, finansal tablolar |
| IsYatirim / Matriks | Ekran kazıma wrapper | Dikkatli | BIST: Analist tahminleri, hedef fiyatlar |
| Polygon.io | polygon.io | Freemium | ABD: Block trades, options flow, temettü takvimi |


> 📝 NOT: BIST hisseleri yFinance'ta .IS uzantısıyla çalışır (örn: THYAO.IS). Bilanço verisi için KAP API wrapper kullanılır.


> 📝 NOT: Alpaca free tier dakikada 200 çağrı (Polygon free 5/dk'ya kıyasla çok cömert) ama gerçek zamanlı veri sadece IEX borsasından (~%2-3 hacim). Tam CTA/UTP kapsamı ticari fazda ücretli plan gerektirir.


#### KATMAN C — PİYASA MİKROSTRÜKTÜR (DARK POOL + L2)


| Kaynak | URL / Repo | Lisans | Kapsam |
|---|---|---|---|
| Squeeze Metrics | squeezemetrics.com/monitor/static/DIX.csv | Ücretsiz | DIX (Dark Index), GEX (Gamma Exposure) |
| FINRA RegSho | api.finra.org | Ücretsiz | Short volume, dark pool şeffaflık (T+1) |
| OpenBB Platform | github.com/OpenBB-finance/OpenBB | AGPLv3 * | Dark Pool, OTC, options flow modülleri (* kişisel kullanım) |
| Alpaca L1/L2 | alpaca.markets | Freemium | IEX order book (kısmi derinlik, gerçek zamanlı) |
| Polygon.io | polygon.io | Freemium (5/dk) | Block trades, options flow (15dk gecikmeli) |
| jensolson/SPX-GEX | github.com/jensolson/SPX-Gamma-Exposure | MIT | CBOE'den market maker GEX hesaplama |
| Databento | databento.com | Ücretli (BYOK) | Gerçek L2/L3 order book (ticari faz) |


> ⚠️ *** OpenBB AGPLv3: Kişisel kullanımda serbest (viral lisans sadece yazılım DAĞITIMINDA tetiklenir). Ticari faza geçişte ya izole container'a alınır (Madde 15.3 network boundary) ya da çıkarılır.**


> 📝 NOT: Stock Grid ve Chart Exchange kaldırıldı (TOS ihlali riski). Webull/Schwab L2 API kaldırıldı (gayri resmi/ToS ticari kullanım yasağı).


> 📝 NOT: DÜRÜST GERÇEK: Tam ücretsiz L2/L3 order book ABD hisseleri için MEVCUT DEĞİL. IEX Cloud (Ağustos 2024) kapandı. Alpaca IEX feed'i kısmi derinlik verir (~%2-3 hacim). Gerçek konsolide L2/L3 ancak Databento/Polygon Business ile (ticari faz) elde edilir. Her raporda bu sınırlama belirtilir.


#### KATMAN D — DUYGU VE HABER ANALİZİ


| Kaynak | URL / Repo | Lisans | Kapsam |
|---|---|---|---|
| FinBERT | github.com/ProsusAI/finbert | Apache-2.0 | İngilizce ABD haber sentiment (-1/+1) |
| FinGPT-TR (fine-tune) | HuggingFace hub | Apache-2.0 | Türkçe finansal metin sentiment (BIST) |
| BERTurk-Finance | HuggingFace hub | Apache-2.0 | BIST özelleşmiş Türkçe finansal model |
| Finnhub | finnhub.io | Freemium | ABD: Anlık haberler, earnings calendar |
| Bloomberg Türkiye | Web scraper (dikkatli) | ToS riski | Türkçe piyasa haberleri (yedek) |
| StockTwits API | api.stocktwits.com | Ücretsiz | ABD sosyal sentiment |
| NewsAPI.org | newsapi.org | Freemium (100 req/gün) | Genel haber, İngilizce + Türkçe |
| GDELT Project | gdeltproject.org | Ücretsiz | Küresel olay verisi, Türkiye haberleri dahil |
| Ekşi Sözlük / Twitter/X Scraper | Dikkatli | ToS riski | Türkiye sosyal medya sentiment (isteğe bağlı) |


> 📝 NOT: FinGPT-DE kaldırıldı — Almanya kapsam dışı. Yerine BERTurk-Finance ile BIST sentiment güçlendirildi.


> 📝 NOT: Web scraper kaynakları (Bloomberg TR, Ekşi) ToS ihlali riski taşır. Dikkatli kullan, hız sınırı uygula.


#### KATMAN E — ML / BACKTEST / TAHMİN


| Kaynak | URL / Repo | Lisans | Kapsam |
|---|---|---|---|
| VectorBT | github.com/polakowo/vectorbt | PolyForm | Walk-forward backtest |
| VectorBT Pro | vectorbt.pro | Ücretli | Gelişmiş backtest, portföy optimizasyonu |
| FinRL | github.com/AI4Finance-Foundation/FinRL | MIT | PPO/A2C DRL, risk-return optimizasyonu |
| Microsoft Qlib | github.com/microsoft/qlib | MIT | Alpha mining, ML modeller |
| TA-Lib | github.com/mrjbq7/ta-lib | BSD | RSI, MACD, BBands, ATR (sadece destekleyici) |
| pandas-ta | github.com/twopirllc/pandas-ta | MIT | TA-Lib alternatifi |
| Nixtla TimeGPT | github.com/Nixtla/nixtla | Apache-2.0 | Zaman serisi tahmini |
| Amazon Chronos | github.com/amazon-science/chronos-forecasting | Apache-2.0 | Uzun vade fiyat projeksiyonu |
| Skfolio | github.com/skfolio/skfolio | BSD-3 | Portföy optimizasyonu, Risk-Parity |


> 📝 NOT: Backtrader (GPL-3.0) kaldırıldı — viral lisans riski.


#### KATMAN F — GITHUB AÇIK KAYNAK VERİ KATMANI [YENİ v4.1]

Pahalı finansal veri servislerinin (Databento $500+/ay, Bloomberg $24K/yıl) açık kaynak alternatifleri. Sistem bu repoları otomatik keşfeder, klonlar ve entegre eder.


| Repo | Lisans | Kapsam | Yerine Geçtiği |
|---|---|---|---|
| bmoscon/orderbook | XFree86 | C ile yazılmış hızlı L2/L3 order book veri yapısı (KRİPTO borsaları) | İleride kripto eklenirse |
| bmoscon/cryptofeed | XFree86 | 30+ KRİPTO borsa websocket feed, L2/L3 book (Binance/Coinbase) | İleride kripto eklenirse |
| mansoor-mamnoon/limit-order-book | MIT | 20M+ msg/sec LOB engine, microstructure analytics | Refinitiv tick data |
| nicolezattarin/LOB-feature-analysis | MIT | OFI, MLOFI, PIN hesaplama, LOB feature engineering | Akademik veri servisleri |
| bigurb10/FINRA | MIT | FINRA RegSho dark pool veri indirme/işleme | Quandl dark pool ($) |
| RishiRCarloni/dark-pool-project | MIT | Real-time dark pool pipeline (Kafka + Flask) | Stock Grid (kaldırıldı) |
| aluay/Insight | MIT | Dark pool, short interest, kongre işlemleri, fed repo | Quiver Quant premium |
| jensolson/SPX-Gamma-Exposure | MIT | CBOE verisiyle market maker GEX hesaplama | SpotGamma ($40/ay) |
| Matteo-Ferrara/gex-tracker | MIT | CBOE'den dealer GEX scraping + Black-Scholes | SpotGamma ($40/ay) |
| aakash-code/GammaGEX | MIT | Real-time GEX momentum, delta flow, gamma squeeze | Unusual Whales ($60/ay) |
| LesterCS/Institutional-Order-Flow | MIT | ICT bazlı institutional order flow analizi | FlowAlgo ($100/ay) |
| FlashAlpha-lab/awesome-options-analytics | MIT | Kapsamlı options analytics kaynak listesi | Referans |
| DrAshBooth/PyLOB | MIT | Pure Python limit order book implementasyonu | Eğitim/yedek |


> ⚠️ **Her repo entegre edilmeden önce Madde 16'daki Repo Entegrasyon Pipeline'ından geçmek ZORUNDADIR.**

**2.3. **Dark Pool verisi eksikse veya 24 saatten eskiyse, Denetçi Ajan raporu otomatik reddeder. BEKLE kodu üretilebilir, EKLE veya DİKKAT ET üretilemez.

**2.4. **RSI, MACD, Bollinger Bands, hareketli ortalamalar tek başına asla yeterli kanıt değildir. Sadece Makro + Temel + Piyasa Mikrostrüktür üçlüsünün destekleyici kanıtı olarak kullanılabilir.

**2.5. **Veri kalite SLA: Her kaynak için %99.5 uptime hedefi. Kaynak çökerse otomatik failover. Gecikme >15 dakikaysa "güvenilmez" işaretlenir.

**2.6. **Counterparty Failover Zinciri (ZORUNLU):

- Birincil: Databento → Fallback: Polygon → Son çare: yFinance + Finance Toolkit
- Her failover tetiklendiğinde kullanıcıya bildirilir
- Failover süresi raporda belirtilir (veri kalitesi notu)
**2.7. **Türkiye BIST Özel Gereksinimleri [GÜNCELLENDİ]:

- USD/TRY kur verisi: FRED DEXTHUS + TCMB EVDS API (çift kaynak çapraz doğrulama)
- BIST piyasa saatleri: pandas-market-calendars ("BIST" takvimi) — 10:00-18:00 TSİ
- KAP finansal tablolar: KAP wrapper ile BIST bilanço/gelir tablosu çekimi
- TCMB faiz kararları: EVDS API (haftalık repo faizi serisi)
- BIST teknik veri: yFinance .IS suffix (THYAO.IS, GARAN.IS) + TradingView scraper yedek
- Türk enflasyon verisi: TÜİK TÜFE → TCMB EVDS API üzerinden
- BIST için ek risk: TL değer kaybı riski — USD/TRY volatilitesi her raporda belirtilir

> 📝 NOT: BIST hisseleri için Dark Pool verisi MEVCUT DEĞİL (FINRA/Squeeze Metrics ABD'ye özgü). BIST raporlarında Dark Pool katmanı atlanır, confluence skoru 4 ajan üzerinden hesaplanır.

**2.8. [YENİ] **Veri Tazelik Matrisi:


| Veri Tipi | Maks Yaş | Aşılırsa |
|---|---|---|
| Dark Pool (DIX/GEX) | 24 saat | EKLE/DİKKAT ET üretilemez |
| L2 Order Book | 15 dakika (RT mod) | "güvenilmez" etiketi |
| Makro (FRED/ECB) | 24 saat | Uyarı, analiz devam |
| Temel (bilanço) | 1 çeyrek | Uyarı, son çeyrek kullanılır |
| Haber/Sentiment | 4 saat | Düşük güven skoru |
| Options Flow | 1 saat | Uyarı, son veri kullanılır |

**2.9. [YENİ] **ChromaDB Önbellekleme: Aynı hisse 24 saat içinde tekrar sorgulanırsa önbellekten servis edilir. LLM çağrısı yapılmaz. Önbellek anahtarı: {ticker}_{tarih}_{katman}. Cache invalidation: yeni veri geldiğinde veya 24 saat dolduğunda.


---


## MADDE 3 — AJAN HİYERARŞİSİ, YETKİ DAĞILIMI VE ORKESTRASYON

**3.1. **Sistem 7 seviyeden oluşur. Hiçbir ajan kendi seviyesinin üstüne emir veremez.


### SEVİYE 0 — ORKESTRATÖR ROUTER [YENİ]

Görev: Gelen analiz talebini sınıflandır, hisse türünü belirle, ajan ağırlıklarını ata, iş akışını başlat.

**Hisse Sınıflandırma Algoritması: **

- Temettü hissesi tespiti: dividend_yield > %2.5 VE payout_ratio < %85 VE ardışık 5+ yıl temettü artışı
- Büyüme hissesi tespiti: revenue_growth_3y > %15 VEYA forward_PE > sektör ortalaması × 1.5
- ETF tespiti: ticker sonu .ETF veya bilinen ETF listesinde
- Alman hissesi tespiti: ticker sonu .DE
**Router Kararları: **

- Hisse türüne göre ajan ağırlık tablosunu seç (Madde 3.3)
- Piyasa açık mı kontrol et (pandas-market-calendars)
- ChromaDB cache kontrolü (24h)
- Eş zamanlı iş limiti kontrolü (katman bazlı)
- Tüm Seviye 1 ajanlarını paralel başlat

### SEVİYE 1 — VERİ AJANLARI

Görev: Veri çekme, temizleme, formatlama, failover yönetimi. Karar vermez.

Framework: n8n + Python servis (her kaynak için ayrı servis)

Yetki: Sadece READ ve FORMAT

**Failover Protokolü: **

- Her veri kaynağı için timeout=10s
- 1. deneme: Birincil kaynak
- 2. deneme: Yedek kaynak (Madde 2.6 zinciri)
- 3. denemede başarısızlık → veri katmanı "eksik" işaretlenir, Denetçi'ye bildirilir

### SEVİYE 2 — ANALİST AJANLAR

Framework: CrewAI (github.com/joaomdmoura/crewAI — Apache-2.0)

Destekleyici: LlamaIndex (github.com/run-llama/llama_index — MIT) — RAG hafıza


| Ajan | Birincil Model (OpenRouter) | Fallback Model | Görev |
|---|---|---|---|
| TAA — Teknik Analist | llama-3.3-70b:free | anthropic/claude-3.5-sonnet | RSI/MACD/BB + Fibonacci + Volume Profile + Confluence |
| FAA — Temel Analist | qwen/qwen-2.5-72b:free | openai/gpt-4o | DCF, FCF, bilanço, Qlib, earnings quality |
| RAA — Risk Ajanı | deepseek/deepseek-r1:free | anthropic/claude-3.5-sonnet | VaR, DIX/GEX, Kelly, L2, korelasyon, likidite |
| SAA — Sentiment | google/gemma-2-27b:free | openai/gpt-4o-mini | FinBERT + haber + kongre + insider + sosyal |
| MAA — Makro Ajanı | mistralai/mistral-small:free | anthropic/claude-3-haiku | FRED, ECB, yield curve, PMI, CPI, sektörel döngü |


#### 3.2. 4-KATMANLI MODEL KASKAD SİSTEMİ (Her Ajan Rolü İçin) [YENİ v4.4]

Her ajan rolü (TAA/FAA/RAA/SAA/MAA) için 4 katmanlı, her katmanda 3 modelli bir yedeklilik zinciri vardır. Amaç: sistem HİÇBİR koşulda cevapsız kalmaz.


| Katman | Amaç | Model Sayısı | Tetiklenme |
|---|---|---|---|
| TIER 1 — Özelleşmiş | Fine-tuned / eğitilmiş yüksek performans | 3 (sıralı) | Her zaman ilk |
| TIER 2 — Ücretsiz | OpenRouter free modeller (F/P optimize) | 3 (sıralı) | Tier 1 yanıt vermezse |
| TIER 3 — Ücretli Yedek | Premium paid modeller (garantili yanıt) | 3 (sıralı) | Tier 2 yanıt vermezse |
| TIER 4 — Deterministik | Kural bazlı hesaplama (ASLA başarısız olmaz) | 1 | Tier 3 yanıt vermezse |

Örnek — TAA (Teknik Analist) tam kaskad:


| Sıra | Model | Tip |
|---|---|---|
| 1-1 | Fine-tuned Llama-3.1-70B (TA özelleşmiş, kendi eğittiğimiz) | Özel eğitim |
| 1-2 | anthropic/claude-3.5-sonnet | Premium |
| 1-3 | openai/gpt-4o | Premium |
| 2-1 | meta-llama/llama-3.3-70b:free | Ücretsiz |
| 2-2 | qwen/qwen-2.5-72b:free | Ücretsiz |
| 2-3 | deepseek/deepseek-r1:free | Ücretsiz |
| 3-1 | anthropic/claude-3.5-sonnet (ayrı paid key) | Ücretli yedek |
| 3-2 | openai/gpt-4o-mini | Ücretli yedek |
| 3-3 | google/gemini-1.5-flash | Ücretli yedek |
| 4 | Kural bazlı: RSI+MACD+momentum deterministik hesap | Asla başarısız olmaz |


#### 3.2.1. Tier Cascade Manager

Her ajan rolü için ai-agent-orchestrator içinde bir Tier Cascade Manager çalışır:

- Her model çağrısı: timeout=25s
- Bir tier içinde 3 model sırayla denenir, ilk başarılı yanıt kabul edilir
- Tier tükenirse bir alt tier'a geçilir
- Tier 4 (deterministik) çıktısı düşük confidence ile işaretlenir (0.4 sabit)
- Kaskadın hangi tier'da çözüldüğü output schema'da kaydedilir (cascade_tier alanı)

#### 3.2.2. Tier Consensus Alt-Katmanı

Aynı rol için Tier 1 ve Tier 3 farklı sinyal üretirse (örn: Tier 1 EKLE, Tier 3 DİKKAT ET):

- İki tier'ın confidence skorları karşılaştırılır
- Fark < 0.2 → düşük confidence, rol çıktısı BEKLE'ye çekilir
- Fark ≥ 0.2 → yüksek confidence olan tier kazanır ama uyuşmazlık loglanır
- Sürekli tier uyuşmazlığı → o rolün Tier 1 modeli retraining kuyruğuna alınır

#### 3.2.3. Gecikme Bütçesi ve Maliyet Koruması

- Toplam pipeline SLA: max 90 saniye (5 rol × kaskad). Aşılırsa çözülemeyen roller direkt Tier 4'e atlar
- Tier 3 (ücretli) tetiklenme oranı günlük izlenir. >%20 ise Tier 1/2 modelinde sorun var → uyarı
- Maliyet dashboard: her analiz için hangi tier'ların kullanıldığı ve toplam token maliyeti

#### 3.3. Hisse Türüne Göre Dinamik Ağırlıklar


| Hisse Türü | TAA | FAA | RAA | SAA | MAA | Örnek |
|---|---|---|---|---|---|---|
| ABD Büyüme | %25 | %20 | %30 | %10 | %15 | NVDA, GOOGL, LLY |
| ABD Temettü | %15 | %35 | %15 | %15 | %20 | O, JNJ, MAIN |
| ABD ETF | %10 | %30 | %25 | %10 | %25 | SCHD, JEPI, VTI |
| BIST Büyüme | %20 | %25 | %25 | %15 | %15 | ASELS.IS, FROTO.IS |
| BIST Banka/Finans | %15 | %30 | %20 | %15 | %20 | GARAN.IS, AKBNK.IS |
| BIST Büyük Cap | %20 | %25 | %20 | %15 | %20 | THYAO.IS, EREGL.IS |


> 📝 NOT: BIST hisselerinde Dark Pool katmanı yoktur. RAA ağırlığı Dark Pool yerine likidite + bid-ask spread analizine odaklanır.


#### 3.4. Output Schema (Her ajan için zorunlu)

Her ajan aşağıdaki JSON schema'ya uygun çıktı üretmek ZORUNDADIR:

{"signal": "EKLE|TUT|BEKLE|DİKKAT ET", "confidence": 0.0-1.0, "confluence_score": 0-100, "reasoning": "[VERİ] → [ANALİZ] → [ÇIKARIM] → [KARAR KODU]", "agent": "TAA|FAA|RAA|SAA|MAA", "model_used": "model_adı", "fallback_triggered": true|false, "data_layers": ["FRED", "DCF", "DIX/GEX", "L2", "FinBERT"], "missing_data": [], "parse_error": false, "parse_retry_count": 0-2, "timestamp": "ISO8601", "self_critique": "Bu analizde eksik olan: ...", "counter_argument": "Yanlış olabilirim çünkü: ...", "short_term": "1-3 ay görüşü", "mid_term": "3-12 ay görüşü", "long_term": "1-3 yıl görüşü", "data_freshness": {"katman": "son_güncelleme_ISO8601"}, "failover_chain": ["kullanılan_kaynaklar"]}


#### 3.5. Parse Error Retry Mekanizması

- LLM çıktısı JSON schema'ya uymazsa → Pydantic validation hatası
- 1. retry: Aynı modelden structured output (function calling) talep
- 2. retry: Fallback modelden structured output talep
- 3. denemede hata → ajan parse_error: true döner, Denetçi raporu reddeder

### SEVİYE 3 — CONFLUENCE KARAR MOTORU [YENİ]

Görev: 5 ajandan gelen skorları topla, hisse türüne göre ağırlıkla, nihai confluence skoru üret.

Bu seviye ayrı bir modül olarak kodlanır — LLM kullanmaz, deterministik hesaplama yapar.

**Hesaplama Formülü: **

confluence_score = Σ(ajan_skoru × ajan_ağırlığı) / Σ(ajan_ağırlıkları)

**Karar Eşikleri: **

- confluence ≥ 80 → EKLE adayı (Denetçi onayı hâlâ gerekli)
- confluence 70-79 → TUT
- confluence 50-69 → BEKLE
- confluence < 50 → DİKKAT ET adayı
- confluence < 70 → EKLE kodu asla üretilemez
**Çatışma Tespiti: **

- 5 ajan 3-2 bölünmüşse → rapor reddedilir, Seviye 5 Çatışma Çözücüye yönlendirilir
- FAA ve RAA zıt sinyal verirse (EKLE vs DİKKAT ET) → otomatik Çatışma Çözücü
- Herhangi 2 ajan parse_error döndürürse → rapor reddedilir

### SEVİYE 4 — DENETÇİ AJAN

Framework: LangGraph (github.com/langchain-ai/langgraph — MIT)

Birincil Model: deepseek/deepseek-r1:free | Fallback: anthropic/claude-3.5-sonnet

Anti-Hallucination: SuperAGI prompt kütüphanesi

Yetki: REDDETME (veto hakkı — hiçbir baskıya boyun eğemez)

**Reddetme Koşulları (ZORUNLU): **

1. Dark Pool verisi eksik → EKLE/DİKKAT ET reddedilir
2. Sadece teknik gösterge → rapor reddedilir
3. Parse error >2 ajan → rapor reddedilir (retry sonrası)
4. Confluence skoru <70 → EKLE reddedilir
5. Ajan sinyalleri 3-2 bölünmüşse → Çatışma Çözücüye yönlendir
6. [YENİ] Veri tazelik ihlali (Madde 2.8) → ilgili katman skoru sıfırlanır
7. [YENİ] Korelasyon >0.85 → EKLE reddedilir (Madde 10.4)
8. [YENİ] Likidite yetersiz → EKLE reddedilir (Madde 10.5)
**Self-Critique Loop (Max 2 iterasyon): **

1. "Dark Pool ve L2 verisi nerede? Kurumsal ayak izi var mı?"
2. "Bu kararın makro gerekçesi nedir?"
3. "Karşıt argüman nedir? Neden yanlış olabilirim?"
4. "Confidence seviyem nedir? (%X) — hangi veri eksikliği var?"
5. [YENİ] "Bu karar geçmiş benzer koşullarda ne sonuç verdi? (MemGPT lookup)"
6. [YENİ] "Stress test sonuçları bu kararla tutarlı mı?"
- İterasyon 1 sonrası hâlâ eksik → iterasyon 2
- İterasyon 2 sonrası hâlâ eksik → "BEKLE" kodu veya insan onayı talep

### SEVİYE 5 — ÇATIŞMA ÇÖZÜCÜ

Framework: AutoGen/AG2 (github.com/ag2ai/ag2 — Apache-2.0)

Destekleyici: FinRobot (github.com/AI4Finance-Foundation/FinRobot — MIT)

**Aktivasyon Koşulları: **

- FAA ile RAA zıt karar verirse (EKLE vs DİKKAT ET)
- 5 ajan 3-2 bölünmüşse
- [YENİ] MAA ile diğer tüm ajanlar arasında makro uyumsuzluk varsa
**Çözüm Algoritması [YENİ]: **

1. Çatışan ajanların data_layers listelerini karşılaştır
2. Eksik veri katmanı olan ajanın güvenilirliğini düşür
3. FinRobot ile bağımsız üçüncü analiz yap
4. Ağırlıklı ortalama ile sentez üret (veri kalitesi ağırlığı)
5. Sonuç hâlâ belirsizse → "BEKLE" + insan onayı talep

### SEVİYE 6 — RAPOR ÜRETİCİ

Framework: LangGraph State Machine

Birincil Model: qwen/qwen-2.5-72b:free | Fallback: openai/gpt-4o

Destekleyici: Nous Hermes 2 (Apache-2.0), Fincept Terminal (MIT)

Yetki: Nihai karar kodu üretimi (Denetçi onayından sonra aktif)


### SEVİYE 7 — ÜST ORKESTRATÖR

Platform: n8n (github.com/n8n-io/n8n — Fair-Code)

Destekleyici: Apache Airflow (github.com/apache/airflow — Apache-2.0)

Yetki: Tetikleme, zamanlama, kuyruk yönetimi, ACİL KOD, Cuma özeti


#### 3.6. Handoff Protokolü (ZORUNLU)

Ajanlar birbirini doğrudan çağıramaz. Sadece handoff_request üretir. Her handoff JSON formatında:

{"from": "ajan_id", "to": "ajan_id|seviye", "payload": {...}, "priority": 1-5, "timestamp": "ISO8601"}


#### 3.7. [YENİ] Ajan Seçim ve Eleme Kriterleri

Yeni bir LLM modeli ajan olarak sisteme dahil edilmeden önce:

1. 500 geçmiş veri noktasında backtest (directional accuracy)
2. JSON schema compliance testi (100 örnek, %98+ başarı gerekli)
3. Latency testi (p95 < 45 saniye)
4. Hallucination testi (bilinen verilerle 50 örnek, %0 hallucination gerekli)
5. Maliyet/performans oranı değerlendirmesi
- Tüm testleri geçen model 2 hafta "gözlemci" modda çalışır (karar vermez, sadece log)
- Gözlemci döneminde directional accuracy >%55 → üretime alınır

#### 3.8. [YENİ v4.4] Ajan Seçim Yetki Matrisi — Kim Karar Verir?


| Aşama | Yetki Sahibi | Tetikleyici |
|---|---|---|
| Yeni model önerisi | github-repo-manager veya ajan kendisi | Hit rate <0.3 (Madde 8.1) veya insan talebi |
| Test çalıştırma | Otomatik Pipeline (Madde 3.7) | Öneri onaylanınca otomatik başlar |
| Tier 1'e alma kararı | Denetçi Ajan + İnsan Admin (ÇİFT ONAY) | Test sonuçları %98+ ise |
| Tier düşürme/çıkarma | Otomatik sistem | Hit rate <0.2 (Madde 8.1) |
| Acil model devre dışı bırakma | İnsan Admin (tek onay yeterli) | Kritik hata / hallucination tespiti |


> 📝 NOT: Tier 1 (özelleşmiş/eğitilmiş) modele YENİ bir model eklemek maliyet taahhüdü içerir — bu yüzden çift onay zorunlu. Tier 2/3/4 içi rotasyon otomatik olabilir.


#### 3.9. [YENİ v4.4] Ajan Denetim ve Test Matrisi

Sistemde hangi seviyenin neyi test/denetlediği net tanımlanır:


| Kontrol Seviyesi | Kim Yapar | Neyi Kontrol Eder | Neye Göre Puanlar |
|---|---|---|---|
| Veri ön kontrolü | Router-service | Veri tazeliği, eksiklik | Madde 2.8 tazelik matrisi |
| Model çıktı kalitesi | Confluence Engine | JSON şema uyumu, gecikme | Pydantic validation, p95 latency |
| Peer Review (yatay) | Ajanlar birbirini çapraz kontrol | Rol-arası tutarlılık | RAA↔FAA, SAA↔MAA mantık uyumu |
| Tier Consensus (dikey) | Tier Cascade Manager | Aynı rol farklı tier tutarlılığı | Madde 3.2.2 fark eşiği |
| Nihai denetim | Denetçi Ajan (Seviye 4) | Confluence + veto koşulları | Madde 3, Seviye 4 kriterleri |
| Uzun vadeli performans | Ajan Seçim Pipeline | Hit rate, directional accuracy | Madde 3.7 + 8.1 |

**Peer Review Mantığı: **RAA'nın risk değerlendirmesi FAA'nın temel analiziyle büyük çelişki gösterirse (örn: RAA yüksek risk derken FAA güçlü büyüme diyorsa) → iki ajan arası otomatik "neden farklı düşünüyorsun" sorgusu tetiklenir, sonuç Denetçi'ye özel not olarak iletilir.


#### 3.10. [YENİ v4.4] Orkestrasyon Framework Yedekliliği

Model kaskadından farklı olarak, ORKESTRASYON ÇATISININ KENDİSİ (CrewAI kütüphanesi) çökerse:


| Seviye | Framework | Rol |
|---|---|---|
| Ana Orkestrasyon | CrewAI + OpenClaw | Birincil — tüm normal operasyon |
| Yedek Orkestrasyon | LangGraph custom orchestrator | CrewAI health check başarısız olursa devreye girer |

- CrewAI health check: her 60 saniyede bir iç test çağrısı
- 3 ardışık health check başarısızsa → Yedek Orkestrasyon devreye girer
- Yedek Orkestrasyon, CrewAI'ı bypass ederek aynı Tier Cascade'i (Madde 3.2) doğrudan çağırır
- CrewAI düzelince otomatik ana role döner, olay Audit Trail'e loglanır

#### 3.11. [YENİ v4.4] Otonom Ajan Öz-Gelişim Protokolü

Ajanlar kendi performans zayıflığını fark edip GitHub'da yeni beceri/teknik arayabilir — ama HİÇBİR ZAMAN insan onayı olmadan sisteme entegre edemez:

1. Ajan hit rate'i düşer (Madde 8.1, <0.3 uyarı eşiği) VEYA tekrarlayan hata paterni tespit edilir
2. github-repo-manager otomatik GitHub araması yapar (role-specific: örn. "technical analysis python 2026")
3. Aday repo/teknik bulunur → Madde 15.2 Repo Entegrasyon Pipeline'ından geçer (lisans, güvenlik, sandbox, kalite)
4. Denetçi Ajan değerlendirir: bu beceri gerçekten performansı iyileştirir mi?
5. İnsan Admin onayı ZORUNLU — ajan kendi kendine hiçbir kod çalıştıramaz veya repo entegre edemez
6. Onaylanırsa: Skill Registry'e versiyonlanmış giriş eklenir, 2 hafta gözlemci modu
7. 2 hafta sonra hit rate iyileşmediyse → otomatik rollback

> ⚠️ **KRİTİK GÜVENLİK KURALI: Otonomi sadece 'öneri sunma' seviyesindedir. Ajan asla kendi kod yazıp çalıştıramaz, asla repo klonlayıp direkt import edemez, asla insan onayını bypass edemez. Bu sınır anayasanın hiçbir revizyonunda gevşetilemez.**


#### 3.12. [YENİ v4.4] Ajanlar Arası Haberleşme (Hatadan Öğrenme Döngüsü)

"Yanlış bilgi/hatalı yorum geldiğinde başka bir denetleyen ajan ordusu tarafından geri gönderilip yeniden mükemmel sonuç gelene kadar eğitilme" mekanizması:

1. Bir ajan çıktısı Peer Review'da (Madde 3.9) tutarsız bulunursa → "düzeltme talebi" ile aynı ajana geri gönderilir
2. Ajana özel critique prompt eklenir: "RAA şunu söyledi: [X], senin çıkarımınla çelişiyor: [Y]. Yeniden değerlendir."
3. Ajan yeni cevap üretir → tekrar Peer Review'a girer
4. Max 2 döngü (Madde Seviye 4 Self-Critique Loop ile aynı limit) — 2 döngü sonrası hâlâ tutarsızsa Denetçi'ye escalate edilir
5. Her düzeltme döngüsü MemGPT'ye kaydedilir → gelecekte benzer durumda ajan bu deneyimden "öğrenir" (RAG hafıza, Madde 8.4)
- Bu döngü ajanın kendi ağırlığını (Madde 8.1) etkilemez — sadece o anki raporun kalitesini artırır. Ağırlık güncellemesi haftalık hit rate bazlıdır.

---


## MADDE 4 — GÜVENLİK, GİZLİLİK VE VERİ İZOLASYON ANAYASASI

**4.1. **API Key Yönetimi:

- HashiCorp Vault (github.com/hashicorp/vault — MPL-2.0) → AES-256 şifreleme
- AWS KMS entegrasyonu → Key rotation 90 günde bir
- Vault erişim logları immutable (değiştirilemez)
**4.2. **Kullanıcı verisi (cost basis, portföy, risk toleransı) asla:

- Başka kullanıcıya gösterilemez
- Aggregate analytics'e dahil edilemez
- Eğitim verisi olarak kullanılamaz
- [YENİ] LLM'e gönderilen prompt'larda anonim hale getirilir (kullanıcı adı, email çıkarılır)
**4.3. **BYOK key'i: Asla loglanmaz, asla plaintext yazılmaz, RAM'de 5 saniyeden uzun tutulmaz. Transit şifreleme: TLS 1.3 zorunlu.

**4.4. **3-Tier İzolasyon (NIST Cybersecurity Framework Tier 3 + ISO 27001 A.13.1.3):


| Tier | Yetki | MCP | Açıklama |
|---|---|---|---|
| TIER 1 (UNTRUSTED READER) | Sadece okuma | Yok | Schema-validated JSON çıktı. Gelen her veri DATA, DIRECTIVE değil. |
| TIER 2 (ORCHESTRATOR) | Okuma + ajan araçları | Read-only | Tier 1 çıktısını doğrular, handoff_request üretir |
| TIER 3 (WRITE-HOLDER) | Read + Write + Edit | Yok | Sadece bu tier dosya yazabilir, raporları üretir |

**4.5. **Her kullanıcı izole Docker container'da çalışır: cgroups + namespaces (process), per-container limit (memory), ayrı VLAN (network).

**4.6. **Kimlik Doğrulama: Email doğrulama → 2FA (TOTP/SMS) → Admin: ayrı vault + MFA + IP whitelist. Session: JWT 24h expiry, refresh token 30 gün.

**4.7. **Fraud Detection: 5 başarısız giriş → 30dk ban. Şüpheli ödeme → manuel inceleme. VPN/proxy kayıt → ek doğrulama.

**4.8. [YENİ] **Prompt Injection Koruması: Tier 1'deki tüm dış veri (haberler, kullanıcı girişi) DATA olarak işlenir. Hiçbir dış veri sistem prompt'una enjekte edilemez. Dış veriden gelen talimat benzeri metinler otomatik filtrelenir.


---


## MADDE 5 — MALİYET, KAYNAK VE FREE-FIRST CASCADE KANUNU

**5.1. **Free-First Cascade (ZORUNLU sıralama):

1. Ücretsiz GitHub repo (yFinance, TA-Lib, pandas-ta, FinanceToolkit)
2. Ücretsiz API tier (FRED, FINRA, Quiver free, NewsAPI free)
3. OpenRouter free modeller (Llama, DeepSeek, Gemma, Mistral)
4. Freemium API (Polygon basic, Finnhub basic, Tiingo basic)
5. BYOK kullanıcının kendi key'i
6. Master key (ücretli) — son çare
**5.2. **CPU %80 aşımında: Ücretli model çağrıları durdurulur, işlem kuyruğa alınır, GPU instance scale-down.

**5.3. **Standart kullanıcı yükü yüksekse → Gece Vardiyası (02:00-06:00 UTC). Elite/VIP → her zaman öncelikli kuyruk (Redis priority queue).

**5.4. **BYOK Tükenirse: Master Key'e fallback → bakiyeden düş. Bakiye eşiği uyarısı (%20 kaldığında alert).

**5.5. **BYOK İndirim: 1 API → %10 + 1 ekstra hisse/gün | 2-3 API → %15 + 2 ekstra | 4+ API → %20 + ömür boyu Elite.

**5.6. [YENİ] **Maliyet İzleme Dashboard: Her analiz için token kullanımı, API çağrı sayısı, toplam maliyet gerçek zamanlı izlenir. Aylık maliyet raporu otomatik üretilir.


---


## MADDE 6 — RAPORLAMA, BENCHMARK VE GEREKÇELENDİRME ANAYASASI

**6.1. **Her rapor 5 bölümde üretilir (v3.1'de 4 bölümdü):


#### BÖLÜM 1 — CONFLUENCE SKORU (0-100)

Hisse türüne göre dinamik ağırlıklar (Madde 3.3'teki tablo kullanılır):


| Hisse Türü | Makro | Temel | Dark Pool | Duygu/Haber |
|---|---|---|---|---|
| Büyüme | X/25 | X/25 | X/30 | X/20 |
| Temettü | X/20 | X/40 | X/20 | X/20 |
| ETF | X/35 | X/35 | X/15 | X/15 |
| Alman | X/25 | X/25 | X/25 | X/25 |

KARAR İÇİN EŞİK: EKLE için ≥70, TUT için ≥50, <50 → DİKKAT ET adayı


#### BÖLÜM 2 — VADE BAZLI ANALİZ

- Kısa Vade (1-3 ay): Piyasa mikrostrüktür + makro momentum
- Orta Vade (3-12 ay): Temel analiz + sektörel döngü
- Uzun Vade (1-3 yıl): DCF + makro trend + yapısal değişim

#### BÖLÜM 3 — 3 SENARYO (ZORUNLU)

- Bull Case: Pozitif senaryo → fiyat hedefi + gerekçe + olasılık %
- Base Case: Mevcut trendler → fiyat hedefi + gerekçe + olasılık %
- Bear Case: Negatif senaryo → fiyat hedefi + gerekçe + olasılık %
Her senaryo için: Revenue farkı %, EBITDA marjı farkı %, DCF farkı %


#### BÖLÜM 4 — KİŞİSEL MALİYET BAZI ANALİZİ (BİLGİ AMAÇLI)

- Kullanıcının alış fiyatı ile mevcut fiyat karşılaştırması
- Unrealized gain/loss %

> ⚠️ **Cost basis karar koduna asla etki etmez. Karar kodları yalnızca forward-looking verilere dayanır.**


#### BÖLÜM 5 — RİSK SKORKART [YENİ]

- VaR (Value at Risk) — %95 ve %99 güven aralığı
- CVaR (Conditional VaR) — kuyruk riski
- Max Drawdown — geçmiş 1 yıl ve 3 yıl
- Korelasyon skoru — portföydeki diğer hisselerle
- Likidite skoru — 20 günlük ortalama hacim bazlı
- Stress test özeti — en kötü senaryo kaybı
- Vergi verimliliği notu (ülkeye özgü)
**6.2. **Gerekçe Formatı (ZORUNLU): [VERİ] → [ANALİZ] → [ÇIKARIM] → [KARAR KODU]

**6.3. **Benchmarking (ZORUNLU): S&P 500, MSCI World veya kullanıcı seçimi. Alpha (α), Beta (β), Sharpe Ratio, Sortino Ratio, Max Drawdown, Information Ratio.

**6.4. **Hassasiyet Analizi (DCF için): WACC ±1% → NPV değişimi. Terminal Growth Rate ±0.5% → NPV değişimi. Revenue Growth ±2% → NPV değişimi.

**6.5. **Rapor Dili: Kullanıcının kayıt dilinde (TR/EN/DE). Duygusal dil, metafor, "fırsat", "kaçırma", "patlama", "çakılma" ifadeleri kesinlikle yasak.


---


## MADDE 7 — BİLDİRİM, ALERT, ACİL KOD VE SPAM KORUMA ANAYASASI

**7.1. **Durum değişmedikçe bildirim üretilmez (TUT→TUT = sessiz).

**7.2. **Cuma 18:00 → Haftalık portföy özeti (değişim olmasa bile gönderilir).


#### 7.3. ACİL KOD Tetikleyicileri

Anında WhatsApp + uygulama içi push:

1. CEO istifası / ani yönetim değişikliği
2. İflas / konkordato ilanı
3. Devasa blok satış (>%5 free float tek günde)
4. VIX > 40 ve %50+ artış (24 saat) — ABD hisseleri için
5. VSTOXX > 35 ve %50+ artış (24 saat) — Alman/Euro hisseleri için
6. Piyasa circuit breaker aktif (NYSE veya XETRA)
7. Savaş, siber saldırı, büyük jeopolitik kriz
8. Dark Pool'da aynı gün 3+ balina çıkışı (GICS sektör kodu bazlı)

#### 7.4. Çapraz Doğrulama (False Alarm Koruması) [GÜÇLENDİRİLDİ]

- En az 2 haber kaynağından (NewsAPI + Finnhub + GDELT) teyit olmadan ACİL KOD gönderilemez
- [YENİ] Her ACİL KOD'a güven skoru eklenir: 2 kaynak teyit = %75, 3 kaynak = %90+
- [YENİ] False alarm oranı haftalık izlenir. %5 üzeri → kalibrasyon tetiklenir
**7.5. **Tatil öncesi (3 gün kala) dark pool balina çıkışı → "Tatil Öncesi Risk Uyarısı"

**7.6. **Kurumsal eylemler 5 iş günü önceden bildirilir: temettü ex-date, M&A, hissedar oylaması, stock split.


#### 7.7. Spam Yasağı

- Günde max 3 bildirim (ACİL hariç)
- Aynı hisse 7 gün içinde aynı kod tekrarı → sadece özet raporda
- [YENİ] Kullanıcı bildirim yoğunluğunu özelleştirebilir (min/normal/agresif)
**7.8. **Bildirim Kanalları:

- WhatsApp: Green API (mevcut çalışan sistem — tüm fazlarda birincil ve tek WhatsApp kanalı)
- Email: SMTP + HTML şablon
- Uygulama içi push notification (PWA — Emergent üzerinden)
- Rapor PDF: S3 presigned URL (24 saat geçerli) veya doğrudan WhatsApp dosya gönderimi

> 📝 NOT: Green API günlük mesaj limitini makul tut (max 50/gün). Ticari fazda çok kullanıcı olduğunda Meta Business API değerlendirilir.


---


## MADDE 8 — ÖĞRENME, EVRİM, MODEL DRIFT, AJAN AĞIRLIKLARI VE HAFIZA


#### 8.1. Ajan Ağırlık Güncelleme Sistemi

- Doğru tahmin → +0.02 (max 2.0)
- Yanlış tahmin → -0.02 (min 0.1)
- Ağırlık 0.3 altı → UYARI
- Ağırlık 0.2 altı → GEÇİCİ DEVRE DIŞI + retraining tetikle
**[YENİ] Doğruluk Ölçütü: **Karar kodunun verildiği tarihten 30/90/180 gün sonraki fiyat hareketi ile karşılaştırma. EKLE → fiyat yükseldi mi? DİKKAT ET → fiyat düştü mü?

**8.2. **Haftalık doğruluk skoru (hit rate) takibi. Hangi veri kaynağı en doğru kararı tetikliyor → otomatik ağırlık artırımı.


#### 8.3. Model Drift Detection

- FinRL + Qlib haftalık RMSE, MAE, directional accuracy takibi
- Directional accuracy 4 hafta %55 altı → model rollback + retraining
- [YENİ] Rule-Based Fallback: Model devre dışı kaldığında basit momentum + makro filtre (GICS sektör momentum + FRED yield curve) devreye girer
- [YENİ] Rollback sonrası modelin son bilinen iyi versiyonuna dönülür (model versiyonlama zorunlu)

#### 8.4. MemGPT Gecelik Konsolidasyon

Framework: MemGPT (github.com/cpacker/MemGPT — Apache-2.0)

Zamanlama: Her gece 03:00 UTC

**Görevler: **

1. Kullanıcı tenant context konsolidasyonu (portföy, risk toleransı, tercihler)
2. Geçmiş kararların doğruluğu → Neo4J ilişki ağırlıklarını güncelle
3. Ajan performans metrikleri → ağırlık tablosunu güncelle
4. [YENİ] Benzer piyasa koşullarında geçmiş kararları indeksle (pattern matching hafızası)
5. [YENİ] Kullanıcı geri bildirimlerini (beğendi/beğenmedi) ajan kalitesine yansıt

#### 8.5. Claude CLI Prompt Güncelleme Mekanizması

- Sistem promptları Claude CLI ile dinamik güncellenir
- Güncelleme: Denetçi Ajan + İnsan Admin çift onayı zorunlu
- [YENİ] Her prompt değişikliği versiyonlanır (git-style), rollback mümkün
- [YENİ] Prompt değişikliği sonrası 24 saat gözlemci mod — kötüleşme varsa otomatik rollback
**8.6. **Walk-Forward Optimization (VectorBT): Standard backtest yasak. Sadece expanding/rolling window. TCA: %0.20 slippage dahil.


---


## MADDE 9 — KULLANICI HAKLARI, ABONELİK, ÖDEME VE UYGUNLUK TESTİ

**9.1. **Abonelik Katmanları:


| Paket | Süre/Limit | Analiz | Bildirim | Öncelik | Paralel Job |
|---|---|---|---|---|---|
| Demo | 7 gün, 2 hisse | Gecikmeli (15dk) | Email | Düşük | 1 |
| Starter | 5 hisse/gün | Gecikmeli (15dk) | Email | Normal | 2 |
| Pro | 10 hisse/gün | Real-time seçenek | WhatsApp+Email | Yüksek | 5 |
| Elite | Sınırsız | Real-time | Tüm kanallar | VIP | 20 |

**9.2. **Ödeme: İyzico (TL/USD), Apple/Google Store, banka havalesi (%5 indirim). e-fatura/e-arşiv GİB entegrasyonu zorunlu.

**9.3. **KVKK/GDPR: "Verilerimi Sil" → 72 saat. Audit log. 30 gün soğutma → secure wipe.


#### 9.4. Uygunluk Testi (Suitability Assessment) — SPK Uyumu [GÜNCELLENDİ]

- Her kullanıcıya kayıtta risk profili anketi (10 soru, 5 dakika)
- Risk kategorileri: Konservatif / Dengeli / Agresif
- Konservatif → tek hisse max %3, sadece temettü hisseleri ve ETF, BIST hissesi max %2 (TL riski)
- Dengeli → tek hisse max %5, tüm hisse türleri
- Agresif → tek hisse max %8 (anayasa limiti)
- BIST hisseleri için ek uyarı: TL değer kaybı riski, yüksek enflasyon ortamı
- Test sonuçları MemGPT'de saklanır, 12 ayda bir yenilenir
- Kişisel kullanım fazında (v1.0): uygunluk testi zorunlu değil, hard gate devre dışı

> ⚠️ **Ticari faza geçişte (çok kullanıcı): SPK mevzuatı gereği uygunluk testi HARD GATE haline gelir.**

**9.5. [GÜNCELLENDİ] **Yasal Onay Zinciri (Kişisel → Ticari Faz):

- Kişisel faz (şimdi): Disclaimer metni yeterli, SPK kaydı gerekmez
- Ticari faza geçişte: SPK kayıt durumu araştırılır → Türk finans hukukçusu
- ABD kullanıcıları eklenirse: SEC/FINRA disclaimer → ABD hukukçusu
- Disclaimer: TR + EN ayrı — hukukçu onayı öncesi geçici metin kullanılır

---


## MADDE 10 — PORTFÖY YÖNETİMİ VE RİSK KONTROL KANUNU


#### 10.1. Pozisyon Sizing

- Framework: Skfolio (BSD-3)
- Algoritma: Half-Kelly (konservatif) veya Risk-Parity
- Volatilite tahmini: GARCH(1,1) veya EWMA — Half-Kelly girdisi
- Tek hisse maksimum: portföyün %8'i
- [YENİ] Uygunluk testine göre dinamik limit (Konservatif: %3, Dengeli: %5, Agresif: %8)

#### 10.2. Sektör/Coğrafi Limitler

- Tek sektör max: %25 (GICS sektör kodları)
- Tek ülke max: %60 (ABD için)
- Tek bölge max: %75
- [YENİ] Sektör konsantrasyonu uyarısı: %20 aşıldığında erken uyarı

#### 10.3. Drawdown Kontrolü

- %10 → DİKKAT ET kodu + portföy gözden geçirme
- %15 → BEKLE modu + insan onayı zorunlu (yeni EKLE yasak)
- [YENİ] %20 → Tam dondurma: hiçbir karar kodu üretilmez, sadece insan müdahalesi

#### 10.4. Korelasyon İzleme

- 30 günlük korelasyon matrisi — günlük hesaplanır
- İki hisse arası korelasyon >0.85 → "Konsantrasyon Riski" uyarısı + EKLE yasak
- [YENİ] 60 günlük rolling korelasyon da izlenir (trend değişimi tespiti)

#### 10.5. Likidite Kontrolü

- Pozisyon > hissenin 20 günlük ortalama hacminin %5'i → red
- Dark Pool OTC sıkışma riski değerlendirilir
- [YENİ] Bid-ask spread izleme: spread > %0.5 → likidite uyarısı

#### 10.6. Rebalancing

- Aylık drift kontrolü (hedeften ±%5 sapma → öneri üret)
- Rebalancing kararı "İNSAN ONAYI GEREKLİ" etiketiyle sunulur
- [YENİ] Vergi-etkin rebalancing: Tax-loss harvesting fırsatı varsa rebalancing ile birleştir

#### 10.7. Vergi Optimizasyonu (Tax-Loss Harvesting)

- 3 aylık tarama: %10+ unrealized loss + benzer alternatif mevcut
- ABD hisseleri: Wash sale kuralına uyumlu (30 gün bekleme zorunlu)
- ABD temettü: W-8BEN durumu takibi → withholding %15 (var) vs %30 (yok)
- BIST hisseleri: Sermaye kazancı vergisi %0 (Türk yatırımcı, 2 yıl+ tutulan). Temettü stopaj %10.
- Yabancı hisse (ABD) → Türkiye'de beyan yükümlülüğü (yıllık gelir beyanı eşiği: 230.000 TL 2024)
- TL kur farkı: BIST → TL, ABD → USD cinsinden takip. Kur farkı vergi matrahına dahil değil (Türkiye 2024 mevzuatı).
- Rapora "vergi verimliliği notu" eklenir — bilgi amaçlı, kesin vergi tavsiyesi değil

---


## MADDE 11 — STRESS TEST, BLACK SWAN, İNSAN KONTROLÜ VE MODEL DECAY


#### 11.1. Haftalık Stress Test Senaryoları

1. 2008 Lehman krizi (finansal sektör çöküşü)
2. 2020 COVID çöküşü (pandemi şoku)
3. 2022 Fed faiz artışı döngüsü (büyüme hissesi baskısı)
4. 2024 Orta Doğu/enerji krizi (petrol şoku)
5. Özel: Çin-Taiwan jeopolitik kriz (NVDA/TSM bağlantısı)
6. [YENİ] Özel: EUR/USD parite kırılması (Alman hisseleri için)
7. [YENİ] Özel: Teknoloji sektörü antitrust düzenlemesi (GOOGL bağlantısı)
- Her senaryo portföy bazında simüle edilir: beklenen kayıp %, recovery süresi

#### 11.2. Black Swan Circuit Breaker → Otomatik BEKLE

- VIX >40 ve 24s içinde %50+ artış (ABD)
- VSTOXX >35 ve 24s içinde %50+ artış (Alman/Euro)
- S&P 500 veya DAX günlük gap-down >%7
- Aynı gün 3+ hisse CEO istifası/iflas
- Sektörde (GICS kodu) eş zamanlı 3+ balina çıkışı
- [YENİ] 10Y-2Y yield curve inversion derinleşme (spread < -50bps VE haftalık kötüleşme)

#### 11.3. Human-in-the-Loop (İnsan Onayı Zorunlu)

1. Portföy %10+ drawdown
2. Tek hisse %8 limiti aşımı
3. Ajan oylaması 3-2 bölünmüş (çekişmeli)
4. ACİL KOD tetiklenmiş
5. Denetçi Ajan veto kullandıktan sonra
6. [YENİ] İlk kez EKLE kodu verilen hisse (portföye yeni giriş)
7. [YENİ] Ajan ağırlığı 0.3 altına düşmüş model hâlâ kullanılıyorsa

#### 11.4. Model Decay Protokolü

- Directional accuracy 4 hafta %55 altı → devre dışı + rule-based fallback
- Rule-based fallback: basit momentum + makro filtre
- [YENİ] Fallback modun performansı da izlenir — %50 altı → tam sistem durdurma + insan müdahale

---


## MADDE 12 — OPERASYONEL SÜREKLİLİK, FELAKET KURTARMA, AUDIT VE GÖZLEMLENEBİLİRLİK


#### 12.1. Business Continuity (AWS Multi-AZ)

RTO <5 dakika, RPO <5 dakika


#### 12.2. Yedekleme

- ChromaDB + Neo4J → saatlik S3 yedek (30 gün immutable)
- Redis → AOF + RDB anlık replika
- PostgreSQL → TimescaleDB WAL archiving + S3 snapshot

#### 12.3. Immutable Audit Trail (WORM)

Loglanan her olay:

- Her ajan kararı (sinyal, confidence, reasoning)
- Her kullanıcı raporu (tam içerik)
- Her API çağrısı (kaynak, sonuç, süre)
- Her admin müdahalesi
- [YENİ] Her prompt değişikliği
- [YENİ] Her model versiyonu değişikliği
- [YENİ] Her failover olayı
- [YENİ] Her insan onayı/reddi
Saklama: 7 yıl (ABD SEC/FINRA + Türkiye SPK — konservatif)


#### 12.4. Counterparty Failover

- Ana veri sağlayıcı çökerse: Databento → Polygon → yFinance + Finance Toolkit
- Yedek kaynak kullanımı kullanıcıya bildirilir + raporda belirtilir

#### 12.5. Regülasyon Uyumu [GÜNCELLENDİ]

- ABD: SEC, FINRA — kayıtlı yatırım danışmanı değiliz, disclaimer her raporda zorunlu
- Türkiye: SPK (CMB) — kantitatif analiz aracı, yatırım danışmanlığı faaliyeti değil
- Kişisel kullanım fazı: Yalnızca kendi portföy analizi → regülasyon yükümlülüğü minimal
- Ticari faz öncesi: SPK'ya bildirim zorunluluğu araştırılacak
- MiFID II KAPSAM DIŞI — Alman borsası bu versiyonda yok

#### 12.6. Gözlemlenebilirlik [YENİ]

Platform: Prometheus (Apache-2.0) + kendi UI

**İzlenen metrikler: **

- LLM token kullanımı (model bazlı, günlük/haftalık)
- API rate limitleri (kaynak bazlı, yaklaşma uyarısı)
- Ajan karar süreleri (p50, p95, p99)
- Kullanıcı kuyruk uzunluğu (katman bazlı)
- Failover olayları (kaynak, süre, etki)
- Confluence skoru dağılımı (hisse bazlı, haftalık)
- Maliyet metrikleri (API çağrı başına, analiz başına)

> 📝 NOT: Grafana AGPLv3 kaldırıldı — viral lisans. Yerine: Prometheus + kendi dashboard UI.


---


## MADDE 13 — TEKNOLOJİ ALTYAPISI VE MİKROSERVİS MİMARİSİ


#### 13.1. Mikroservis Yapısı

services/

- darkpool-l2l3-scanner/ — [GÜNCELLENDİ v4.4] FINRA + Squeeze Metrics + Alpaca IEX + Polygon + OpenBB (sürekli tarama, whale detection)
- macro-data-service/ — FRED + ECB SDW + pandas-market-calendars
- fundamental-service/ — yFinance + FinanceToolkit + Qlib + EDGAR
- sentiment-service/ — FinBERT + FinGPT-TR/DE + Finnhub + StockTwits
- backtest-engine/ — VectorBT Pro + walk-forward + TCA
- ai-agent-orchestrator/ — CrewAI + AutoGen + LangGraph + MemGPT
- report-generator/ — Çoklu dil + PDF + HTML + S3
- risk-monitor/ — Drawdown + korelasyon + likidite + GARCH + stress test
- notification-service/ — Green API WhatsApp + Email + Push
- user-service/ — Auth + abonelik + BYOK vault + Uygunluk Testi
- api-gateway/ — FastAPI + rate limiting + kuyruk
- [YENİ] confluence-engine/ — Deterministic skor hesaplama + karar eşik motoru (LLM KULLANMAZ)
- [YENİ] audit-service/ — Immutable log + WORM + 7 yıl saklama
- [YENİ] monitoring-service/ — Prometheus + kendi dashboard
- [YENİ v4.1] router-service/ — Seviye 0 Orkestratör: hisse sınıflandırma, ağırlık atama, cache, piyasa saati
- [YENİ v4.1] stress-test-engine/ — Haftalık 7 senaryo, Black Swan circuit breaker
- [YENİ v4.1] tax-optimizer/ — Tax-loss harvesting, wash sale, W-8BEN, ülke bazlı vergi kuralları
- [YENİ v4.1] github-repo-manager/ — Repo keşif, klonlama, test, entegrasyon pipeline

#### 13.2. GitHub Repo Kataloğu

(Madde 2.2'deki kaynak listesi + aşağıdaki framework'ler)


| Kategori | Araç | Lisans |
|---|---|---|
| Orkestrasyon | n8n | Fair-Code |
| Orkestrasyon | Apache Airflow | Apache-2.0 |
| Orkestrasyon | Redis | BSD-3 |
| Ajan Framework | CrewAI | Apache-2.0 |
| Ajan Framework | LangGraph | MIT |
| Ajan Framework | AutoGen/AG2 | Apache-2.0 |
| Ajan Framework | LangChain | MIT |
| Ajan Framework | LlamaIndex | MIT |
| Ajan Framework | MemGPT | Apache-2.0 |
| Ajan Framework | FinRobot | MIT |
| Ajan Framework | SuperAGI | MIT |
| Veritabanı | PostgreSQL+TimescaleDB | Apache-2.0 |
| Veritabanı | ChromaDB | Apache-2.0 |
| Veritabanı | Qdrant (yedek) | Apache-2.0 |
| Veritabanı | Neo4J Enterprise | Ücretli |
| Güvenlik | HashiCorp Vault | MPL-2.0 |
| API/Backend | FastAPI | MIT |
| API/Backend | Uvicorn | BSD-3 |
| API/Backend | Pydantic | MIT |
| Bildirim | Green API Python | MIT |
| Gözlem | Prometheus | Apache-2.0 |


#### 13.3. Backtest ve ML

- Walk-Forward Optimization zorunlu (standard backtest yasak)
- TCA: %0.20 slippage modeli
- ML Retraining: FinRL + Qlib haftalık
- TimeGPT/Chronos: uzun vade fiyat projeksiyonu

---


## MADDE 14 — İŞ AKIŞ DİYAGRAMI VE ORKESTRASYON PROTOKOLÜ [YENİ]

Bu madde, bir analiz talebinin baştan sona nasıl işlendiğini tanımlar.


#### 14.1. Ana İş Akışı

1. Kullanıcı analiz talebi gönderir (ticker + tercihleri)
2. API Gateway → JWT doğrulama + rate limit + kuyruk
3. Orkestratör Router (Seviye 0) → hisse sınıflandırma + ağırlık atama
4. ChromaDB cache kontrolü → 24h içinde varsa önbellekten dön
5. Piyasa saati kontrolü (pandas-market-calendars) → kapalıysa zamanlayıcıya at
6. Seviye 1 Veri Ajanları → 5 katmandan paralel veri çekme
7. Veri kalite kontrolü (tazelik + completeness) → eksikse failover
8. Seviye 2 Analist Ajanlar → 5 ajan paralel analiz (CrewAI)
9. Output schema validation (Pydantic) → parse error varsa retry
10. Seviye 3 Confluence Motoru → ağırlıklı skor hesaplama
11. Çatışma tespiti → varsa Seviye 5 Çatışma Çözücü
12. Seviye 4 Denetçi Ajan → self-critique + veto kontrolü
13. Risk Monitor kontrolü (drawdown, korelasyon, likidite)
14. Stress test sonuçları entegrasyonu
15. Human-in-the-Loop gerekli mi? → gerekiyorsa beklet
16. Seviye 6 Rapor Üretici → 5 bölümlü rapor
17. Bildirim servisi → WhatsApp/Email/Push
18. ChromaDB'ye cache yaz + Audit Trail'e log
19. MemGPT'ye sonuç bildir (gecelik konsolidasyon için)

#### 14.2. ACİL KOD İş Akışı

1. n8n tetikleyici → haber/veri feed izleme
2. ACİL KOD koşulu tespit
3. Çapraz doğrulama (min 2 kaynak)
4. Güven skoru hesapla
5. Etkilenen portföyleri belirle
6. Anlık bildirim gönder (WhatsApp + push)
7. İlgili hisseler için olağanüstü analiz tetikle
8. Audit Trail'e log

#### 14.3. Gecelik Bakım İş Akışı (03:00 UTC)

1. MemGPT konsolidasyonu (kullanıcı bazlı)
2. Neo4J ilişki ağırlıkları güncelleme
3. Ajan ağırlık tablosu güncelleme (hit rate bazlı)
4. Model drift kontrolü (RMSE, MAE, directional accuracy)
5. Korelasyon matrisi yeniden hesaplama
6. ChromaDB cache temizliği (>24h)
7. Haftalık stress test çalıştırma (Pazar gecesi)

#### 14.4. Haftalık Kontrol Döngüsü

- Pazartesi: Makro veri güncelleme (FRED, ECB)
- Salı-Perşembe: Normal analiz döngüsü
- Cuma 18:00: Haftalık portföy özeti
- Pazar 03:00: Stress test + model drift kontrolü + retraining

---


## MADDE 15 — GITHUB REPO KEŞİF VE ENTEGRASYON SİSTEMİ [YENİ v4.1]

Bu madde, pahalı finansal veri servislerinin GitHub üzerindeki ücretsiz açık kaynak alternatifleriyle değiştirilmesini ve sistemin otomatik olarak repo bulma, klonlama, test etme ve entegre etme yeteneğini tanımlar.


#### 15.1. Otomatik Repo Keşif Mekanizması

Sistem, ihtiyaç duyduğu veri/araç için GitHub'da otomatik arama yapabilir:

1. Veri ihtiyacı tespit edilir (örn: GEX verisi gerekli ama Databento BYOK bağlı değil)
2. GitHub API ile topic/keyword araması yapılır (örn: 'gamma-exposure python MIT')
3. Sonuçlar lisans filtresi uygulanır: MIT, Apache-2.0, BSD, XFree86 KABUL — GPL, AGPL RED
4. Star sayısı, son commit tarihi, issue/PR aktivitesi değerlendirilir
5. Aday repo Entegrasyon Pipeline'ına alınır

#### 15.2. Repo Entegrasyon Pipeline (ZORUNLU)

Hiçbir GitHub reposu bu pipeline'dan geçmeden sisteme entegre edilemez:

1. Lisans kontrolü: GPL/AGPL → otomatik RED. Viral lisans riski sıfır tolerans.
2. Güvenlik taraması: Bağımlılık CVE kontrolü (pip-audit / npm audit)
3. Sandbox testi: İzole Docker container'da çalıştırma (ana sisteme dokunmaz)
4. Veri kalite testi: Bilinen verilerle output doğrulama (%95+ accuracy gerekli)
5. Performans testi: Latency (p95 < 5 saniye), memory kullanımı
6. 2 hafta gözlemci modu: Production'da çalışır ama karar vermeye dahil edilmez
7. İnsan onayı: Denetçi Ajan + Admin çift onay sonrası üretime alınır

> ⚠️ **Bu pipeline çiğnenemez. Acil durumlarda bile en az Adım 1-4 zorunludur.**


#### 15.3. Repo İzolasyon Stratejisi

- Her GitHub reposu ayrı Docker container'da çalışır
- Ana sisteme sadece JSON/REST API üzerinden veri aktarır (network boundary)
- Repo'nun kaynak kodu ana sisteme import edilmez — DATA olarak kullanılır
- AGPL riskli repolar (OpenBB gibi): kesinlikle ayrı container + network boundary
- Repo güncelleme: Haftalık otomatik git pull + pipeline Adım 2-5 tekrarı

#### 15.4. Free-First GitHub Cascade (Madde 5.1 Genişletilmiş)

Veri ihtiyacı karşılama sırası:

1. GitHub açık kaynak repo (Katman F — ücretsiz)
2. Ücretsiz API (FRED, FINRA, Squeeze Metrics DIX.csv)
3. OpenRouter free modeller
4. Freemium API (Polygon basic, Finnhub basic)
5. BYOK kullanıcının kendi key'i
6. Master key (ücretli) — son çare

> 📝 NOT: GitHub reposu mevcut ve çalışıyorsa, ücretli servise kesinlikle geçilmez.


#### 15.5. Hedef Maliyet Tasarrufu (DÜRÜST DEĞERLENDİRME)


| Pahalı Servis | Aylık Maliyet | Ücretsiz Alternatif | Gerçek Tasarruf |
|---|---|---|---|
| Bloomberg Terminal | $2,000+ | yFinance + FinanceToolkit + FRED + Alpaca | %100 |
| SpotGamma GEX | $40 | jensolson/SPX-GEX + gex-tracker + Squeeze Metrics | %100 |
| Unusual Whales Flow | $60 | aluay/Insight + GammaGEX + FINRA RegSho | %90 (kısmi) |
| FlowAlgo | $100 | Institutional-Order-Flow + FINRA + Polygon free | %85 (kısmi, gecikmeli) |
| Databento L2/L3 (Hisse) | $500+ | YOK — gerçek konsolide L2/L3 ücretsiz mevcut değil | %0 — ticari fazda gerekli |
| Refinitiv Tick History | $1,800+ | LOB-feature-analysis + PyLOB (akademik/eğitim amaçlı) | %30 (sınırlı) |


> ⚠️ **DÜZELTME: bmoscon/orderbook ve cryptofeed KRİPTO borsaları için tasarlanmıştır (Binance, Coinbase). ABD hisse senedi L2/L3'üne doğrudan uygulanamaz. Bu repolar sadece ileride kripto varlık eklenirse kullanılır.**

Gerçekçi toplam tasarruf: ~$2,200/ay tam ücretsiz + ~$260/ay kısmi/gecikmeli alternatif. L2/L3 tam derinlik ticari faza kadar ertelenir (Databento/Polygon Business gerekir).


#### 15.6. [YENİ v4.4] Dark Pool + L2/L3 Sürekli Tarama Servisi (darkpool-l2l3-scanner)

Ayrı, sürekli çalışan mikroservis. Amaç: mevcut ücretsiz kaynaklardan azami dark pool/mikrostrüktür sinyali çıkarmak, sınırlamaları dürüstçe raporlamak.


| Bileşen | Kaynak | Tarama Sıklığı | Çıktı |
|---|---|---|---|
| Dark Pool Index | Squeeze Metrics DIX.csv | Günlük (piyasa kapanışı sonrası) | DIX skoru, GEX skoru |
| Short Volume | FINRA RegSho | T+1 (ertesi gün) | Dark pool short volume % |
| Kısmi L2 Derinlik | Alpaca IEX feed | Gerçek zamanlı (websocket) | IEX order book (~%2-3 hacim örneklem) |
| Block Trade Tespiti | Polygon.io free (15dk gecikmeli) | 15 dakikada bir | Whale event listesi |
| OTC/Dark Pool modülü | OpenBB Platform (kişisel kullanım) | Günlük | OTC hacim, dark pool detayı |
| GEX Hesaplama | jensolson/SPX-GEX (CBOE veri) | Günlük | Dealer gamma exposure |

**Whale Detection Algoritması: **Tek blok işlem > günlük ortalama hacmin (ADV) %5'i → whale event olarak işaretlenir. Aynı gün 3+ whale event aynı sektörde → Madde 7.3 ACİL KOD tetikleyicisi.

**Kompozit Dark Pool Skoru: **normalize(DIX) × 0.4 + normalize(IEX_depth_imbalance) × 0.3 + normalize(whale_event_count) × 0.3 → RAA'ya beslenir.


> ⚠️ **HER RAPORDA ZORUNLU UYARI: "Bu dark pool/L2 verisi örneklem ve/veya gecikmeli kaynaklardan derlenmiştir (IEX ~%2-3 hacim, FINRA T+1, Polygon 15dk gecikme). Tam konsolide piyasa derinliğini yansıtmayabilir."**


---


## MADDE 16 — ALTYAPI VE İLETİŞİM PROTOKOLÜ [YENİ v4.1]


#### 16.1. Servisler Arası İletişim

- Senkron çağrılar: gRPC (protobuf schema) — ajan-ajan, ajan-veri servisi arası
- Asenkron mesajlaşma: Redis Streams — event-driven iş akışları, ACİL KOD
- Request-Response: FastAPI REST — dış API Gateway, frontend bağlantısı
- Pub/Sub: Redis Pub/Sub — bildirim fanout, monitoring event'leri

#### 16.2. Health Check ve Service Discovery

- Docker healthcheck: Her container'da /health endpoint (30s interval)
- Liveness probe: HTTP GET /healthz → 200 OK veya container restart
- Readiness probe: HTTP GET /readyz → servis veri almaya hazır mı?
- Service mesh: Docker Compose DNS (basit) → Kubernetes'e geçişte Consul

#### 16.3. Database Stratejisi

- Migration: Alembic (SQLAlchemy) — her schema değişikliği versiyonlanır
- TimescaleDB hypertable: Fiyat verisi, makro indikatörler → otomatik partitioning
- Redis database ayrımı: DB0=cache, DB1=rate-limit, DB2=task-queue, DB3=pub/sub
- ChromaDB → Qdrant failover: ChromaDB health check başarısızsa otomatik geçiş
- Neo4J Enterprise: Lisans maliyeti bütçeye dahil ($36K/yıl veya Community + ayrı container)

#### 16.4. SSL ve Sertifika Yönetimi

- Let's Encrypt + certbot: 90 günde bir otomatik yenileme
- Nginx reverse proxy: TLS 1.3 zorunlu, HTTP/2 aktif
- Internal servisler: mTLS (mutual TLS) ile şifreli iletişim

#### 16.5. Python Standartları

- Python 3.11+ (tüm servisler)
- Docker base image: python:3.11-slim-bookworm
- Dependency management: pip + pip-audit (CVE tarama)
- Code quality: ruff (linting) + mypy (type checking)

---


## MADDE 17 — 7-EC2 DAĞITIK MİMARİ VE AĞ TASARIMI [YENİ v4.4]

**17.1. **Genel Mimari: 7 ayrı AWS hesabı → 7 EC2 t2.micro → Tailscale mesh VPN ile tek private ağ. Tüm fazlar baştan tam kurulur.


#### 17.2. Neden 7 Ayrı EC2?

- t2.micro = 1 vCPU + 1GB RAM — tek servise yeter, hepsine yetmez
- 7 ayrı hesap = 7 × 750 saat/ay ücretsiz EC2 = toplamda 7 makine ücretsiz
- Servisler izole çalışır → bir servis çökerse diğerleri etkilenmez

#### 17.3. Neden Tailscale VPN?

- 7 ayrı AWS hesabı = 7 ayrı VPC = birbirini görmez (varsayılan)
- Public IP ile iletişim: güvensiz, her şey açık internette dolaşır
- Tailscale: Her EC2'ye kurulur, 100.x.x.x özel IP atar, sunucular sanki aynı odadaymış gibi görür
- Kurulum: Her EC2'de 2 komut → ücretsiz (100 cihaza kadar)
- Kaspersky VPN: Sadece tarayıcı trafiği için — sunucu-sunucu iletişim için kullanılamaz

#### 17.4. EC2 Servis Dağılımı


| EC2 # | AWS Hesap | Servisler | RAM Tahmini | Kritiklik |
|---|---|---|---|---|
| #1 | hesap-1 | PostgreSQL + TimescaleDB + Redis | ~800MB | KRİTİK — veri tabanı |
| #2 | hesap-2 | api-gateway + user-service + router-service + audit-service | ~400MB | KRİTİK — giriş kapısı |
| #3 | hesap-3 | macro-data-service + darkpool-aggregator + fundamental-service | ~600MB | Yüksek — veri katmanı |
| #4 | hesap-4 | ai-agent-orchestrator (CrewAI + LangGraph + AutoGen + MemGPT) | ~900MB | KRİTİK — ajan beyni |
| #5 | hesap-5 | sentiment-service (FinBERT ~400MB) + notification-service | ~900MB | Orta — analiz desteği |
| #6 | hesap-6 | backtest-engine + stress-test-engine + confluence-engine + risk-monitor | ~800MB | Orta — analiz motoru |
| #7 | hesap-7 | n8n + report-generator + monitoring-service + github-repo-manager + tax-optimizer | ~700MB | Orta — orkestrasyon |


#### 17.5. Ağ Topolojisi

Tailscale mesh ağında her servis diğerini Tailscale IP'si üzerinden bulur:

- EC2 #1 Tailscale IP: 100.64.0.1 → PostgreSQL: 5432, Redis: 6379
- EC2 #2 Tailscale IP: 100.64.0.2 → API Gateway: 8000 (tek dışarıya açık port)
- EC2 #3 Tailscale IP: 100.64.0.3 → Veri servisleri: 8001-8003
- EC2 #4 Tailscale IP: 100.64.0.4 → Ajan orchestrator: 8004
- EC2 #5 Tailscale IP: 100.64.0.5 → Sentiment + Notification: 8005-8006
- EC2 #6 Tailscale IP: 100.64.0.6 → Analiz motorları: 8006-8009
- EC2 #7 Tailscale IP: 100.64.0.7 → n8n: 5678, Report: 8010, Monitoring: 9090

> 📝 NOT: Dışarıya açık tek port: EC2 #2'deki API Gateway port 443 (HTTPS). Emergent ve Green API buraya bağlanır.


#### 17.6. Kurulum Sırası

1. Tüm AWS hesapları oluşturulur, EC2 t2.micro instance'lar başlatılır (Ubuntu 22.04 LTS)
2. Her EC2'ye Tailscale kurulur → mesh ağ kurulur
3. EC2 #1: PostgreSQL + TimescaleDB + Redis → temel altyapı
4. EC2 #2: API Gateway + Auth → giriş kapısı
5. EC2 #3: Veri servisleri → FRED, BIST, Dark Pool bağlantıları test edilir
6. EC2 #4: Ajan orchestrator → LLY ile ilk test analizi
7. EC2 #5-7: Kalan servisler → tam sistem devreye alınır
8. Emergent frontend EC2 #2'deki API'ye bağlanır
9. Green API WhatsApp → EC2 #7'deki notification-service'e bağlanır
10. LLY üzerinde tam döngü testi → rapor üretilir, WhatsApp'a gönderilir

#### 17.7. Kişisel → Ticari Faz Geçiş Kriterleri

- LLY testi dahil en az 5 hisse üzerinde tutarlı analiz (1-2 ay)
- Hata oranı < %5 (confluence motoru, denetçi, rapor üretici)
- WhatsApp bildirimleri düzenli ve doğru geliyor
- Gecelik MemGPT konsolidasyonu stabil çalışıyor
- Walk-forward backtest sonuçları directional accuracy > %55
Bu kriterler karşılandığında: EC2'ler t3.medium/large'a yükseltilir, Neo4J Enterprise eklenir, SPK araştırması başlatılır, gerekirse ücretli API'lar devreye alınır.


---


## MADDE 18 — DEĞİŞMEZLİK, ANAYASA ÜSTÜNLÜĞÜ VE REVİZYON

**18.1. **Bu anayasa tüm sprint'lerin, kod deploy'larının ve sistem güncellemelerinin üzerindedir. Hiçbir koşulda çiğnenemez.

**18.2. **Hiçbir sprint kodu, hotfix veya feature anayasaya aykırı olamaz. Aykırı kod deploy edilemez, test ortamına bile alınamaz.

**18.3. **Anayasa değişikliği: İnsan Sistem Mimarı onayı + 24 saat cooling-off + Versiyonlama (v4.4, v4.4...) + Eski versiyonla çalışan ajan → güvenli mod.

**18.4. **Deployment Sırası (7 EC2 Tam Kapasite — Madde 17.6 detaylandırır):

1. 7 AWS hesabı kur → 7 EC2 t2.micro başlat (Ubuntu 22.04 LTS)
2. Tailscale mesh VPN kur → tüm EC2'ler birbirini görür
3. EC2 #1: PostgreSQL+TimescaleDB + Redis + ChromaDB (temel altyapı)
4. EC2 #2: API Gateway + Auth + Router → LLY ile ilk bağlantı testi
5. EC2 #3: Veri katmanı → yFinance, FRED, TCMB, FINRA, Squeeze Metrics DIX
6. EC2 #4: Ajan orchestrator → OpenRouter free modeller ile LLY test analizi
7. EC2 #5: FinBERT sentiment + Green API WhatsApp notification
8. EC2 #6: Backtest engine + Confluence + Risk monitor
9. EC2 #7: n8n zamanlama + Rapor üretici + Monitoring
10. Emergent UI → EC2 #2 API'ye bağlan → tam döngü testi: LLY raporu WhatsApp'a gelir
ALPHAWISE Sistem Anayasası v4.4 — SON HAL / Deployment Versiyonu

Tarih: Temmuz 2026

Durum: ONAYLANDI — Deployment başlatılabilir

v4.4 (SON HAL): Twilio tamamen kaldırıldı → Green API. Emergent ücretsiz başlangıç. 7-EC2 Tailscale mimarisi kesinleşti.

Toplam: 18 madde, 7 seviye ajan, 18 mikroservis, 7 EC2, 6 veri katmanı (A-F), 13+ GitHub repo. Test hissesi: LLY.
