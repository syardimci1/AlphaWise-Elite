# Patent ve Lobi Verisi — Kaynak Değerlendirmesi

**Madde 35** — *Senate LDA (lobi bildirimleri) + USPTO (patent) alternatif veri kaynakları*
**Tarih:** 10 Eylül 2026

## Kısa sonuç

Madde iki yarıya ayrıldı ve **yalnızca biri teslim edildi**:

| yarı | durum |
|---|---|
| **USPTO / patent** | ölçüm modülü yazıldı, 47 test geçti — ama kaynak üretim için **güvenilmez** bulundu |
| **Senate LDA / lobi** | **BEKLEYEN_KARAR** — kayıtsız erişilebilir hiçbir yolu kalmamış |

## 1. Ölçüm: hangi kaynaklar hâlâ açık?

Anahtarsız, tek istekle ölçüldü (10.09.2026):

| kaynak | sonuç |
|---|---|
| `api.uspto.gov/api/v1/...` (yeni resmi API) | **HTTP 401** Unauthorized — anahtar şart |
| `api.patentsview.org` (eski PatentsView) | **emekli** — `data.uspto.gov` geçiş kılavuzuna yönlendiriyor |
| `search.patentsview.org` | bağlantı kurulamadı |
| `bulkdata.uspto.gov` (toplu veri) | bağlantı kurulamadı — **emekli** |
| `ops.epo.org` (Avrupa Patent Ofisi) | **HTTP 403** — anahtar şart |
| `worldwide.espacenet.com` | **HTTP 403** |
| `lda.senate.gov/api/v1/...` | **HTTP 403** — `lda.gov`'a taşınmış, Akamai engelliyor |
| `lda.senate.gov/system/public/` (toplu XML) | **HTTP 403** |
| `disclosurespreview.house.gov` | **HTTP 500** |
| `www.opensecrets.org/api/` | anahtar şart (HTML döndü) |
| `patents.google.com/xhr/query` | **HTTP 200, anahtarsız** ← tek açık yol |
| `data.sec.gov/submissions/` | HTTP 200 (kontrol amaçlı; bu madde kapsamında değil) |

Yani her iki resmî kaynak da artık **ücretsiz ama kayıt gerektiren** anahtar
arkasında. Anahtar almak para harcamaz, ancak kullanıcı adına hesap açmayı
gerektirir — bu, bu oturumun yetkisi dışındadır.

## 2. Google Patents: çalıştı, sonra engelledi

Tek açık yol olan `patents.google.com/xhr/query` ilk ölçümlerde beklendiği gibi
çalıştı:

```
q=microsoft                                       -> 136.800 sonuç
q=assignee:"Microsoft Technology Licensing"       ->  34.240 sonuç
  + &after=priority:20240101                      ->     251 sonuç
alanlar: publication_number, title, assignee, filing_date,
         priority_date, grant_date, publication_date, inventor
```

Assignee ve tarih süzgeçleri çalışıyor, yani istenen sinyal teknik olarak
üretilebilir durumda.

**Ancak** yıl yıl sayım almak için art arda 8 sorgu denendiğinde kaynak
**tamamının 8'ine de HTTP 503** döndü ve 15–30 saniyelik yeniden denemeler
bloğu açmadı. Yaklaşık on isteğin ardından erişim kesiliyor.

Bloğun geçici olup olmadığı ayrıca ölçüldü — 4 dakika arayla, **tek** istekle:

```
t+4  dk: HTTP503
t+8  dk: HTTP503
t+12 dk: HTTP503
t+16 dk: HTTP503
```

Yani blok dakikalık bir hız penceresi değil; on kadar istekten sonra en az
**16 dakika** boyunca sürüyor. Bu, günde birkaç yüz sembol taranması gereken
bir sinyal için kullanılabilir bir bütçe değildir.

Bu, kaynağın değerlendirmesini belirler: **belgelenmemiş, hız sınırlı ve
haber vermeden kapanabilen bir uç nokta, üretimde canlı bağımlılık olarak
kullanılamaz.** Bu nedenle modül bilinçli olarak **servis hâline
getirilmemiştir** — Dockerfile ve FastAPI sarmalayıcısı yazılmadı, servis
`docker-compose.yml`'ye eklenmedi, MAA karar yoluna bağlanmadı.

## 3. Yine de yazılan şey: ölçüm modülü (`patent-sinyal/`)

Kaynak güvenilmez olduğu için modülün tasarım ekseni "veriyi almak" değil,
**alamadığında doğru davranmak** oldu.

### 3.1 `kaynak.py` — kaynak hatası asla sıfır olmaz

503, 429, bağlantı hatası, zaman aşımı, HTML hata sayfası, şema değişikliği —
hepsi `OLCULEMEDI` döndürür. `total_num_results = 0` ise bu **gerçek bir
ölçümdür** ve `OLCULDU` olarak döner. İkisi karıştırılmaz.

