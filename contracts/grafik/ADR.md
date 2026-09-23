# FAZ 2 — MİMARİ KARAR KAYITLARI (ADR)

**Tarih:** 22.09.2026 · Tümü FAZ 1 ölçümlerine dayanır (`kanit/grafik/faz1_kesif.md`).

---

## ADR-1 — Çizim motoru: kendi primitive tabanlı motorumuz

**Bağlam.** 7 çizim aracı isteniyor. lightweight-charts 5.2.1'de **yerleşik çizim aracı yok**
(kanıtlandı: export edilen 12 fonksiyonun hiçbiri çizim aracı değil, `fibonacci` tip tanımlarında 0 kez geçiyor).
Ama tam bir primitives API'si var: `attachPrimitive`, `IPrimitivePaneView.renderer().draw(target)`,
`hitTest(x,y) → PrimitiveHoveredItem`, `zOrder`.

**Seçenekler.**
| # | Seçenek | Artı | Eksi |
|---|---|---|---|
| A | Üçüncü taraf çizim eklentisi | Hazır araçlar | Yeni bağımlılık → bundle bütçesi (C5) riski, lisans/bakım belirsizliği, v5 uyumu garantisiz |
| B | **Kendi primitive motorumuz** | Sıfır bağımlılık, tam kontrol, hitTest/zOrder zaten var | Çizim/hit-test/taşıma kodunu biz yazarız |
| C | Ayrı bir `<canvas>` katmanı | Kütüphaneden bağımsız | Zoom/pan ile senkron tutmak elle koordinat dönüşümü ister — primitives bunu bedava veriyor |

**Karar: B.** Görev tanımı da "varsayılan tercih: kendi primitive tabanlı motorun (bağımlılık yok)" diyor
ve ölçüm bunu destekliyor.

**Sonuçlar.** Çizim geometrisi **saf fonksiyonlarda** (`cizim-model.ts`) tutulur, render primitive'e delege edilir;
böylece geometri testleri DOM'suz koşar. `takeScreenshot(**true**)` zorunlu (varsayılan `false` primitives'i dışlar).

---

## ADR-2 — Kalıcılık: localStorage, kullanıcı+sembol ad alanlı; DB YOK

**Bağlam.** C3 kalıcılık istiyor. D1 kapısı: üretim veritabanına yazma DUR gerektirir.

**Seçenekler.** A) DB (Supabase) · B) localStorage · C) hiç kalıcılık yok.

**Karar: B.** C3 zaten "varsayılan: tarayıcı localStorage" diyor ve "DB kalıcılığı bu görevde YAPILMAZ".
DB'ye gitmek D1 (DUR) tetiklerdi ve bu görevin kapsamı değil.

**Sonuçlar.**
- Anahtar: `alphawise:grafik:cizim:v1:<kullanici_kimligi>:<SEMBOL>` — **kullanıcılar arası sızıntı yok**
  (kiracı izolasyonu bu depoda zaten sert bir ilke: `tests/kiracilik/sizinti-matrisi.test.ts`).
- Şema **sürümlü** (`v:1`); bilinmeyen/bozuk sürüm → güvenli sıfırlama + kullanıcıya görünür uyarı (sessiz veri kaybı YOK).
- `QuotaExceededError` yakalanır → çizim bellekte kalır, "kaydedilemedi" uyarısı gösterilir (Y9 fail-loud).
- localStorage erişimi try/catch'li: gizli sekme/kapalı depolama çökmeye yol açmaz.

---

## ADR-3 — Göstergeler: saf TS fonksiyonları, istemcide; VWAP KAPSAM DIŞI

**Bağlam.** C4 SMA/EMA/Bollinger/RSI/MACD/hacim/VWAP istiyor ve "referans değerlere karşı test" şart koşuyor.

**Seçenekler.** A) Sunucuda (yeni Python ucu) · B) **İstemcide saf TS** · C) Kütüphane (ör. technicalindicators).

**Karar: B.**
- A yeni bir servis ucu + ağ gecikmesi + kimlik yüzeyi ekler; veri zaten istemcide.
- C yeni bağımlılık → C5 bütçesi; ayrıca saf fonksiyonlar birkaç yüz satır.
- B ile göstergeler **DOM'suz, deterministik** test edilir (`node:test`).

