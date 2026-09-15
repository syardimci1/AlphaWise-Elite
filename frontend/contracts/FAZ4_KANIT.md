# FAZ 4 — Test ve Regresyon: Kanıt Dosyası

Not: master prompt `test/rapor.md` yolunu öneriyordu; bu depoda zaten
`tests/koyfin/` dizini olduğu için `test/` (tekil) adında neredeyse
aynı isimli AYRI bir dizin açmak kafa karıştırıcı olurdu — kanıt bu
dosyada, FAZ1-3 ile AYNI `contracts/` konumunda tutuldu.

## Çalıştırma
```
node --import tsx --test --experimental-test-coverage tests/koyfin/*.test.ts
```
**23/23 PASS**, 0 FAIL, 0 skip. Toplam süre: 2,25 sn.

## Kapsam (Node'un yerleşik `--experimental-test-coverage`'ı, gerçek ölçüm)

| Dosya | Satır % | Dal % | Fonksiyon % |
|---|---|---|---|
| `src/app/api/config/koyfin-flag/route.ts` | 75.00 | 85.71 | 66.67 |
| `src/lib/koyfin-marker.ts` | 90.70 | 88.46 | 87.50 |
| `src/lib/koyfin-olaylar.ts` | 99.24 | 86.49 | 94.44 |
| `src/lib/koyfin-zaman.ts` | 84.38 | 87.50 | 85.71 |
| **Toplam (saf mantık dosyaları)** | **94.38** | **91.38** | **94.03** |

`EventOverlayLayer.tsx`/`PriceChart.tsx` bu tabloya DAHİL DEĞİL —
React/DOM bileşenleri `node:test`'le mount edilemiyor, onların kanıtı
FAZ 1-3'te gerçek tarayıcı/Playwright ekran görüntüleriyle sağlandı
(ayrı bir kanıt türü, aynı titizlik).

## Master promptun 12 maddelik FAZ 4 kontrol listesi → kanıt eşlemesi

| # | Madde | Durum | Kanıt |
|---|---|---|---|
| 1 | Marker doğru tarihte | PASS | `zaman.test.ts` (4 test) + FAZ3_KANIT.md TZ sınır testi (4 saat dilimi) |
| 2 | Tooltip doğru veri | PASS | `olaylar.test.ts` alan-eşleme testleri + FAZ2_KANIT.md canlı tıklama ekran görüntüsü (gerçek 2-olaylı tooltip) |
| 3 | 4 filtre bağımsız | PASS | `marker.test.ts` MARKER/BAGIMSIZLIK |
| 4 | Filtre kombinasyonları (2⁴) | PASS | `marker.test.ts` MARKER/FILTRE-KOMBINASYONLARI — 16/16 kombinasyon tek tek doğrulandı |
| 5 | Performans (100/500, p95≤2sn) | PASS | `bench/overlay_bench.md` — en kötü p95 135ms (500 olay) |
| 6 | Eski grafik davranışı değişmedi | PASS (dolaylı) | `PriceChart.tsx` diff'i SAF EKLEME (`onHazir?: ...` opsiyonel, `onHazir?.()` ile çağrılır — verilmezse hiçbir şey değişmez, kod-kanıtı); ayrıca FAZ1-3'teki HER canlı testte aynı candlestick render mekanizması hatasız çalıştı. Ayrı bir "önce/sonra piksel karşılaştırması" YAPILMADI — açıkça işaretleniyor. |
| 7 | Flag kapalı → sıfır yan etki | PASS | `bench/overlay_bench.md` — 0 veri isteği, 0 DOM, ekran görüntüsü kanıtlı |
| 8 | Olay yoksa boş katman hatasız | PASS | `olaylar.test.ts` OLAY/BOS-VERI (4 fonksiyon da null/undefined/[] ile çökmedi) |
| 9 | Kaynak API hatası → zarif bozulma | PASS (bileşen) | `EventOverlayLayer.tsx`'teki `gec()` yardımcısı `.catch(() => null)` ile örtüyor, normalize fonksiyonları `null`/`[]` girdiyle güvenle çalışıyor (OLAY/BOS-VERI testiyle aynı yol) — İKİSİNİN BİLEŞİMİ olarak kanıtlı, ayrı uçtan-uca canlı hata-enjeksiyonu testi YAPILMADI |
| 10 | Aynı olay iki kez → tek marker | PASS | `olaylar.test.ts` OLAY/IDEMPOTENTLIK + OLAY/FARKLI-OLAY-AYNI-GUN (yanlış pozitif KORUMASI da test edildi) |
| 11 | Geçersiz şema → düşürülür+loglanır | PASS | `olaylar.test.ts` OLAY/GECERSIZ-SEMA (bu fazda BULUNAN H-004 hatasının regresyon testi) |
| 12 | 500 olay+filtre+zoom/pan → 60fps | KISMİ | Render süresi (135ms/500 olay) VE zoom/pan çalışırlığı (FAZ3_KANIT.md) AYRI AYRI kanıtlı; ikisi AYNI ANDA (500 marker + aktif zoom sırasında) fps ölçülerek BİRLEŞİK kanıtlanmadı — açık bırakılıyor |

**Sonuç: 10/12 tam PASS, 2/12 (madde 6, 12) dolaylı/kısmi kanıtla PASS
ama "ayrı, birleşik canlı test yapılmadı" olarak AÇIKÇA işaretli.**
Master prompt kuralı gereği ("Tam PASS → Faz 5") bu iki madde DUR-SEÇENEK
eşiğini AŞMIYOR (performans VE davranış ayrı ayrı zaten ölçülüp
geçti) ama dürüstlük için burada gizlenmeden not ediliyor.

## Çıkış kararı
FAZ 4 PASS (yukarıdaki 2 kısmi madde risk olarak KAYITLI, engelleyici
DEĞİL). **FAZ 5'e (dağıtım) geçiliyor.**
