# FlashAlpha Ücretsiz Tier — Değerlendirme

**Madde 36** — *FlashAlpha GEX/DEX ücretsiz API değerlendirmesi*
**Tarih:** 10 Eylül 2026

## Kısa sonuç

FlashAlpha ücretsiz tier **kullanılabilir durumda ve yerinde duruyor** — ama
günlük bütçesi düşünüldüğünden çok daha dar ve iki yerden sızıyordu. İkisi de
düzeltildi.

| ölçü | değer |
|---|---|
| tanımlı anahtar | 5 |
| anahtar başına günlük hak | 5 |
| **günlük toplam istek hakkı** | **25** |
| kapsanan sembol evreni | **~250 sembol** (ölçüldü, aşağıda) |
| veri gecikmesi | ~15 dakika |
| DEX/Vanna maliyeti | **0** — kendi hesabımız, FlashAlpha kotası tüketmiyor |

## 1. Mimari zaten doğruydu

Değerlendirmenin ilk bulgusu olumlu: **DEX ve Vanna FlashAlpha'dan
alınmıyor.** `/dex-vanna` ucu opsiyon zincirini ücretsiz `openbb-service`'ten
çekip Black–Scholes türevlerini kendi içinde hesaplıyor, 15 dakika
önbelleklıyor ve `flashalpha_kotasi_tuketildi: false` alanıyla bunu açıkça
bildiriyor. Yani günlük 25 hakkın tamamı yalnızca GEX'e ayrılmış durumda.

Çok anahtarlı rotasyon, atomik Redis sayaçları, kota dolunca sessiz hata
yerine açık `429 + istek_yapilmadi: true` — bunlar da yerindeydi.

## 2. Bulgu 1: `/gex` sonucu hiç önbelleklenmiyordu

Kardeş uç `/dex-vanna` 15 dakikalık önbellek kullanırken, asıl **sınırlı
kaynağı harcayan** `/gex` ucu sonucu hiç saklamıyordu. Aynı sembol için arka
arkaya iki istek 25 hakkın ikisini birden yakıyordu; paneli bir kez yenilemek
günlük bütçenin %8'ini harcıyordu.

**Düzeltme.** 15 dakikalık sonuç önbelleği eklendi. Üç ayrıntı önemli:

- **Önbellek kota ayrılmadan önce okunur.** Sonra okunsaydı hiçbir tasarruf
  sağlamazdı; hak zaten ayrılmış olurdu. `M9` mutasyonu tam olarak bu sırayı
  sınar: önbellek okuması kotadan sonraya alınınca test kırılıyor.
- **Önbellek kota kontrolünü atlatmaz.** Kota dolu olsa bile önbellekteki
  geçerli yanıt sunulur (istek yapılmadığı için hak tüketilmez), ama boş
  önbellekte 429 yine döner.
- **Tazelik gizlenmez.** Kaynak zaten ~15 dk gecikmeli; üstüne 15 dk önbellek
  konunca veri en kötü ~30 dk eski olabilir. Her önbellek isabetinde yanıt,
  verinin kaç saniye önce alındığını ve toplam olası gecikmeyi taşır. Kota
  durumu saklanmaz, her yanıtta canlı okunur — saklanan hak dakikalar içinde
  yanlışlaşırdı.

Yalnızca başarılı yanıt önbelleklenir; geçici bir 502'yi 15 dakika boyunca
tekrar sunmak arızayı kalıcı hale getirirdi.

## 3. Bulgu 2: ücretsiz plan yalnızca ~250 sembol kapsıyor

Bu, birinci düzeltmeyi **canlı doğrularken kazara** bulundu. `/gex/ZZTEST`
isteğine FlashAlpha şu yanıtı verdi:

```json
{"status":"ERROR","error":"symbol_not_in_free_universe",
 "message":"The Free plan only covers ~250 tracked symbols. ZZTEST isn't one
            of them. Upgrade to Basic or higher for on-demand access to any
            US-listed symbol.",
 "current_plan":"Free","required_plan":"Basic"}
```

Bu, değerlendirmenin en önemli bulgusudur ve daha önce hiçbir yerde kayıtlı
değildi: **ücretsiz tier rastgele bir ABD sembolünü vermiyor.** Sistem
kapsam dışı bir sembol sorduğunda bunu *öğrenmek bile* günlük 25 hakkın
birini yakıyordu — ve bu bilgi saklanmadığı için aynı sembol her
sorulduğunda yeniden yakıyordu.

**Düzeltme.** Yalnızca `symbol_not_in_free_universe` kodu gün sonuna kadar
olumsuz önbelleğe yazılır. Genel hataları önbelleklemek yanlıştır (geçici
arızayı kalıcı yapar), ama bu hata geçici değil: planın kapsadığı sembol
kümesi dakikalar içinde değişmez. TTL gün sonuna (kota sıfırlanmasıyla aynı
ana) bağlandığı için, kullanıcı planı yükseltirse olumsuz kayıt bir
yükseltmeyi kalıcı olarak gizlemez.

