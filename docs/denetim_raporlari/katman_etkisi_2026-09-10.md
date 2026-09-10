# Katman Etkisi ve Hiyerarşik Süreç Değerlendirmesi

**Madde 42** — *Hiyerarşik süreç*
**Tarih:** 10 Eylül 2026

## Soru

CrewAI gibi çerçevelerde "hiyerarşik süreç" fikri şudur: sabit bir boru hattı
yerine bir **yönetici**, hangi uzmanın çağrılacağına duruma göre karar verir.
AlphaWise'da MAA her karar için beş katmanın hepsini çağırır.

Bu fikri benimsemek gerekli mi? Önce ölçülmesi gereken şey şu: **hangi katman,
çağrılmasaydı kararı değiştirirdi?**

Karar yolu (`maa/src/main.py`) korunmuştur ve **hiç dokunulmamıştır**. Yapılan
iş yalnızca geçmiş kayıtlar üzerinde ölçümdür: her kayıt, bir katman
çıkarılarak yeniden oynatılmıştır (madde 34'te yazılan replay aracıyla).

## 1. Ablasyon ölçümü

102 replay edilebilir kayıt, 21.07 – 09.09.2026:

| katman | ölçüldüğü kayıt | eşik kayması | **oran** | yeter sayı düştü |
|---|---:|---:|---:|---:|
| **faa** | 100 | 69 | **%69,0** | 13 |
| taa | 95 | 23 | %24,2 | 13 |
| raa | 95 | 23 | %24,2 | 13 |
| saa | 68 | 3 | %4,4 | 0 |
| chronos | 79 | 2 | %2,5 | 0 |

İki değişim türü **ayrı** sayılır. Bir katmanı çıkarmak kararı iki yoldan
değiştirebilir: (a) toplam skor değişir ve eşik aşılır/aşılmaz — bu katmanın
bilgi değerinin işaretidir; (b) geçerli katman sayısı 3'ün altına düşer ve
karar BEKLE olur — bu katman hakkında **hiçbir şey söylemez**, yalnızca o
kayıtta zaten sınırda olunduğunu gösterir. İkisini tek sayıda toplamak
yanıltıcı olurdu.

Oranlar yalnızca katmanın **gerçekten ölçüldüğü** kayıtlar üzerinden
hesaplanır. Katmanın `null` olduğu kayıtları paydaya koymak, onu yapay olarak
"etkisiz" gösterirdi — oysa orada zaten yoktu.

## 2. Çapraz ölçüm ve görünür çelişki

Aynı 94 kayıt (≥3 katmanlı) üzerinde ikinci bir ölçüm yapıldı:

| katman | ortalama katkı | \|katkı\| payı | std | toplamla korelasyon |
|---|---:|---:|---:|---:|
| faa | **+3,330** | %60,5 | 1,105 | **r = +0,205** |
| taa | +0,372 | %16,4 | 0,875 | r = +0,638 |
| raa | +0,053 | %14,9 | 1,095 | r = +0,748 |
| chronos | −0,179 | %6,2 | 0,615 | **r = +0,777** |
| saa | +0,097 | %1,9 | 0,390 | r = +0,354 |

İki ölçüm ilk bakışta **çelişiyor**: FAA ablasyonda açık ara birinci (%69) ama
toplam skorla korelasyonda **sonuncu** (r=+0,205). Chronos ise tam tersi —
ablasyonda son (%2,5), korelasyonda birinci (r=+0,777).

**Çelişki değil; iki farklı şeyi ölçüyorlar.**

FAA'nın ortalaması büyük (+3,33) ama standart sapması görece küçük: neredeyse
**sabit ve büyük bir kaydırma** gibi davranıyor. Toplamı EKLE eşiğinin (≥4)
hemen yakınına taşıyor, dolayısıyla çıkarıldığında eşik neredeyse her zaman
geri geçiliyor — ablasyonda %69. Ama sabit olduğu için toplamın *değişimiyle*
birlikte hareket etmiyor, o yüzden korelasyonu düşük.

Chronos ise ortalaması ~0 olan, oynak bir katman: toplamın değişimini iyi
izliyor (r=0,777) ama genliği (±1) eşik atlatmaya nadiren yetiyor.

> **Sonuç:** FAA kararın **seviyesini**, diğer katmanlar **değişimini**
> belirliyor. Hiçbir ölçüm tek başına bu tabloyu vermiyor; biri "FAA her şeydir",
> öteki "FAA önemsizdir" derdi ve ikisi de yanlış olurdu.

Bu, madde 34'teki bağımsız bulguyla da tutarlı: FAA 100 kayıtta **hiç negatif
olmamış** (min +1), çünkü `score_faa` beş ölçütten üçünü yalnızca ödül olarak
kullanıyor.

## 3. Hiyerarşik süreç gerekli mi?

**Veriye göre hayır.**

- **FAA atlanamaz** — kararın seviyesini o belirliyor. Onu koşullu çağırmak
  kararların %69'unu değiştirir.
- **Chronos ve SAA nadiren eşik atlatıyor** (%2,5 ve %4,4), yani "gereksiz"
  görünüyorlar. Ama tam da onlar toplamın değişimini taşıyan katmanlar. Onları
  atlamak, az kazanç için sistemin tek oynak sinyallerini kaybetmek olurdu.
- **Ablasyon etkisi, değer değildir.** Chronos'un %2,5'lik payı, o 2,5'te
  *yanlış* olduğu anlamına gelmez; tersine, en belirleyici olduğu anlar tam da
  o anlar olabilir. Bu ölçüm etkiyi ölçer, isabeti değil — isabet ölçümü ayrı
  bir iştir (`was_correct` alanı üzerinden yapılabilir, bu maddede yapılmadı).

Ek olarak: beş katman zaten **paralel** çağrılıyor ve hepsi ücretsiz iç
servisler. Hiyerarşik seçimin kazancı gecikme değil, yalnızca karmaşıklık
olurdu. Karar yolu Anayasa v4.4'te sabit ve korunmuş durumda; değiştirmek için
bir gerekçe **ölçülemedi.**

## 4. Şüphecilik turu

| # | mutasyon | sonuç |
|---|---|---|
| M1 | yeter sayı düşüşünü eşik kayması say | YAKALANDI |
| M2 | yeter sayı düşüşünü hiç tespit etme | YAKALANDI |
| M3 | hiç ölçülmeyen katmanda oranı 0 göster | YAKALANDI |
| M4 | ölçülemeyen kayıtları da paydaya kat | YAKALANDI |
| M5 | kayıtta olmayan katmanı da raporla | YAKALANDI |
| M6 | replay edilemeyen kaydı da değerlendir | YAKALANDI |

**Hayatta kalan mutasyon yok (0/6).** 14 test.

## 5. Üretilen dosyalar

- `maa/src/katman_etkisi.py` — ablasyon ölçümü (karar yolunu değiştirmez)
- `maa/src/test_katman_etkisi.py` — 14 test
