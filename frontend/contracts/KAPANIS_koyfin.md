# KAPANIŞ — Koyfin Olay Katmanı (Grafik Olay Katmanı)

## Önce/sonra
- **Önce:** `PriceChart.tsx` hiçbir sayfaya bağlı değildi (canlı
  dashboard'da hiç fiyat grafiği YOKTU). 4 veri kaynağı (13F, dark
  pool, kongre, içeriden işlem) ayrı, ilişkisiz kartlarda gösteriliyordu.
- **Sonra:** Dashboard'da ticker aranınca gerçek bir mum grafiği
  render ediliyor (`contracts/kanit/faz2_sifir_maliyet_kaniti.png`).
  Bir feature flag (`koyfin_event_overlay`, varsayılan KAPALI) açık
  olduğunda aynı grafiğin üzerine 4 kaynağın olayları marker olarak
  biniyor, tıklanınca tüm alanlarıyla (+kaynak linki) açılıyor
  (`contracts/kanit/faz2_tiklama_tooltip_kaniti.png`).

## Performans
| N | p50 | p95 | p99 | Hedef |
|---|---|---|---|---|
| 10 | 34,0ms | 87,0ms | 87,0ms | ✅ |
| 100 | 39,6ms | 56,5ms | 56,5ms | ✅ |
| 500 | 35,1ms | 135,4ms | 135,4ms | ✅ (2000ms hedefinin %6,8'i) |

Bundle: olay katmanının kendisi +5KB First Load JS; grafiğin (önceden
var olan, hiç bağlanmamış `lightweight-charts` bağımlılığının) ilk kez
bağlanması +52KB — ayrıntı ve gerekçe: `bench/overlay_bench.md`.

## Test sonuçları
**23/23 PASS**, 0 FAIL. Kapsam (saf mantık dosyaları):
%94,38 satır / %91,38 dal / %94,03 fonksiyon. Master promptun 12
maddelik FAZ4 kontrol listesi: 10/12 tam, 2/12 dolaylı/kısmi kanıtla
(açıkça işaretli) — ayrıntı: `contracts/FAZ4_KANIT.md`.

## Push/dağıtım durumu
- **Commit'ler (10, hepsi tek mantıksal değişiklik, ayrı ayrı
  `git revert` edilebilir):** `eb24174`(FAZ1 sözleşmeler) →
  `418a763`(C1/C2/C4) → `07888b1`(C3 regsho proxy) →
  `d1a91ee`(C5 flag) → `5550424`(EventOverlayLayer) →
  `4507bb5`(testler+idempotentlik düzeltmesi) →
  `17f7720`(CORS düzeltmesi) → `e5081eb`(dashboard bağlama+bench) →
  `d7511f9`(FAZ3+geçersiz-şema düzeltmesi) →
  `f9fd494`(FAZ4 kanıtı).
- **Dağıtım:** `alphawise-frontend` GERÇEKTEN yeniden inşa edilip
  dağıtıldı (bu oturumda). Ölçülen kesinti: **10,61 saniye** (≤15sn
  sert eşiğinin altında). Konteyner `healthy`, diğer servisler
  dokunulmadı.
- **Gözlem metrikleri:** `KOYFIN_EVENT_OVERLAY_ENABLED=0` canlı
  konteynerde doğrulandı (varsayılan kapalı, doğru dağıtıldı).
  Bölüm 4'ün istediği kalıcı metrik/log/trace ALTYAPISI (Prometheus
  vb.) bu görevde KURULMADI — bu açıkça eksik bırakılan bir madde
  (aşağıda tekrar).
- **Rollback komutu:** yazılı ve YÖNTEM olarak bu oturumda 2 kez
  kanıtlı (build+recreate), ama BU ÖZELLİK için canlı rehearsal
  YAPILMADI (bkz. `contracts/FAZ5_KANIT.md`).
- **Push:** Bu 10 commit HENÜZ origin'e push EDİLMEDİ — bu depodaki
  yerleşik kural gereği (bu oturum boyunca her push ayrı, açık onay
  istendi) push için kullanıcı onayı bekleniyor.

## Kendi bulduğum hatalar (hepsi HATA_HAFIZASI_koyfin.md'de)
- **H-001:** Önceki fizibilite turu dark pool'u "günlük olaya uygun
  değil" diye yanlış işaretlemişti — aynı serviste kullanılmayan
  `/regsho` ucu (günlük) bulunup düzeltildi.
- **H-002:** `PriceChart.tsx` CORS'a takılıp çöküyordu VE belgelenmiş
  güvenlik ilkesini ihliyordu — `/api/market-data` proxy'sine taşındı.
- **H-003:** `next dev`/`next build` ortam tuzağı (tsconfig.json'ı
  sessizce değiştiriyor, ilgisiz boş bir dizin build'i kırıyordu) —
  tespit edilip temizlendi, kod etkisi yok.
- **H-004:** Normalize fonksiyonları tek bozuk kayıtta TÜM kaynağı
  kaybediyordu — `guvenliMap()` ile düzeltildi.

## Açık kalan varsayımlar (VARSAYIM_DEFTERI_koyfin.md, hepsi AÇIK/dip not'lu)
- V-001: dark pool eşiği (+10 puan) gerçek evrende KALİBRE EDİLMEDİ.
- V-003/V-004/V-005: bazı `detay_url`/`confidence` kararları keyfi
  sabitler, kullanıcı geri bildirimiyle değişebilir.
- V-009: Next.js bundle rakamlarının gzip/ham ayrımı bağımsız
  doğrulanamadı.
- **En önemlisi (FAZ5_KANIT.md'de ayrıntılı):** gerçek kimlik
  doğrulamalı bir oturumda 4 kaynağın CANLI uçtan uca akışı bu
  ortamda hiç gözlemlenemedi (yalnızca mock'lanmış `fetch` ile test
  edildi) — bu yüzden özellik %100'e AÇILMADI, flag kapalı bırakıldı.

## Bu görevde YAPILMAYANLAR (dürüstçe)
- Gerçek Prometheus/log/trace altyapısı (Bölüm 4) kurulmadı.
- Rollback canlı rehearsal edilmedi.
- Kaynak-API-hatası → zarif bozulma senaryosu ayrı canlı test edilmedi
  (yalnızca bileşenlerin kompozisyonuyla çıkarsandı).
- 500 olay + tüm filtreler + zoom/pan BİRLEŞİK fps ölçülmedi (ayrı
  ayrı ölçüldü).
- Özellik hiçbir gerçek kullanıcıya AÇILMADI (flag kapalı).

## Tek cümle

Bu katman canlı karar yoluna dokunmuyor çünkü `EventOverlayLayer.tsx`
yalnızca 4 salt-okuma veri ucunu (`congress-trading`, `insider-trading`,
`finra-darkpool-regsho`, `sec-edgar-13f` proxy route'ları) okuyup
`lightweight-charts`'ın resmi görsel eklenti API'sine (`createSeriesMarkers`)
yazıyor — `maa/`, `godmode-paper-trading-service/` veya herhangi bir
sinyal/emir/PnL modülünü import ETMİYOR, hiçbir POST/PUT/DELETE
yapmıyor ve varsayılan olarak (flag kapalı) hiç çalışmıyor bile.

SONRA DUR. Yeni iş icat etme.
