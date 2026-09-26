# FAZ 1 — KEŞİF: çoklu seri, veri API'si, eksik gün

**Tarih:** 25.09.2026 · **Taban:** `f827ca7`

## 1. Mevcut mimari — "PriceChart.tsx" değil, `GrafikTerminali.tsx`

| Bileşen | Rol | Karar |
|---|---|---|
| `frontend/components/PriceChart.tsx` (58 satır) | Dashboard'daki eski tek mum grafiği; olay katmanı (`onHazir`) ona bağlı | **Dokunulmadı.** Grafik terminali onu zaten kullanmıyor (`GrafikTerminali.tsx:18-21` gerekçesi). |
| `frontend/components/GrafikTerminali.tsx` (815 satır) | Grafik terminali: tek mum serisi + çizim primitive'i + gösterge katmanı + kalıcılık | Karşılaştırma modu **buraya** eklenir; dashboard'un geçtiği prop'lar değişmez → `dashboard/page.tsx`'e dokunulmaz (D2 riski yok). |

Terminal tek sembollüdür: bir `CandlestickSeries`, `seri.attachPrimitive(CizimPrimitive)`, `GostergeKatmani`.
Çizim noktaları fiyat birimindedir (`Nokta.fiyat`), göstergeler fiyat serisinden hesaplanır.
→ Normalize (%) eksende çizimler ve göstergeler **anlamsızdır**; aynı grafiğe konamazlar (ADR-6 §görünüm).

## 2. lightweight-charts 5.2.1 çoklu seri

| Özellik | Kanıt | Sonuç |
|---|---|---|
| Çoklu seri | `chart.addSeries(LineSeries, …)` istenen sayıda çağrılabilir (`typings.d.ts` `addSeries`) | aynı grafikte 2–3 `LineSeries` |
| Yerleşik yüzde modu | `PriceScaleMode.Percentage` = "first **visible** value … is 0%" (`typings.d.ts:145-160`) | **KULLANILMAZ.** Taban, kullanıcı kaydırdıkça/yakınlaştırdıkça kayar; C1 "her serinin ilk günü %0" der. Yüzde kendi saf fonksiyonumuzda, sabit bir taban tarihine göre hesaplanır. |
| Seri etiketi | `SeriesOptionsCommon.title` + `lastValueVisible` | fiyat ekseninde son değerin yanında sembol adı (C3: renk yalnız başına kimlik taşımaz) |
| Özel eksen biçimi | `priceFormat: { type: 'custom', formatter }` (`PriceFormatCustom`) | eksen "%" biçiminde |
| Nokta başı renk | `LineData.color` | aşağıdaki ölçüm |

### 2.1 ÖLÇÜM — eksik gün çizgi serisinde nasıl görünüyor? (Y9 / C4)

Sonda: `kanit/karsilastirma/e2e/bosluk_sondasi.mjs` (gerçek Chromium 1194, `takeScreenshot(true)` piksel sayımı).
Çıktı: `kanit/karsilastirma/faz1_bosluk_sondasi_cikti.txt`. 21 günlük iki seri; kırmızı seride 11 Mart eksik.
Sütunlardaki kırmızı çizgi pikseli:

| Kip | 09→10 | 10→11 | 11 (eksik) | 11→12 | 12→13 |
|---|---|---|---|---|---|
| eksik gün veriden **atlanmış** | 3 | 3 | **3** | 3 | 3 |
| eksik gün **whitespace** `{time}` | 3 | 3 | **3** | 3 | 3 |
| boşluk ÖNCESİ son noktanın `color`'u saydam | 3 | **0** | **0** | **0** | 3 |
| boşluk SONRASI ilk noktanın `color`'u saydam | 3 | 3 | 3 | 3 | **0** |

