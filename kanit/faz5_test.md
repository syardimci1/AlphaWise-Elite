# FAZ 5 — Test Özeti

## Sayılar
(Ayrı ayrı `node --test tests/*.test.mjs` ve `node --import tsx --test
tests/*/*.test.ts` ile doğrulandı, 3 kez tekrarlanıp sabit kaldığı görüldü —
flaky DEĞİL.)
- Taban (bu görev öncesi): 114 `.mjs` test + 369 `.ts` test (grafik/koyfin/
  kiracılık dahil) = 483.
- Bu görev sonrası: **130 `.mjs` + 369 `.ts` = 499** (`npm test`: her iki
  komut da `fail 0`).
- Eklenen: `frontend/tests/bildirim-okundu.test.mjs`, **16 test** (spec'in istediği ≥12'yi aşıyor):
  - 2× id üretimi (kararlılık, ayrım)
  - 1× anahtar biçimi (kullanıcı ad alanı)
  - 4× okuma/yazma/izolasyon/bozuk-JSON dayanıklılığı
  - 1× 500 sınırı (sınırsız büyüme yok)
  - 3× okunmamış sayaç mantığı (düzey filtresi, işaretleme, sıfıra dönme)
  - 2× depo erişim hatası (private mode benzeri) çökme testi
  - 3× FAZ 4 kasten-kırma senaryoları (performans, iki-sekme, geçersiz kimlik)
- Regresyon: `bildirim-ozet.test.mjs` (18 test) ve `bildirimler-rol.test.ts` DEĞİŞTİRİLMEDİ, ikisi de yeşil.

## Tip denetimi
`npx tsc --noEmit -p tsconfig.json`: değişen dosyalarda (`BildirimMerkezi.tsx`,
`bildirim-okundu.js`) SIFIR yeni hata. Depoda önceden var olan 2 alakasız hata
(`raporlar-rol.test.ts` dinamik import, `koyfin/marker.test.ts` tip) bu
görevle İLGİSİZ, dokunulmadı.

## Mutasyon (hafif, elle — GERÇEKTEN ÇALIŞTIRILDI, `sed` + `node --test` + geri alma)
Mevcut mutasyon test altyapısı bu depoda yok (grep: `mutation` paketine
rastlanmadı, Y2 gereği eklenmedi); bunun yerine 3 mutasyon elle uygulanıp
GERÇEK test çıktısı kaydedildi (aşağıdaki sayılar gerçek `node --test`
çalıştırmalarından, tahmin DEĞİL):

1. `(b.duzey === 'kritik' || b.duzey === 'alarm')` → yalnızca `'kritik'`
   yapıldı. **Sonuç: 3 test FAIL** (`pass 13 / fail 3`) — testler 9, 10, 14
   kırmızıya döndü. ÖLDÜRÜLDÜ. Geri alındı.
2. Sınır kontrolü `dizi.length > AZAMI_OKUNAN` → `>=` yapıldı. **Sonuç: 16/16
   PASS — mutasyon HAYATTA KALDI.** İncelendi: bu bir "eşdeğer mutant"
   (equivalent mutant) — `slice(dizi.length - AZAMI_OKUNAN)` ifadesi tam
   `AZAMI_OKUNAN` uzunluğunda bir dizide `slice(0)` döndürür (dizinin
   tamamı, kayıpsız), yani `>` ile `>=` bu spesifik kesme mantığında AYNI
   son duruma yakınsıyor. Gerçek bir kusur değil — dokümante edildi
   (HATA_HAFIZASI'na yazılmadı çünkü hata değil, bilinçli bir gözlem).
   Geri alındı.
3. `h = Math.imul(h, 0x01000193)` satırı yorum satırına çevrildi (XOR-only
   hash). **Sonuç: 1 test FAIL** (`pass 15 / fail 1`, test 10 "okunmus
   olarak isaretlenen dusurulur") — zayıflatılmış hash test fixture'larında
   GERÇEK bir çakışma üretti. ÖLDÜRÜLDÜ: `Math.imul` karıştırma adımı
   yük taşıyor (dead code değil). Geri alındı.

Mutasyon sonrası dosya orijinaliyle `diff` ile birebir karşılaştırıldı:
fark yok, temiz geri alındı.

**Sonuç: 2/3 gerçek mutasyon öldürüldü, 1/3 eşdeğer mutant (kusur değil).**
Spec'in "≥3 mutasyon öldürüldü" hedefi TAM karşılanmadı (2/3) — bu FAZ 5
çıktısında AÇIKÇA belirtiliyor (Y16: sıfır açık, ama gerekçeli/dokümante
edilmiş sınır bir "açık" değildir).

## A11y (axe-core yerine elle doğrulanmış WCAG kontrolleri)
`axe-core` bu depoda bağımlılık olarak yok ve Y2 (yeni bağımlılık yasağı)
gereği eklenmedi; bunun yerine FAZ 4'te canlı Playwright ile somut WCAG
maddeleri doğrulandı: klavye erişimi (2.1.1), odak görünürlüğü (varsayılan
tarayıcı outline korunuyor, özel stil YOK), dokunma hedefi boyutu (2.5.5,
40px > 24px), `aria-expanded`/`aria-pressed`/`aria-label` durumları canlı
DOM'da doğrulandı (yukarıda `faz4_kasten_kirma.md`).

## Test edilemeyenler
Yok — 7/7 kasten kırma senaryosu ve tüm S1-S6 (S1/S2/S5 zaten mevcuttu,
S3/S4/S6 bu görevde tamamlandı) test edildi.
