# Performans Kanıtı — Koyfin Olay Katmanı (FAZ 2)

Ölçüm yöntemi: gerçek kurulu `lightweight-charts@5.0.0` (standalone
build), Playwright/Chromium, 250 günlük gerçekçi sahte candle serisi
(bugünkü izlenen evrenin bir yıllık işlem günü sayısına yakın). Her N
için 15 tekrar (ilk çağrı `createSeriesMarkers`, sonraki 14'ü
`setMarkers` — filtre değiştirme senaryosunu yansıtır). Süre,
`performance.now()` çağrı ÖNCESİNDEN, **iki art arda
`requestAnimationFrame`** SONRASINA kadar ölçüldü (yalnızca senkron JS
dönüşü değil, tarayıcının fiilen boyama için zamanladığı ana kadarki
süre).

| N (olay sayısı) | p50 (ms) | p95 (ms) | p99 (ms) | Eşik (2000ms) |
|---|---|---|---|---|
| 10  | 34.0 | 87.0  | 87.0*  | GEÇTİ (%4,4'ü) |
| 100 | 39.6 | 56.5  | 56.5*  | GEÇTİ (%2,8'i) |
| 500 | 35.1 | 135.4 | 135.4* | GEÇTİ (%6,8'i) |

`*` 15 örneklemle p95 ve p99 aynı (son) örneğe düşüyor — örneklem
büyüklüğü sınırı, DEZENFORME EDİLMİYOR: gerçek bir istatistiksel ayrım
için ≥100 tekrar gerekirdi ama 500 olayda bile en kötü örnek 135ms
(hedefin %6,8'i), yani ek tekrarın sonucu DEĞİŞTİRMESİ beklenmez.

**Karar Matrisi sonucu:** p95 ≤ 2000ms hedefi 3 boyutta da (10/100/500)
İLK ölçümde geçti — optimizasyon turu (gruplama/sanallaştırma/iptal
edilebilir render) GEREKMEDİ.

## "Kapalıyken gerçekten sıfır maliyet mi?" — CANLI ölçüldü

`KOYFIN_EVENT_OVERLAY_ENABLED=0` ile gerçek bir Next.js dev sunucusunda
(port 3099), gerçek tarayıcıda (Playwright), izole bir test sayfasında
(bkz. FAZ2_KANIT.md) `EventOverlayLayer` gerçek `chart`/`series`
referanslarıyla mount edildi:

- Yakalanan `/api/*` istekleri: **yalnızca 2 kez** `/api/config/koyfin-flag`
  (React geliştirme modunun StrictMode çift-effect'i — üretimde 1 kez
  çalışır). `/api/congress-trading`, `/api/insider-trading`,
  `/api/finra-darkpool-regsho`, `/api/sec-edgar-13f` — **SIFIR istek**.
- `createSeriesMarkers`/`setMarkers` HİÇ çağrılmadı (kod-kanıtı: `if
  (!bayrakAcik) return null` erken çıkışı, useEffect'lerin TAMAMI
  `bayrakAcik`'a bağımlı).
- Ekran görüntüsü: `contracts/kanit/faz2_sifir_maliyet_kaniti.png` —
  yalnızca candlestick grafiği var, filtre kutucukları/marker/tooltip
  YOK.

## Bundle boyutu — GERÇEK `next build` ile 3 durumlu ölçüm

`npm run build` (production, minified) üç ayrı durumda çalıştırıldı;
her seferinde `.next` temizlenip yeniden derlendi (önbellek
kirlenmesini önlemek için). Next.js'in kendi build-özet tablosundaki
`/dashboard` satırı okundu (bu depoda bundle ölçümü için standart,
belgelenmiş yöntem):

| Durum | `/dashboard` kendi boyutu | First Load JS (toplam) |
|---|---|---|
| A) Grafik YOK (`PriceChart`/`EventOverlayLayer` bağlı değil — bu görevden ÖNCEKİ hal) | 18.5 kB | 162 kB |
| B) Yalnızca `PriceChart` bağlı (Koyfin katmanı YOK) | 70.6 kB | 214 kB |
| C) `PriceChart` + `EventOverlayLayer` (bu görevin TAM hali) | 75.4 kB | 219 kB |

**Ayrıştırılmış sonuç:**
- Grafik KÜTÜPHANESİNİN kendisi (`lightweight-charts`, B−A): **+52 kB**
  First Load JS. Bu, bu görevde eklenen bir bağımlılık DEĞİL —
  `package.json`'da zaten vardı (önceki, hiçbir sayfaya bağlı olmayan
  `PriceChart.tsx` taslağından, bkz. FAZ1_KANIT.md) ve yalnızca artık
  GERÇEKTEN bir sayfaya bağlandığı için ilk kez paketleniyor.
- Koyfin olay katmanının KENDİSİ (C−B, `EventOverlayLayer.tsx` +
  3 `koyfin-*.ts` dosyası): **+5 kB** First Load JS.
- Toplam (C−A, "grafiksiz dashboard"a göre): +57 kB.

**Karar Matrisi okuması:** "bundle artışı ≤50KB gzip" eşiği bu GÖREVİN
ÜRETTİĞİ katmana (Koyfin overlay, +5KB) uygulanırsa RAHATÇA GEÇER.
Toplam +57KB'nin +52KB'si, bu görevin başlangıç koşulu olan (FAZ 1'de
tespit edilen) "grafik hiç bağlı değildi" durumunun düzeltilmesinden
geliyor — bu, olay katmanının maliyeti değil, misyonun ön koşulunun
(çalışan bir grafik) maliyetidir ve FAZ 1'de zaten açıkça
belgelenmişti. Şeffaflık için HER İKİ sayı da burada raporlanıyor,
gizlenen yok.

**Yöntem notu / açık nokta:** Next.js CLI tablosundaki rakamların
üretim ölçütü (gzip mi, ham mı) belgede teyit edilmedi; ham bir `.js`
chunk dosyası üzerinde yapılan bağımsız bir gzip kontrolü CLI
rakamlarıyla doğrudan eşleşmedi (muhtemelen paylaşılan/çerçeve
chunk'larının ayrı sayılmasından kaynaklanıyor, kesin açıklama
doğrulanmadı). Bu yüzden yukarıdaki sayılar "Next.js'in resmi build
çıktısı" olarak raporlanıyor, bağımsız gzip doğrulaması YAPILAMADI -
bu açık bırakılmış bir belirsizlik (VARSAYIM_DEFTERI'ne V-009 olarak
eklenmeli).