**Bulgu (varsayımım yanlış çıktı):** bu sürümde çizgi serisi whitespace'i **kesmez**; komşu iki gerçek noktayı
düz çizgiyle birleştirir. Yani "whitespace ver, boşluk olur" yaklaşımı eksik günü **sessizce doğrusal enterpole
edilmiş gibi** gösterirdi — tam olarak Y9'un yasakladığı şey, üstelik görsel olduğu için hiçbir birim testi yakalamazdı.

**Ölçülen mekanizma:** i. noktanın `color`'u i→i+1 segmentini boyar. Boşluktan önceki son noktayı saydam yapmak
köprü segmentini **tamamen** siler, komşu segmentlere dokunmaz. C4 bu mekanizmayla uygulanır (ADR-6).

## 3. Veri API'si — tek tek, toplu uç yok

- Tek uç: `GET /api/market-data/{ticker}?limit=N` → proxy → market-data-service `/price/{ticker}` (`route.ts`).
  Toplu (çoklu sembol) sorgu **yok**. Karşılaştırma her sembol için ayrı, paralel istek atar; yeni uç EKLENMEZ (Y2).
- `limit` 1..2000 doğrulanıyor (`veri-penceresi.ts`); terminal 1500 istiyor, karşılaştırma aynı değeri kullanır.

### 3.1 Eksik gün gerçek bir durum mu? — EVET

`market-data-service/src/main.py` `read_central_csv`: bütünlük kontrolünden (`bar_butunlugu_gecerli`) geçemeyen
satırlar **düşürülüyor**; docstring merkezi depoda **4 649** imkânsız bar bulunduğunu, bir kısmının onarılamadığını
kaydediyor. Yani aynı günde bir sembolde bar olup diğerinde olmaması yalnızca tatil farkı değil, bu depodaki
gerçek veri yolunun doğal sonucu. Ayrıca `hamBarlariCevir` bozuk kayıtları atlıyor (sayısını raporlayarak).

### 3.2 Kapanış fiyatı düzeltilmiş mi? — KAYNAĞA GÖRE DEĞİŞİYOR, doğrulanamadı

- Tiingo yolu (`fetch_and_cache_from_tiingo`): `adjClose` yazılıyor → temettü/bölünme **düzeltilmiş**.
- Merkezi depo defeatbeta yolu (`data-fetcher/scripts/incremental_update.py`, `bulk_fetch_defeatbeta_us.py`):
  `factor = 1.0` sabit, düzeltme durumu kodda belli değil.
- Yanıt hangi yoldan geldiğini `source` alanında söylüyor ama hangi CSV'nin hangi araçla yazıldığını söylemiyor.

→ Karşılaştırma bu konuda **iddiada bulunmaz**; lejantta "kapanış fiyatları; temettü/bölünme düzeltmesi kaynağa
göre değişebilir" notu görünür ve tek günde ±%40'ı aşan hareketler sayılıp "bölünme veya veri hatası olabilir"
diye işaretlenir (düzeltilmemiş bir bölünme −%50 gibi görünür; sessizce performans sanılmamalı).

## 4. Kalıcılık deseni (Y8)

`adAlaniAnahtari(onek, kimlik, sembol)` (`cizim-kalicilik.ts`) tek ad alanı kaynağı; `GecikmeliKayit` (300 ms, anahtar
başına); yükleme kapısı anahtarın tamamı (H-1); `depodakiRef` yankı kapısı (H-5); `kayitlariSifirla`; `storage` olayı uyarısı.
Karşılaştırma seçimi aynı fonksiyonla, üçüncü bir tür olarak saklanır: `alphawise:grafik:karsilastirma:v1:<kimlik>:<SEMBOL>`.
Yeni mekanizma icat edilmez.

## 5. Ticker doğrulama

`tickerDogrula` (`servis-proxy.ts`) `next/server` içe aktarıyor → istemci bileşenine alınamaz (sunucu kodu pakete girerdi).
Karşılaştırma modülü aynı deseni tutar; **iki fonksiyonun aynı girdilerde aynı kararı verdiği** bir testle kilitlenir
(sessiz ayrışma yakalanır).