**Sonuçlar.**
- **VWAP KAPSAM DIŞI BIRAKILDI.** Gerekçe ölçülü: gün içi veri yok (`/price` yalnızca günlük döner),
  C4'ün kendi koşulu ("yalnızca gün içi veri varsa") sağlanmıyor. Günlük barla "VWAP" hesaplamak
  yanlış bir sayıyı doğru isimle sunmak olurdu (Y3 ihlali).
- **Isınma penceresi çizilmez**: ilk N bar (SMA-n için n-1, EMA için seed, RSI-14 için 14) `null` döner
  ve arayüz "ısınıyor" gösterir — sahte değer üretilmez.
- Referans doğrulama: TA-Lib **kurulu konteynerde salt-okunur** `docker exec … python -c` ile üretilir
  (korunan `main.py`'ye dokunulmaz); referans değerler teste **sabit** olarak gömülür.

---

## ADR-4 — Zaman dilimi: günlük yerli, haftalık/aylık TÜRETİLMİŞ, gün içi İMKÂNSIZ

**Bağlam.** "Çok zaman dilimli" isteniyor ama ölçüm gösterdi ki yukarı akışta **yalnızca günlük** veri var
(`/price/{ticker}`'ın tek parametresi `limit`; zaman dilimi parametresi YOK).

**Karar.** Günlük = yerli; haftalık/aylık = **istemcide resample**, arayüzde **"türetildi"** rozeti;
dakika/saat dilimleri **butonları devre dışı + neden etiketi** ("gün içi veri kaynağı yok").

**Sonuçlar.**
- Resample kuralı: hafta = ISO haftası, ay = takvim ayı; `open`=ilk, `high`=maks, `low`=min, `close`=son,
  `volume`=toplam. **Eksik gün enterpole EDİLMEZ** (Y3) — yalnızca var olan barlar toplanır.
- Yarım/eksik son kova ("bu hafta henüz bitmedi") **açıkça işaretlenir**, tam kova gibi sunulmaz.
- `/price` proxy'sine `limit` iletimi eklenecek (şu an iletilmiyor → grafik 60 barla sınırlı,
  olay marker'ları pencere dışına düşüyor).

---

## RİSK KAYDI

| # | Risk | Olasılık | Etki | Azaltma |
|---|---|---|---|---|
| R1 | Test glob'unun sessiz boşluğu: `tests/x.test.ts` hiç çalışmaz, hata da vermez | **Yüksek** | Testler "yeşil" görünürken hiç koşmamış olur | Tüm yeni testler `tests/grafik/*.test.ts` altına; FAZ 5'te "test dosyası sayısı arttı mı" kontrolü |
| R2 | `takeScreenshot()` varsayılanı primitives'i dışlar | Yüksek | PNG'de çizimler yok → yanlış hata avı | `takeScreenshot(true)` + bir test bunu kilitler |
| R3 | Bundle bütçesi biriminin belirsizliği (V-009: gzip mi ham mı) | Orta | "≤60KB gzip" iddiası doğrulanamaz | Ölçüm ham CLI rakamıyla raporlanır, birim belirsizliği açıkça yazılır (Y11) |
| R4 | `limit` iletilmediği için olay marker'ları mum penceresi dışına düşüyor | Orta | Sessizce kaybolan marker | S1'de `limit` parametrelendirilir; pencere dışı marker sayısı raporlanır |
| R5 | Paralel oturumların frontend dağıtımı çakışabilir | Orta | Birinin imajı diğerinin işini geri alır | FAZ 6: komşuya bildirim + temiz kaynaktan (`origin/main` worktree) build, ana dizinde build YOK (T3) |
| R6 | Kapsam gerçekçi değil (8 dilim + 7 araç + 6 gösterge tek oturumda) | **Yüksek** | Yarım iş "bitti" diye sunulur | Öncelik sırası + FAZ 8'de bitmeyenler açıkça YAPILMADI olarak raporlanır (Y12/Y15) |