Bu ayrım teorik değil: yukarıdaki 503 dalgası, "hata → 0 patent" yazan bir
tasarımda Microsoft'u sekiz yıl üst üste **sıfır patentli** gösterirdi.

### 3.2 `eslesme.py` — en tehlikeli sessiz hata

Patent kayıtlarında şirket, borsa koduyla değil patent sahibi adıyla geçer ve
bu ad genellikle işletme adı değildir (`MSFT` → *Microsoft Technology
Licensing, LLC*). Yanlış ad sorgulandığında kaynak **hata vermez, sıfır sonuç
döner**.

Modül bu yüzden adı tahmin etmez: kaynağın **geri döndürdüğü** sahip adlarını
okur, şirket adının ayırt edici belirteçleriyle örtüşenleri işaretler ve
adayları kanıt olarak raporlar. Örtüşen ad yoksa sonuç `OLCULEMEDI`'dir —
"bu şirketin patenti yok" değil. Kısmi eşleşme reddedilir; *Apple Rush
Company* ile *Apple Inc.* aynı şirket sayılmaz.

### 3.3 `momentum.py` — yayın gecikmesi tuzağı

Patent başvurusu, başvurudan ~18 ay **sonra** yayımlanır. Dolayısıyla "son 12
ay" penceresi her şirkette eksik doludur ve son 12 ayı önceki 12 ayla
karşılaştıran bir ölçüm, şirket ne yaparsa yapsın **her zaman düşüş** gösterir.
Bu, veriden gelen bir sinyal değil, yöntemin ürettiği sahte bir sinyaldir.

Çözüm: bugünden geriye 24 aylık dilim tamamen atılır; karşılaştırılan iki
pencere de bu dilimin gerisindedir. Bedeli, sinyalin doğası gereği ~2 yıl
gecikmeli olmasıdır — bu bedel gizlenmez, her çıktıda `veri_bitis_tarihi` ve
`gecikme_notu` olarak bildirilir. Olgunlaşmamış döneme taşan bir pencere
istendiğinde modül sessizce düzeltmez, `OLCULEMEDI` döndürür.

Önceki pencere sıfırsa oran tanımsızdır; bölme yapılmaz.

## 4. Şüphecilik turu — mutasyon testi

| # | mutasyon | sonuç |
|---|---|---|
| M1 | kaynak hatasında 0 patent döndür (503 → sıfır) | YAKALANDI (9 fail) |
| M2 | HTML hata sayfasını sessizce 0 say | YAKALANDI (1 fail) |
| M3 | eşleşme bulunamayınca 0 döndür | YAKALANDI (1 fail) |
| M4 | olgunluk penceresini atla (yayın gecikmesi tuzağı) | YAKALANDI (2 fail) |
| M5 | önceki sıfırken yine de böl | YAKALANDI (2 fail) |
| M6 | kısmi eşleşmeyi kabul et (Apple ~ Apple Rush) | YAKALANDI (1 fail) |

**Hayatta kalan mutasyon yok (0/6).**

## 5. Testler

47 test, hepsi **çevrimdışı**: kaynak sahte bir `acan` (opener) ile taklit
edilir, `--network none` ile izole konteynerde koşar. Böylece testler
Google'ın o anki hız sınırına bağlı değildir. Gerçek uç noktanın verdiği
yanıtlar ayrıca ölçüldü ve yukarıda kayıtlıdır.

## 6. Bekleyen kararlar

1. **Senate LDA (lobi verisi)** — ücretsiz ama kayıt gerektiren API anahtarı
   olmadan hiçbir yolu kalmamış. Toplu XML dizini de 403. Kullanıcı
   `lda.gov` üzerinden ücretsiz anahtar alırsa modül yazılabilir; para
   harcamaz, yalnızca hesap açılmasını gerektirir.
2. **USPTO resmî API anahtarı** — `api.uspto.gov` ücretsiz anahtar veriyor.
   Alınırsa `kaynak.py` sağlam, belgelenmiş ve hız sınırı bilinen bir uç
   noktaya taşınabilir; modülün geri kalanı (eşleşme, momentum, üç durumlu
   ölçüm) olduğu gibi kalır — tasarım kaynaktan bağımsız yazıldı.
3. **Bu sinyalin karar yoluna bağlanması** — mevcut kaynak güvenilmez olduğu
   için MAA'ya bağlanmadı. Anahtar geldikten sonra ayrıca değerlendirilmeli.

## 7. Üretilen dosyalar

- `patent-sinyal/src/kaynak.py` — kaynak istemcisi, üç durumlu ölçüm
- `patent-sinyal/src/eslesme.py` — şirket → patent sahibi doğrulaması
- `patent-sinyal/src/momentum.py` — yayın gecikmesine dayanıklı momentum
- `patent-sinyal/src/olcum.py` — üç durumlu ölçüm sözleşmesi (skor-sentezi ile ortak)
- `patent-sinyal/tests/test_patent_sinyal.py` — 47 test
- `regresyon_calistir.sh` — `patent-sinyal` bağlamı genel python imajına bağlandı