Diğer tier hataları (`tier_restricted`, genel `upgrade`/`plan` mesajları)
saklanmaz — `test_gecici_tier_hatasi_kalici_saklanmaz` bunu kilitler.

Mevcut bir doğru davranış da testle kilitlendi: plan kısıtlamasında diğer
anahtarlara **rotasyon yapılmıyor**. Yapılsaydı tek bir kapsam dışı sembol
5 hakkı birden yakardı.

## 4. Bulgu 3: kota sayılamayınca sınırlı kaynak yine de harcanıyordu

Redis düşükse `_tek_anahtar_kota_ayir` içindeki `incr` yakalanmıyordu; uç
nokta çıplak bir `RuntimeError` ile 500 veriyor ve nedeni yanıttan
anlaşılmıyordu. Daha önemlisi: **"sayamadık" ile "hakkın var" aynı şey
değil.** Sayılamayan bir kotayı harcamak, günlük bütçenin muhasebesiz
tükenmesi demektir. Artık kota sayacı okunamazsa istek yapılmaz, açık bir
503 döner.

## 5. Şüphecilik turu

13 mutasyon uygulandı, **13'ü de yakalandı; hayatta kalan yok.**

| # | mutasyon | sonuç |
|---|---|---|
| M1 | önbellek anahtarı vadeyi yok saysın | YAKALANDI |
| M2 | önbellekten saklanan (bayat) kotayı döndür | YAKALANDI* |
| M3 | önbellek yaşını gizle, veriyi taze göster | YAKALANDI |
| M4 | azami gecikmeyi aşağı yuvarla | YAKALANDI |
| M5 | kota durumunu da önbelleğe yaz | YAKALANDI |
| M6 | önbellek okumasını kaldır | YAKALANDI |
| M7 | önbelleğe yazmayı kaldır | YAKALANDI |
| M8 | kota-sayılamadı korumasını kaldır | YAKALANDI |
| M9 | **önbellek okumasını kotadan sonraya al** | YAKALANDI |
| M10 | her plan hatasını kapsam dışı say | YAKALANDI |
| M11 | kapsam dışı anahtarı sembolü yok saysın | YAKALANDI |
| M12 | kapsam dışı kaydını hiç yazma | YAKALANDI |
| M13 | kapsam dışı kaydını hiç okuma | YAKALANDI |

\* M2 ilk turda **hayatta kalmıştı**: testim `isabet_yaniti`'na zaten kotası
ayıklanmış bir gövde veriyordu, yani mutasyonu göremiyordu. Savunmayı
bağımsız sınayan bir test eklendikten sonra yakalandı.

## 6. Canlı doğrulama — kota harcamadan

Her iki önbellek yolu çalışan serviste, gerçek Redis üzerinden doğrulandı;
kayıt önceden yerleştirilerek FlashAlpha'ya hiç istek gitmedi:

```
sonuç önbelleği    : onbellekten=True, yaş=300 sn, kota 1 -> 1 (değişmedi)
kapsam dışı kaydı  : istek_yapilmadi=True, kota 1 -> 1 (değişmedi)
```

## 7. Dürüstlük notu — harcanan 1 hak

Birinci düzeltmeyi canlı doğrularken **günlük 25 hakkın 1'i boşa harcandı.**
Nedeni benim hatam: sahte önbellek kaydını `redis-cli`'a kimlik doğrulaması
vermeden yazdım, `SETEX` `NOAUTH` ile reddedildi, ben de stderr'i
bastırdığım için bunu görmedim. Önbellek boş kaldı, istek FlashAlpha'ya
gitti. Hak gece yarısı UTC'de sıfırlanıyor. Aynı kaza, Bulgu 2'nin
bulunmasını sağladı — ama bu, harcamayı planlanmış göstermez.

## 8. Bekleyen karar

**Sembol evreni.** Ücretsiz plan ~250 sembolle sınırlı. Sistemin izlediği
semboller bu evrenin dışına çıkıyorsa GEX o semboller için hiçbir zaman
üretilemez. Hangi sembollerin kapsandığını öğrenmek de hak harcar (sembol
başına 1 istek). Evrenin çıkarılması ya da Basic plana geçilmesi **kullanıcı
kararıdır** — ikisi de bütçe kuralı kapsamındadır ve onaysız yapılmadı.

## 9. Üretilen dosyalar

- `gamma-exposure-service/gex_onbellek.py` — sonuç ve kapsam dışı önbellek mantığı
- `gamma-exposure-service/main.py` — üç düzeltme bağlandı
- `gamma-exposure-service/test_gex_onbellek.py` — 34 test
- `gamma-exposure-service/Dockerfile` — yeni modül COPY listesine eklendi
