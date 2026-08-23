# TASARIM — DEX/Vanna kartının dashboard'a eklenmesi (8. Piyasa Sinyali)

> **DURUM: UYGULANDI (23 Ağustos 2026).** Servis tarafı (`/dex-vanna/{ticker}`)
> daha önce yazılmış ve test edilmişti; dashboard bağlantısı, proxy route'u ve
> kartı bu tarihte eklendi.
>
> **Uygulamada tasarımdan sapan tek nokta:** alan adı `en_buyuk_gex_strike`
> değil, servisin gerçekte döndürdüğü `en_buyuk_gex_strike_bayi_isaretli`.
> Tasarım metnindeki kısa ad canlı yanıtla karşılaştırılınca düzeltildi.

## 1. Görevin öncülü neden düzeltildi

Görev metni şöyle diyordu: *"mevcut gamma-exposure-service'in ZATEN sahip olduğu
FlashAlpha opsiyon zinciri verisinden hesaplanabilir — yeni veri kaynağı
GEREKMİYOR."*

Ölçüldü, bu **doğru değildi**:

| İddia | Ölçüm |
|---|---|
| Servis opsiyon zinciri verisine sahip | `grep -rnE 'strike\|open_interest\|delta\|iv'` → **0 eşleşme**. `main.py` FlashAlpha yanıtını hiç ayrıştırmadan `"gex": veri` diye opak geçiriyor. |
| Veri elimizde | `/gex` ücretsiz planda **HTTP 402** dönüyor; üstelik **başarısız çağrı bile kotadan düşüyor** (ölçüldü: 25 → 24). |

**Çözüm:** zincir, zaten kurulu `openbb-service`'ten `yfinance` sağlayıcısıyla
alınır — ücretsiz, anahtarsız ve **FlashAlpha kotasına hiç dokunmaz**
(kanıt: hesap sonrası `/quota` → `0/25`, değişmedi).

## 2. Servis tarafı (HAZIR, test edildi)

`GET /dex-vanna/{ticker}` — `gamma-exposure-service` (8220)

Yanıtın ilgili alanları:

| Alan | Anlamı |
|---|---|
| `spot` | Dayanak fiyatı |
| `kullanilan_kontrat` / `atlanan_kontrat` | Hesaba giren / elenen kontrat sayısı |
| `ham.dex` / `ham.gex` / `ham.vex` | **Varsayımsız** toplamlar (işaret sözleşmesi uygulanmamış) |
| `bayi_varsayimli.*` | Bayi call'da kısa / put'ta uzun varsayımıyla |
| `call_dex` / `put_dex` | Ayrıştırılmış delta maruziyeti |
| `en_buyuk_gex_strike` | En yoğun 5 strike |
| `varsayimlar` | Risksiz faiz, temettü, bayi konumu, birimler |
| `kalibrasyon_gecerli` | **Her zaman `false`** |
| `yon_kodu_uretir` | **Her zaman `false`** |

## 3. Dashboard kartı tasarımı

Mevcut `PiyasaSinyalleri` bileşenine **8. kart** olarak, `SinyalKutusu`
deseniyle. Mevcut 7 karta dokunulmaz.

```
Başlık : "Opsiyon Maruziyeti — DEX / GEX / Vanna"
Rozet  : "hesaplanmış türev — kalibre edilmemiş"   (turuncu, #fbbf24)
Kaynak : openbb-service → yfinance opsiyon zinciri (ücretsiz)
```

Gösterilecek satırlar:

| Etiket | Değer |
|---|---|
| Dayanak fiyatı | `spot` |
| Hesaba giren kontrat | `kullanilan_kontrat` (+ atlanan oranı) |
| Toplam açık pozisyon | `toplam_acik_pozisyon` |
| Delta maruziyeti (bayi varsayımlı) | `bayi_varsayimli.dex` |
| Gamma maruziyeti (%1 spot başına) | `bayi_varsayimli.gex` |
| Vanna maruziyeti (1 puan IV başına) | `bayi_varsayimli.vex` |
| En yoğun GEX strike | `en_buyuk_gex_strike[0]` |

### Zorunlu dürüstlük uyarısı (God Mode standardı)

Kartın `uyari` alanında, gizlenmeden:

> Bu değerler **hesaplanmış türevlerdir**, ölçülmüş bayi konumlanması
> değildir. Bayinin call'da kısa / put'ta uzun olduğu varsayımı sektörde
> yaygındır ama **kamuya açık bir veriyle doğrulanamaz**; bu yüzden
> varsayımsız "ham" değerler de ayrıca döndürülür. Yunanlar (delta, gamma,
> vanna) zincirde bulunmadığı için Black-Scholes ile hesaplanır; risksiz
> faiz ve temettü getirisi varsayımdır ve yanıtta açıkça yazılıdır.
> Bu sinyalin öngörü gücü **bu sistemde kalibre edilmemiştir** ve karar
> koduna (EKLE/TUT/BEKLE/DİKKAT ET) **bağlanmaz**.

### Proxy route

`frontend/src/app/api/dex-vanna/[ticker]/route.ts` — mevcut 7 route ile
birebir aynı desen: `tickerDogrula` + `servisProxy`, adres yalnızca sunucuda
(`GAMMA_EXPOSURE_URL`), zaman aşımı 120 sn (soğuk hesap ölçüldü: ~20-40 sn,
sıcak <1 sn).

Hız sınırlaması: `/api/dex-vanna/*` middleware'de **`sinyal` sınıfına** düşer
(dakikada 30) — ayrı bir düzenleme gerekmez, `sinifBelirle()` `/api/` altındaki
tanımsız yolları zaten `sinyal` sayar.

## 4. Ölçülen performans ve önbellek

| Ölçüt | Değer |
|---|---|
| AAPL zincir | 2.418 kontrat, 20 vade, OI/IV'de %0 NaN |
| Hesaba giren | 2.248 kontrat (170 atlandı: OI=0 veya IV geçersiz) |
| Redis TTL | 900 sn (15 dk) — yfinance zinciri zaten gecikmelidir |
| FlashAlpha kotası | **0 tüketim** (doğrulandı) |

## 5. Uygulanmadan önce cevaplanması gereken

1. Bayi işaret varsayımı kullanıcıya hangi ayrıntıda anlatılmalı? (Öneri:
   varsayılan görünüm `bayi_varsayimli`, "ham değerleri göster" bağlantısıyla
   varsayımsız değerler açılır.)
2. Risksiz faiz sabit %4 varsayılıyor; canlı bir eğriden okunmalı mı?
   (Delta/vanna bu parametreye az duyarlıdır; ölçülmeden değiştirilmemeli.)
3. Kart yalnızca opsiyonu olan hisselerde gösterilmeli — zincir boşsa
   `404` dönüyor; kart bu durumda "bu hisse için opsiyon zinciri yok" demeli.
