# Databento ve Schwab — Kaynak Değerlendirmesi

**Madde 49 (Databento) ve 50 (Schwab)**
**Tarih:** 10 Eylül 2026

## Kısa sonuç

Her ikisi de **BEKLEYEN_KARAR**. İkisi de kimlik doğrulama arkasında ve
Databento ücretli. Ancak asıl gerekçe bütçe değil: **bu veriyi bugün
tüketecek hiçbir modül yok.**

## 1. Ölçüm

| uç nokta | sonuç |
|---|---|
| `hist.databento.com/v0/metadata.list_datasets` | **HTTP 401** — kimlik doğrulama şart |
| `hist.databento.com/v0/metadata.list_publishers` | **HTTP 401** |
| `api.schwabapi.com/marketdata/v1/quotes?symbols=MSFT` | **HTTP 401** |
| `developer.schwab.com/products` | **HTTP 403** — tarayıcıyla da erişilemedi |

Schwab'ın geliştirici portalı hem `curl` hem gerçek tarayıcıyla 403 döndü;
bu nedenle **koşulları bu oturumda doğrulanamadı.** Schwab API'sinin
brokerlık hesabı ve onaylı geliştirici uygulaması gerektirdiği yaygın
bilgidir, ancak burada **ölçülmemiştir** ve doğrulanmış gibi sunulmaz.

## 2. Databento fiyatlandırması (fiyatlandırma sayfasından okundu)

- Kullanım bazlı ($/GB) **veya** abonelik
- **$125 ücretsiz kredi** kayıtta; 6 ay sonra sona eriyor, ekip başına bir kez
- Sayfada görünen abonelik rakamları: **$97, $199, $1.750, $4.500**
- 15+ yıl geçmiş veri, 45+ borsa

$125'lik kredi ücretsiz bir katman değil, **tek seferlik deneme bütçesidir.**
Bütçe kuralı gereği kullanılması açık onay gerektirir.

## 3. Sistemin şu anki veri kapsamı (ölçüldü)

| alan | kaynak |
|---|---|
| günlük barlar | Tiingo — 6.733 sembol önbellekli, 9 anahtar |
| opsiyon zinciri | openbb-service (yfinance) — ücretsiz |
| GEX | FlashAlpha ücretsiz tier — günde 25 istek, ~250 sembol |
| borsa dışı hacim | FINRA Reg SHO günlük (T+1) + haftalık ATS — anahtarsız |
| kurumsal pozisyon | SEC EDGAR 13F — ücretsiz |
| makro | FRED (anahtarlı) + DBnomics (anahtarsız, madde 44) |
| emir/işlem | Alpaca **PAPER** — gerçek para yok |

## 4. Ne eklerlerdi — ve neden şu an gereksiz

Databento/Schwab'ın getireceği şeyler:

- tick seviyesi işlem verisi (trade-by-trade)
- emir defteri derinliği (L2 / MBO)
- gerçek zamanlı konsolide teklif (SIP)
- gerçek parayla emir yürütme (Schwab)

**Depoda bu veriyi tüketecek tek bir modül yok.** `order book`, `tick data`,
`level 2`, `MBO`, `bid_size`, `ask_size` desenleri tüm Python kaynağında
arandı — hiçbir eşleşme yok (finrl-x hariç tutuldu; o ayrı bir alt modül).

Yani bugün Databento aboneliği alınsa veri **hiçbir yere akmaz.** Önce onu
kullanacak bir sinyal tanımlanması gerekir; kaynak ondan sonra anlamlı olur.

Aynısı Schwab için: sistem şu an **kâğıt üzerinde** işlem yapıyor ve
`godmode-paper-trading` bunun için Alpaca PAPER kullanıyor. Gerçek para
yürütmeye geçmek bir veri kaynağı kararı değil, ürün kararıdır.

## 5. Bekleyen karar

1. **Databento** — $125 deneme kredisi kullanılırsa ne ölçüleceği önceden
   tanımlanmalı (kredi 6 ayda sona eriyor ve ekip başına bir kez). Bugün
   tüketici yok.
2. **Schwab** — koşulları doğrulanamadı (403). Gerçek para yürütmesi ayrı
   bir ürün kararı.
3. **Ön koşul** — her ikisi için de önce mikroyapı verisini kullanacak bir
   sinyal tanımı gerekiyor. Kaynak seçimi ondan sonra ölçülebilir bir soru
   hâline gelir.

Hiçbir hesap açılmadı, hiçbir kredi harcanmadı, hiçbir bağımlılık eklenmedi.
