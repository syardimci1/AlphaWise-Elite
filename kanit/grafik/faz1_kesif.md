# FAZ 1 — KEŞİF VE KABİLİYET ÖLÇÜMÜ

**Tarih:** 22.09.2026 · **Oturum:** claude3 · **Worktree:** `otonom/claude3/grafik-terminali` (origin/main `06e86dc`)
**Yöntem:** 5 eksende paralel salt-okunur keşif (workflow) + C1 için doğrudan canlı ölçüm.

---

## 1. ÇİZİM MOTORU — kütüphanede yerleşik araç YOK, primitives VAR

**Kurulu sürüm:** beyan `^5.0.0`, **gerçek 5.2.1** (`node_modules/lightweight-charts/package.json:2`; bundle `version()` → `5.2.1`). Tek çalışma-zamanı bağımlılığı `fancy-canvas@2.1.0`.

| Soru | Cevap | Kanıt |
|---|---|---|
| Yerleşik çizim aracı (trend/fib/dikdörtgen)? | **YOK** | `typings.d.ts` içinde export edilen TÜM fonksiyonlar 12 tane ve hiçbiri çizim aracı değil. `fibonacci` kelimesi tip tanımlarında ve bundle'da **0 kez** geçiyor. |
| Primitives API? | **VAR** | `ISeriesApi.attachPrimitive(ISeriesPrimitive)` `typings.d.ts:2591`, `detachPrimitive` `:2598`; `IPaneApi.attachPrimitive(IPanePrimitive)` `:2055` |
| Çizim katmanı sözleşmesi | `IPrimitivePaneView { zOrder?(): 'bottom'\|'normal'\|'top'; renderer(): IPrimitivePaneRenderer }` → `draw(target: CanvasRenderingTarget2D, utils?)` | `:2314-2325`, `:2300`, `:4889` |
| Fare etkileşimi (seç/taşı) | `hitTest?(x, y): PrimitiveHoveredItem \| null` — `{distance?, hitTestPriority?, cursorStyle?, externalId, zOrder}` | `:3819-3856` |
| Çoklu panel (RSI/MACD alt panel) | **VAR, tam destek**: `addPane()`, `panes()`, `removePane()`, `swapPanes()`, `moveToPane()`, `addSeries(..., paneIndex)` | `IChartApiBase` / `ISeriesApi` bildirimleri |
| PNG dışa aktarma (C9) | **VAR**: `takeScreenshot(addTopLayer?: boolean, includeCrosshair?: boolean): HTMLCanvasElement` | `:1767` |

### ⚠️ C9 için kritik tuzak (kanıtlı)
`takeScreenshot()` varsayılanı `addTopLayer=false` ve bu durumda **primitives ekran görüntüsüne DAHİL EDİLMEZ**
(`typings.d.ts:1761-1766` doc: *"if true, the top layer and primitives will be included"*).
Yani **çizimlerin PNG'de çıkması için `takeScreenshot(true)` zorunludur.** Varsayılanla test edilirse "çizimler kayboluyor" diye
yanlış bir hata avına çıkılır.

