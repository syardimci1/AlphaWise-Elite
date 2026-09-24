# HATA HAFIZASI — grafik terminali

Yalnızca ekleme yapılır; mevcut girdiler silinmez.

## H-1 — kullanıcı değişiminde çizimlerin başka ad alanına yazılması (24.09.2026, kalıcılık işi)

- **Belirti:** aynı sembolde kullanıcı kimliği A→B değişince, A'nın çizimleri bir kez `…:cizim:v1:kullanici-B:AAPL` anahtarına yazılıyor.
  Hemen sonraki render B'nin (boş) listesini yazdığı için SON depo durumu temiz görünüyor → yalnızca son durumu kontrol eden test bunu kaçırıyor.
- **Ölçüm:** `kanit/kalicilik/e2e/kos.mjs` E5, `Storage.prototype.setItem` kaydıyla: düzeltmeden önce `KALDI … gelen ["alphawise:grafik:cizim:v1:kullanici-B:AAPL"]`, sonra `GEÇTİ`.
- **5 Neden:** (1) B anahtarına A verisi yazıldı ← (2) kaydetme efekti eski `cizimDurum` ile çalıştı ← (3) React, yükleme efektinin
  `cizimGonder(YUKLE)` güncellemesini aynı commit'teki sonraki efekte göstermez ← (4) kaydetme kapısı "yükleme bitti mi" sorusunu
  yalnızca **sembol** üzerinden soruyordu ← (5) kapı tasarlanırken kimlik değişimi senaryosu (prop ile) düşünülmemişti; bugünkü
  tek çağıran kimlik prop'u geçmediği için görünmüyordu.
- **Düzeltme:** kapı `yuklenenCizimAnahtari === anahtarUret(etkinKimlik, symbol)` — ad alanının tamamı. Gösterge kaydı baştan aynı kapıyla yazıldı.
- **Ders:** kalıcılık testinde son durum yetmez; yazım günlüğü (her `setItem`) denetlenmeli.

## H-5 — debounce, yüklenen verinin "yankı" yazımını tehlikeli hale getirdi (24.09.2026, S5)

- **Belirti:** debounce eklenince E11 (`1001` beklenirken `1` çizim) ve E7 (yer açıldıktan sonra kalıcı kota uyarısı) kırmızıya döndü.
- **Kök neden:** kaydetme efekti yükleme sonrası da çalışıp **az önce okunan veriyi geri yazıyordu**. Senkron yazımda bu zararsızdı
  (aynı an). Debounce ile yazım 300 ms gecikti: o arada başka bir yerden (başka sekme; düzenekte `/bos` sayfası) yazılan daha yeni
  kayıt, eski veriyle **ezildi**; E7'de ise gecikmiş yankı, kota dolduktan sonra çalışıp gerçek olmayan bir "çizim yazılamadı" uyarısı bıraktı.
- **5 Neden:** (1) yeni kayıt ezildi ← (2) gecikmiş yazım eski veriyi taşıdı ← (3) yüklenen veri kaydetme efektini tetikliyor ←
  (4) efekt "değişti mi" değil "render oldu mu" sorusuna bakıyor ← (5) "depoda ne var" bilgisi hiçbir yerde tutulmuyordu.
- **Düzeltme:** `depodakiRef` — anahtar başına depoda olduğu bilinen içerik (JSON). Yüklenen içerik oraya yazılır; kaydetme efekti
  içerik aynıysa planlamaz. Yan kazanım: sıfırlama sonrası silinen anahtar yeniden yaratılmaz.
- **Ders:** gecikme eklemek, "zararsız" gereksiz yazımları yarış durumuna çevirir; debounce'tan önce gereksiz yazımlar ayıklanmalı.

## H-4 — yinelenen çizim kimliği kaydı bütünüyle yüklenemez kılıyordu (24.09.2026, S5 sırasında okuma)

- **Belirti:** kayıtta aynı `id`'li iki geçerli çizim → `yukle()` ikisini de döndürür → `cizim-model` reducer'ı `YUKLE`'u
  (yinelenen kimlik = geçersiz liste, `cizim-model.ts:154`) reddedip durumu DEĞİŞTİRMEZ → önceki sembolün çizimleri yeni
  sembolde görünür ve yeni sembolün anahtarına yazılır.
- **Kök neden:** iki doğrulama katmanı farklı sözleşmelerle çalışıyordu: `yukle` öğe bazlı, `YUKLE` liste bazlı (benzersizlik dahil).
- **Düzeltme:** `cizimleriAyikla` yinelenen kimlikleri ayıklar (ilk gelen kalır), sayısı uyarıya yazılır. Test: "yukle çıktısı
  reducer YUKLE tarafından HER ZAMAN kabul edilir".
