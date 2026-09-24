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
