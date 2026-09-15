# FAZ 2 — Uygulama: Kanıt Dosyası

## Bileşenler
- `components/EventOverlayLayer.tsx` — Y4 kod-kanıtı: import listesi
  yalnızca `lightweight-charts` + kendi `koyfin-*` saf fonksiyonları.
- `src/app/dashboard/page.tsx`'e bağlandı: `PiyasaSinyalleri`
  bileşeninin en üstüne, "SEC EDGAR 13F" kartından ÖNCE (ticker
  seçiliyken).

## Kendi bulunan iki hata (Bölüm 3 kendi kendini onaran döngü)
1. **Idempotentlik eksikliği** — `olaylariTekillestir()` eklendi
   (bkz. HATA_HAFIZASI_koyfin.md, test dosyasının commit mesajı).
2. **H-002: PriceChart CORS/güvenlik hatası** — `/api/market-data/
   [ticker]` proxy'si eklendi, `PriceChart.tsx` düzeltildi (bkz.
   HATA_HAFIZASI_koyfin.md H-002).

## Marker tıklama → tooltip (CANLI kanıt)
Gerçek `EventOverlayLayer` bileşeni, gerçek `lightweight-charts`
kütüphanesiyle, gerçek 4-kaynak veri şekilleriyle (mock edilen yalnızca
`fetch` — middleware'in oturum katmanı bu testin konusu değil, ayrı ve
zaten üretimde kanıtlı bir katman) bir tarayıcıda çalıştırıldı:

- `contracts/kanit/faz2_markerlar_canli_kanit.png` — 4 filtre kutucuğu
  + CONGRESS/INSIDER/DARK_POOL+13F(kümelenmiş) marker'ları görünür
  halde.
- `contracts/kanit/faz2_tiklama_tooltip_kaniti.png` — kümelenmiş
  "DARK_POOL +1" marker'ına tıklanınca tooltip AÇILDI ve İKİ olayı da
  (DARK_POOL + 13F) ayrı ayrı, doğru alanlarla gösterdi:
  ```
  DARK_POOL — Kisa hacim orani %55.0 (10g ort. %30.0)
  Olay: 03.09.2026 · Açıklama: 03.09.2026 · güven: 1
  13F — BlackRock, Inc. 2026-06-30 donemi icin $226.560.080.545 pozisyon bildirdi
  Olay: 30.06.2026 · Açıklama: 03.09.2026 · güven: 1
  Kaynağı gör
  ```
  Bu, V-002'nin (marker açıklama tarihinde, tooltip'te HER İKİ tarih)
  ve kümelemenin (tüm üyeler korunuyor, tek olaya indirgenmiyor) canlı
  kanıtıdır.

## "Kapalıyken sıfır maliyet" (CANLI kanıt)
`contracts/kanit/faz2_sifir_maliyet_kaniti.png` + ağ isteği kaydı:
flag kapalıyken yalnızca `/api/config/koyfin-flag` çağrıldı (React dev
StrictMode nedeniyle 2 kez — üretimde 1), 4 veri kaynağına SIFIR istek,
DOM'da filtre/marker/tooltip YOK. Ayrıntı: `bench/overlay_bench.md`.

## Performans
`bench/overlay_bench.md` — 10/100/500 olay, p50/p95/p99, hepsi
2000ms hedefinin ÇOK altında (en kötü 135ms). Optimizasyon turu
gerekmedi.

## Bundle
`bench/overlay_bench.md` — 3 durumlu gerçek `next build` ölçümü.
Olay katmanının KENDİSİ +5KB (First Load JS) — 50KB hedefinin çok
altında. Grafiğin kendisinin (lightweight-charts, önceden var olan
bağımlılık) bağlanması +52KB — bu görevin bir ön koşulu, olay
katmanının maliyeti değil; şeffaflık için ikisi de raporlandı.

## Ortam/araç notu
Bu fazda `next dev`/`next build` çalıştırmaları `tsconfig.json`'ı
sessizce değiştirdi ve ilgisiz boş bir `src/app/login/` dizini build'i
kırdı — ikisi de geri alındı/temizlendi, kalıcı kod etkisi YOK (bkz.
HATA_HAFIZASI_koyfin.md H-003).

## Çıkış kararı
PASS. Y1-Y5 sağlam (kutsal dosyalara dokunulmadı, yeni dış API yok,
her commit tek mantıksal değişiklik, canlı karar yoluna sıfır bağlantı,
kapalıyken sıfır maliyet kanıtlı). **FAZ 3'e (şüphecilik turu) geçiliyor.**
