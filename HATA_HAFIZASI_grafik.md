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

## H-7 — "whitespace = boşluk" varsayımı yanlıştı: çizgi serisi eksik günü köprülüyor (25.09.2026, karşılaştırma FAZ 1)

- **Belirti:** eksik gün whitespace (`{ time }`) olarak verildiğinde bile lightweight-charts 5.2.1 çizgi serisi komşu iki
  gerçek noktayı düz çizgiyle birleştiriyor — eksik gün **görsel olarak doğrusal enterpole edilmiş** gibi görünüyor (Y9 ihlali).
- **Ölçüm:** `kanit/karsilastirma/e2e/bosluk_sondasi.mjs` (piksel sayımı): atlanmış ve whitespace kiplerinde eksik gün sütununda
  3 çizgi pikseli; boşluk öncesi son noktanın `color`'u saydam yapılınca 0. Çıktı `kanit/karsilastirma/faz1_bosluk_sondasi_cikti.txt`.
- **5 Neden:** (1) boşluk görünmezdi ← (2) whitespace verisi çizgiyi kesmiyor ← (3) kütüphane whitespace'i yalnızca zaman
  ölçeği noktası olarak kullanıyor, segment çizimini etkilemiyor ← (4) belgelenmiş davranış sanıldı, ölçülmedi ← (5) görsel bir
  sözleşme (C4) yalnızca veri düzeyinde (null) test edilecekti; birim testi bunu asla yakalayamazdı.
- **Düzeltme:** `cizgiVerisi` boşluktan önceki son noktayı `SAYDAM` yapar (ölçülen mekanizma: i. nokta i→i+1 segmentini boyar);
  birim testi (`karsilastirma-cizim.test.ts`) + gerçek bileşende piksel testi (e2e **K5**: eksik gün sütunu 0, pozitif kontrol 5 piksel).
- **Ders:** görsel bir iddia ("boşluk görünür") piksel ölçümüyle kanıtlanır; veri yapısının doğru olması ekranın doğru olduğunu göstermez.

## H-6 — karşılaştırma grafiği kaldırılırken tüm terminal çöküyordu (25.09.2026, karşılaştırma S3)

- **Belirti:** üç sembol eklenince `Error: Value is undefined` → React ağacı çöktü, terminal bölümü tamamen kayboldu (e2e K2/K3/K6/K7/K8/K11/K13/K15 kırmızı).
- **Ölçüm:** TANI kipi (geliştirme paketi + yığın izi): `ensureDefined ← ChartApi.removeSeries ← commitHookPassiveUnmountEffects`.
- **5 Neden:** (1) yok edilmiş grafikte `removeSeries` çağrıldı ← (2) bileşen kaldırılırken React temizlikleri bildirim sırasıyla
  çalıştırır: önce kurulum efektinin `grafik.remove()`'u, sonra seri efektinin temizliği ← (3) seri temizliği grafiğin hâlâ canlı
  olduğunu varsaydı ← (4) bileşen yalnızca yeniden çizimde (seri değişimi) sınanmıştı, kaldırılmada değil ← (5) ikinci sembol
  yüklenirken "yükleniyor" durumu karşılaştırma grafiğini söküp mum grafiğine düşürüyordu — kaldırma, beklenenden çok daha sık bir olaydı.
- **Düzeltme:** seri temizliği `grafikRef.current !== grafik` ise hiçbir şey yapmaz (grafik zaten serileriyle birlikte yok edildi).
  Ek olarak: hazır bir ek sembol varken yeni sembolün yüklenmesi karşılaştırmayı SÖKMEZ (titreme yok), yüklenen sembol notta söylenir.
- **Ders:** grafik kütüphanesi nesnesi paylaşan birden çok efektte temizlik sırası sözleşmenin parçasıdır; kaldırma yolu ayrıca sınanmalı
  (K6 artık mod gidiş-dönüşünü, K8 art arda ekle/çıkar yolunu kapsıyor).
