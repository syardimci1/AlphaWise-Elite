# Çok Kullanıcılı Ölçekleme — Tasarım Notu

**Madde 54** — *Çok kullanıcılı ölçekleme (YALNIZCA TASARIM NOTU)*
**Tarih:** 10 Eylül 2026

> Bu madde iş listesinde **yalnızca tasarım notu** olarak işaretlenmişti.
> Hiçbir kod yazılmadı, hiçbir şema değiştirilmedi. Aşağıdaki her tespit
> çalışan sistemden ölçülmüştür.

## 1. Mevcut durum: kimlik doğrulanıyor, veri bölünmüyor

| katman | durum |
|---|---|
| Kimlik doğrulama | **var** — Supabase, `frontend/src/middleware.ts`, `supabase.auth.getUser()` |
| `decision_log` tablosu | kullanıcı sütunu **YOK** (`id, ticker, decision, total_score, layer_scores, price_at_decision, decided_at, price_after, pct_change, was_correct, evaluated_at, source`) |
| Kâğıt defter `karar` / `islem` | kullanıcı sütunu **YOK** |
| Redis anahtarları | kullanıcı bileşeni **YOK** (`finra:dp:rows:MSFT`, `insider:form4:AAPL`, `gex:quota:FLASHALPHA_API_KEY_1`, …) |

Yani sistem **kimlik doğrulayan ama tek kiracılı** bir üründür. Bugün iki
kullanıcı giriş yapsa **aynı portföyü, aynı kararları ve aynı kâğıt
defteri** görür.

Bu bir hata değil — ürün bugün tek bir hesabı hedefliyor. Ama çok
kullanıcıya geçiş, aşağıdaki dört sorunun **ayrı ayrı** yanıtlanmasını
gerektirir.

## 2. Neyin bölünmesi gerekir, neyin gerekmez

Bu ayrım tasarımın en önemli parçası: **her şeyi kullanıcıya bölmek
maliyetli ve gereksizdir.**

### Bölünmemesi gereken (kullanıcıdan bağımsız)

MSFT'nin dünkü kapanışı, FINRA'nın borsa dışı hacmi, SEC 13F dosyaları,
FRED makro serileri, opsiyon zinciri — bunlar **kime sorulduğundan
bağımsızdır**. Kullanıcı başına kopyalamak hem depolamayı hem de dış API
kotasını kullanıcı sayısıyla çarpardı.

Ölçülen kanıt: Redis'teki `finra:dp:rows:MSFT`, `insider:form4:AAPL`,
`sec13f:kurum:1006249` anahtarlarının hiçbiri kullanıcıya bağlı değil ve
**bağlı olmamalı**.

### Bölünmesi gereken (kullanıcıya özgü)

- **Portföy ve kâğıt defter** — `karar`, `islem` tabloları. Bugün tek
  defter var; iki kullanıcı aynı pozisyonu paylaşır.
- **İzlenen semboller** — `/veri/izlenen_semboller.json` tek dosya.
- **Bildirimler ve risk kayıtları** — kime ait olduğu belirsiz.
- **Karar geçmişi** — `decision_log`. Burada bir nüans var: kararın
  *kendisi* (MSFT için EKLE) kullanıcıdan bağımsızdır; kullanıcıya özgü
  olan **hangi kullanıcının o kararı istediği ve gördüğü**. Yani tablo
  bölünmemeli, ayrı bir "kim sordu" ilişkisi eklenmelidir. Aksi halde aynı
  karar N kullanıcı için N kez hesaplanır ve N kez LLM kredisi harcanır.

## 3. En kritik sorun: kota muhasebesi

Bu, çok kullanıcılığın en sert kısıtı ve ölçülmüş durumda:

| kaynak | kota | bugünkü muhasebe |
|---|---|---|
| **FlashAlpha** | **25 istek/gün TOPLAM** (5 anahtar × 5) | `gex:quota:<anahtar>:<tarih>` — **kullanıcıdan bağımsız tek sayaç** |
| Alpha Vantage | 25 istek/gün | tek sayaç |
| OpenRouter (LLM) | kredi bazlı | kullanıcı ayrımı yok |
| LLMQuant | kredi bazlı | kullanıcı ayrımı yok |

Günlük 25 FlashAlpha isteği **tüm sistem için** geçerlidir. On kullanıcı
olsa kişi başı 2,5 istek düşer. Dolayısıyla çok kullanıcılıkta üç seçenek
var ve **üçü de ürün kararıdır, teknik değil**:

1. **Havuz** — kota ortak kalır, ilk gelen alır. Basit ama adaletsiz:
   bir kullanıcı günün bütçesini tek başına bitirebilir.
2. **Kullanıcı başına pay** — 25 istek N kullanıcıya bölünür. Adil ama
   N büyüdükçe kullanılamaz hâle gelir.
3. **Paylaşılan önbellekle ihtiyacı azaltmak** — madde 36'da yapılan iş
   tam olarak budur: aynı sembol için ikinci istek artık kota yakmıyor.
   Çok kullanıcılıkta bu **en değerli** yol olur, çünkü kullanıcılar
   büyük ölçüde aynı popüler sembolleri sorar.

> Madde 36'daki önbellek kullanıcıdan bağımsız olduğu için çok
> kullanıcılığa **olduğu gibi** hazırdır; anahtarı sembol ve vadedir,
> kullanıcı değil. Bu bir tesadüf değil, doğru katmanda önbelleklemenin
> sonucudur.

## 4. Maliyet atfı

LLM çağrıları (`maa` kaskadı) kredi harcar ve bugün **kimin harcadığı
kaydedilmiyor**. Çok kullanıcılıkta bu üç şey için gerekir: fatura,
kötüye kullanım tespiti, ve kullanıcı başına sınır. En ucuz yol,
`decision_log`'a "kim istedi" ilişkisi eklemektir — karar tablosunu
bölmeden.

## 5. Eşzamanlılık

Bugün ölçülen tek eşzamanlılık koruması FlashAlpha kota sayacındaki
atomik `INCR`/`DECR`'dir (madde 36'da incelendi). Kâğıt defter SQLite
üzerindedir ve **tek yazar** varsayar; çok kullanıcılı yazma yükünde
SQLite'ın kilitleme davranışı ayrıca ölçülmelidir — varsayılmamalıdır.

## 6. Bu notun sınırı

Burada **hiçbir şey uygulanmadı** ve uygulanmamalıdır: çok kullanıcılık
bir şema kararı, bir fiyatlandırma kararı ve bir kota politikası kararıdır.
Üçü de kullanıcının vereceği kararlardır. Bu notun işi, o kararlar
alınırken hangi tespitlerin **ölçülmüş** olduğunu ortaya koymaktır.

Uygulamaya geçilirse ilk adım en ucuz olanıdır ve tek başına anlamlıdır:
**kâğıt defteri ve izlenen sembolleri kullanıcıya bölmek.** Karar tablosu
ve önbellekler paylaşımlı kalabilir.
