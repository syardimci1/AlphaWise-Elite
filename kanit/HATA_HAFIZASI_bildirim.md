# HATA_HAFIZASI — Bildirim Merkezi denetimi

## Hata #1: Test sayısı iddiası ilk seferde ters karıştırıldı
- **Alt-Görev:** FAZ 5 (test özeti)
- **Tarih:** 2026-09-26
- **Belirti:** `npm test` çıktısının iki alt-komut özetini (`.mjs` ve `.ts`)
  sırayla yanlış eşleştirdim; ilk yazdığım FAZ 5 taslağı ".mjs=369, .ts=127"
  dedi, gerçekte tam tersi (".mjs=130, .ts=369").
- **Kök neden (5 Whys):**
  1. Neden yanlış yazıldı? → İki ayrı `node --test` çıktısını tek `tail -80`
     ile birlikte okudum, hangi blok hangi komuta ait ayrımı gözle yaptım.
  2. Neden gözle ayrım hataya açık? → `node --test` özet formatı
     (`1..N / # tests N`) komut adını YAZMIYOR, yalnızca sayı veriyor.
  3. Neden bu fark edilmedi? → İlk kontrolü tek birleşik `npm test` çıktısı
     üzerinden yaptım, ayrı ayrı doğrulamadım.
  4. Neden ayrı doğrulama atlandı? → Zaman baskısı altında "ikisi de yeşil"
     yeterli görüldü, hangi sayının hangi dosyaya ait olduğu ayrıca
     önemsenmedi.
  5. Kök → Kanıt toplarken "test geçti mi" ile "iddia edilen sayı doğru mu"
     ayrı doğrulama gerektiren iki farklı önermedir; ilki kontrol edildi,
     ikincisi edilmedi.
- **Düzeltme:** `kanit/faz5_test.md` — iki komut AYRI AYRI çalıştırılıp
  (`node --test tests/*.test.mjs` ve `node --import tsx --test
  tests/*/*.test.ts`), sonuç 3 kez tekrarlanarak (flaky olmadığı da
  doğrulanarak) düzeltildi: `.mjs`=130 (taban 114+16 yeni), `.ts`=369
  (değişmedi).
- **Tur:** 1
- **Tekrar:** 1
- **Ders:** Birleşik `&&` ile zincirlenmiş iki test komutunun çıktısını TEK
  `tail` ile okurken hangi özet bloğunun hangi komuta ait olduğunu ASLA
  gözle tahmin etme — komutları ayrı ayrı çalıştırıp her birinin çıktısını
  kendi bağlamında oku (Y7: kanıtsız iddia yasak, "muhtemelen bu" bir kanıt
  değildir).
- **Önlem:** Bundan sonra çok komutlu test zincirlerinde sayısal iddia
  yazmadan önce ilgili komutu TEK BAŞINA çalıştırıp çıktısını doğrudan
  eşleştirme.

## Hata #2: `kanit/faz0_on_ucus.md` başka bir görevin kanıt dosyasının üzerine yazıldı
- **Alt-Görev:** FAZ 0
- **Tarih:** 2026-09-26
- **Belirti:** `Write` ile `kanit/faz0_on_ucus.md` oluşturuldu; `git status`
  bunu `M` (yeni değil, DEĞİŞTİRİLMİŞ) olarak gösterdi — depoda bu isimde
  ZATEN commit'lenmiş, TAMAMEN alakasız bir dosya vardı (`d9c279d`,
  "coklu kullanici izolasyonu" görevinin FAZ 0 kanıtı).
- **Kök neden (5 Whys):**
  1. Neden üzerine yazıldı? → Spec'in önerdiği genel dosya adını
     (`kanit/faz0_on_ucus.md`) sorgusuzca kullandım.
  2. Neden çakışma kontrol edilmedi? → FAZ 0.3'te YALNIZCA `git status`
     çalıştırıldı (kirli ağaç kontrolü), hedef dosya adının kendisinin
     ÖNCEDEN commit'lenmiş olup olmadığı kontrol edilmedi.
  3. Neden bu önemli? → Bu depoda `kanit/` dizini TEK bir görev için değil,
     BİRDEN FAZLA farklı görev için ortak kullanılıyor (R1_R7_R13,
     çoklu-kullanıcı-izolasyonu, R-15, şimdi bildirim) ve hepsi aynı
     jenerik `fazN_*.md` adlandırma kuralını izliyor — isim çakışması
     riski YÜKSEK.
  4. Neden fark edildi? → FAZ 6 kapanışında `git status --porcelain`
     çıktısında `M kanit/faz0_on_ucus.md` (yeni değil, değişmiş) görülünce
     şüphelenildi, `git log -- <dosya>` ile doğrulandı.
  5. Kök → Ortak bir dizinde jenerik dosya adı kullanmadan önce o TAM
     yolun daha önce commit'lenip commit'lenmediği kontrol edilmedi.
- **Düzeltme:** İçerik `kanit/faz0_on_ucus_bildirim.md`'ye taşındı,
  `git checkout -- kanit/faz0_on_ucus.md` ile orijinal içerik geri
  getirildi (kayıp YOK, `git diff` ile doğrulandı — orijinal metin
  birebir geri geldi). Bu dosyaya çapraz referans veren tek yer
  (`ozelestiri_bildirim.md`) düzeltildi.
- **Tur:** 1
- **Tekrar:** 1
- **Ders:** Ortak `kanit/`/`contracts/` gibi dizinlerde jenerik isim
  (`fazN_*.md`, `*_SONUC.md`) kullanmadan ÖNCE `git log --oneline -- <yol>`
  ile o TAM yolun başka bir göreve ait olup olmadığı kontrol edilir; bu
  depoda böyle dizinler tek-görevlik değil, ortak havuzdur.
- **Önlem:** Bu görevde tüm yeni `kanit/*.md` dosyaları görev-özel sonek
  (`_bildirim`) ile adlandırıldı ve commit öncesi TAMAMI için
  `git log --oneline -- <her dosya>` ile "yeni" olduğu teyit edildi.

## Hata #3 (bulunmadı, aranmadı olarak işaretlenmedi — Y19 notu)
FAZ 3 uygulaması (okundu/okunmadı, polling, a11y) ilk yazımda testler
sıfırdan doğru geçti (13/13, sonra 16/16) — TDD disiplini (Y6: önce test)
sayesinde "gerçek" bir kod hatası turu (DENEY→ÖLÇ→KÖK NEDEN→KOD→TEST
döngüsü) bu görevde tetiklenmedi. Bu, döngünün gereksiz olduğu anlamına
gelmez; sadece bu spesifik uygulamada rastlanmadığını dürüstçe belirtir.