**KARAR (ADR-1'e girdi):** Kendi primitive tabanlı çizim motorumuz yazılacak. Üçüncü taraf çizim eklentisi
DEĞERLENDİRİLMEDİ ÇÜNKÜ gerek yok: primitives API'si seç/taşı/çiz için gereken her şeyi (render + hitTest + zOrder)
sağlıyor ve yeni bağımlılık bundle bütçesini (C5) riske atardı.

---

## 2. VERİ GERÇEKLİĞİ (C1) — CANLI ÖLÇÜLDÜ, en kısıtlayıcı bulgu

`market-data-service`'in **TEK** veri ucu var ve **zaman dilimi parametresi YOKTUR**:

```
GET /health
GET /price/{ticker}   parametreler: [ticker, limit (varsayılan 60)]
```
*(kanıt: `docker exec alphawise-market-data` → `/openapi.json`)*

### Ölçülen gerçek veri (MSFT, canlı)

| Ölçüm | Değer |
|---|---|
| Çözünürlük | **YALNIZCA GÜNLÜK** (`date: "2026-06-16"`, bar/gün) |
| Azami derinlik | **1681 bar**, `2020-01-02` → `2026-09-10` (limit=10000 verilse de 1681'de tavanlanıyor) |
| Varsayılan pencere | **60 bar (~3 ay)** — proxy `limit`'i İLETMİYOR |
| OHLC gerçek mi | **EVET** — `h>l` oranı **1.0** (1681/1681) |
| Boşluk deseni | 1 gün×1316, 3 gün×299 (hafta sonu), 4 gün×50 (tatil), 2 gün×15 — klasik işlem-günü serisi |
| Bölünme düzeltmesi | `factor` alanı VAR; 1681 barın **1604**'ünde `factor != 1.0` |
| Tazelik | Son bar `2026-09-10` — **bugünden 12 gün eski** |
| Kaynak | `source: "merkezi_depo"` (canlı Alpaca değil, merkezi depo) |

### C1 SONUCU — hangi zaman dilimi mümkün

| Dilim | Durum | Gerekçe |
|---|---|---|
| **Günlük (1G)** | ✅ YERLİ | tek gerçek çözünürlük |
| **Haftalık (1H)** | ✅ TÜRETİLMİŞ | günlükten resample — C1 izin veriyor, "türetildi" etiketi ZORUNLU |
| **Aylık (1A)** | ✅ TÜRETİLMİŞ | aynı |
| 1dk / 5dk / 15dk / 1saat | ❌ **İMKÂNSIZ** | yukarı akışta gün içi veri **hiç yok** — buton devre dışı + neden etiketi (Y3: uydurulmaz) |
| **VWAP** | ❌ **İMKÂNSIZ** | C4 "yalnızca gün içi veri varsa" diyor; gün içi veri yok → gösterge listesinden ÇIKARILDI |

### ⚠️ Ölçülen risk: pencere uyuşmazlığı
Proxy `limit`'i iletmediği için grafik **60 bar** gösteriyor; olay kaynakları (13F çeyreklik, kongre işlemleri ~1 yıl)
çok daha geriye gidiyor. Bu pencerenin dışındaki marker'lar için **mum yok**. Çok-zaman-dilimi için `limit`
parametrelendirilecek (S1), aksi halde olay katmanı sessizce marker kaybeder.

---

## 3. MEVCUT BİLEŞENLER — yeniden kullanılacak, kopyalanmayacak (C8)

| Dosya | Satır | Rol |
|---|---|---|
| `frontend/components/PriceChart.tsx` | 58 | v5 API'sini DOĞRU kullanıyor (`chart.addSeries(CandlestickSeries)`), `onHazir(chart, series)` ile dışarı veriyor |
| `frontend/components/EventOverlayLayer.tsx` | 178 | Olay katmanı — `PriceChart`'ın verdiği `chart`/`series` ile çalışıyor, feature flag'e bağlı |
| `frontend/src/lib/koyfin-{marker,olaylar,zaman}.ts` | — | Marker üretimi, olay çekme, zaman dönüşümü — **C2 gereği zaman modülü yeniden kullanılacak** |
| `frontend/src/app/api/market-data/[ticker]/route.ts` | 33 | Sunucu-tarafı proxy (CORS + güvenlik gerekçesi H-002'de belgeli) |

---

## 4. TEST/BUILD KISITLARI — sürpriz: vitest/jest YOK

| Bulgu | Etki |
|---|---|
| Test koşucusu **çıplak `node:test`**: `node --test tests/*.test.mjs && node --import tsx --test tests/*/*.test.ts` | `describe/it/expect`, `vi.mock` **KULLANILAMAZ**; `node:test` + `node:assert/strict` kullanılacak |
| **Sessiz kapsam boşluğu**: `tests/x.test.ts` (kökte) ve `tests/alt/x.test.mjs` **HİÇ ÇALIŞMAZ**, hata da vermez | Yeni TS testleri **mutlaka** `tests/<konu>/*.test.ts` altına |
| `&&` zinciri | `.mjs` paketi düşerse `.ts` paketi hiç çalışmaz |
| Bundle taban çizgisi (ölçülü) | `/dashboard`: **75.4 kB** kendi / **219 kB** First Load JS. lightweight-charts +52 kB, olay katmanı +5 kB |
| **V-009 açık**: Next.js tablosundaki rakam gzip mi ham mı **teyit edilmemiş** | C5'teki "≤60KB gzip" bütçesi bu belirsizlikle birlikte raporlanacak — uydurma birim kullanılmayacak |
| `middleware.ts` matcher `/api/:path*` (`:333`), çerez yoksa **401** (`:253`) | **Y10 otomatik sağlanıyor** — yeni rotalar da kapı arkasında; test ile kanıtlanacak |
| T4 doğrulandı: commit'li `tsconfig.json` yerel `next build` ile uyumsuz (build onu değiştiriyor) | Build sonrası `tsconfig.json`/`next-env.d.ts` değişikliği **geri alınacak**, "istenmeyen değişiklik" sanılıp döngüye girilmeyecek |

---

## 5. HUKUKİ DİL (Y8) — kaynak BAŞKA DEPODA

`hukuki_dil` modülü bu depoda **YOK**; `/opt/alphawise/godmode-paper-trading-service/planlama/src/hukuki_dil.py`
içinde ve **15 yasaklı regex** taşıyor (emir kipi `\w+m[ae]l[iı]s[iı]n[iı]z`, `tavsiye\s+ed[ei]r`, `\ben iyi\b`,
`\b(al[iı]n|sat[iı]n|girin|yat[iı]r[iı]n)\b`, `kesin\s+kazan`, `risksiz`, `garanti\s+ed…` vb.).

**Karar:** Depo sınırı aşılmayacak (Y16). Yasaklı kalıp listesi bu depoya **kopyalanmayacak**; grafik arayüzü
kendi metinlerini o listeye UYACAK şekilde yazacak ve bir testle (statik metin taraması) kilitleyecek.
Tek doğruluk kaynağı olarak o dosyaya ATIF yapılacak.

---

## 6. ŞÜPHECİLİK TURU — "kendimi kandırıyor muyum?"

1. **"Çok zaman dilimli" gerçekten yapılabilir mi?** Hayır, istenen ölçekte yapılamaz — gün içi veri YOK.
   Dürüst kapsam: günlük + türetilmiş haftalık/aylık. Bunu gizlemek Y3 ihlali olurdu; butonlar
   devre dışı + neden etiketiyle gösterilecek.
2. **VWAP listede duruyor ama mümkün mü?** Hayır. C4'ün kendi koşulu ("yalnızca gün içi veri varsa")
   sağlanmıyor → kapsam dışı, raporda açıkça yazılacak.
3. **Bundle bütçesi ölçülebilir mi?** Kısmen — birim (gzip/ham) belirsizliği V-009 olarak açık.
   "≤60KB gzip" iddiası bu belirsizlik belirtilmeden kullanılmayacak (Y11).
4. **7 çizim aracı + 6 gösterge + karşılaştırma + mobil + a11y + PNG tek oturumda biter mi?**
   Dürüst cevap: hayır. Dikey dilimler öncelik sırasına konacak; bitmeyenler FAZ 8'de
   **TEST_EDİLEMEDİ / YAPILMADI** olarak açıkça raporlanacak (Y12/Y15), yarım iş "bitti" diye sunulmayacak.
