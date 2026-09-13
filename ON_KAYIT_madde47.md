# ÖN-KAYIT — Madde 47

**Bu dosya, ölçüm başlamadan ÖNCE yazılıp commit edilmiştir. Ölçüm bittikten
sonra değiştirilemez** (Y7). Sapma olursa `KAPANIS_madde47.md`'de gerekçesiyle
kayıt altına alınır, bu dosya değil.

## Hipotezler

- **H_A:** Piyasaya göreli TUT bandı ±%5'e çekildiğinde (mevcut seçim,
  `isabet_olcut.py`) taban oranı %50'den anlamlı biçimde farklılaşır
  (Wilson %95 GA %50'yi dışlar).
- **H_B:** BEKLE dönemlerinde gerçek fiyat hareketinin |getiri|<δ ile tanımlı
  "sakin kalma" oranı, δ∈{%3,%5,%7} için %50'den ayrışır. **Not (V-004):**
  bu ölçüm **betimleyicidir**; BEKLE'yi bir piyasa çağrısı gibi puanlamak
  commit `232d1a0`'ın kapattığı "ölçülemedi ≠ sıfır" ilkesiyle gerilim
  taşıyabilir — Faz 2'de açıkça tartışılacak, otomatik olarak
  uygulanmayacak.
- **H_C (null):** Mevcut durum (A zaten uygulanmış, B uygulanmamış) diğer
  seçeneklerden anlamlı biçimde farklı değildir; dokunmaya gerek yoktur.

## Veri

- Semboller (10, gerçek karar evreni — `test_isabet_taban.py`'deki
  `KARAR_EVRENI` ile birebir, genel bir liste DEĞİL):
  ASML, CAT, GOOGL, JEPI, LLY, NVDA, O, SCHD, TSM, WDC
- Piyasa vekili: SPY
- Pencere: 30 iş günü ileri getiri
- Kaynak: `qlib-service/csv_data_persistent/us_data/<SEMBOL>.csv` (günlük kapanış)
- Ortak tarih aralığı: `2020-01-02` → `2026-09-09` (SPY'nin kapsadığı aralık,
  en kısıtlayıcı seri)
- Bölme (ZAMAN BAZLI, kronolojik, RASTGELE DEĞİL):
  - **Geliştirme seti:** `2020-01-02` → `2024-09-06` (ilk ~%70)
  - **Holdout seti:** `2024-09-06` → `2026-09-09` (son ~%30, geliştirmeden
    SONRA gelen tarihler)
  - Gerekçe: rastgele bölme, örtüşen 30 günlük pencereler nedeniyle
    geliştirme/holdout arasında veri sızıntısına yol açardı (bir günün
    penceresi, ayrı kümeye düşen bitişik bir günün penceresiyle ortak gün
    paylaşabilir). Zaman bazlı bölme, holdout'un tamamen geliştirmeden
    sonraki bir dönem olmasını garanti eder.

## Bağımsızlık Kontrolü (ÖLÇÜMDEN ÖNCE karar verildi)

**Örtüşme var mı?** EVET, doğrulandı: mevcut `isabet_olcut.py`/
`test_isabet_taban.py`'daki `_taban()` fonksiyonu `for i in range(len(k) -
UFUK)` ile **her günden bir pencere** başlatıyor — 30 günlük pencereler
günlük kaydırılıyor, yani bitişik pencereler 29 gün ortak paylaşıyor.
Bu, önceki ölçümün (`n=16.367`) **HAM, bağımsız olmayan** bir sayı
olduğu anlamına gelir (kayıt: V-003).

**Seçilen yöntem: (b) — pencereleri ÇAKIŞMAYACAK şekilde seç.**

Gerekçe (neden (a) blok bootstrap değil): Blok bootstrap (sistemin
`stres-testi-service/src/montecarlo.py:82` `blok_yol()` deseni) bir
**simülasyon** aracıdır — mevcut örneklemin *volatilite yapısını* koruyarak
yeni yollar üretir, ama iki ayrı oranı (p_TUT vs 0.50) karşılaştırmak için
gereken şey simülasyon değil, **gerçekten bağımsız gözlem sayısıdır**.
Örtüşmeyen pencereleme (her sembolde 30 günde bir örnekleme) n_eff'i
*tahmin etmek* yerine bağımsızlığı **doğrudan sağlar**, ekstra varsayım
(blok uzunluğu, dairesellik) gerektirmez ve denetlenmesi/tekrarlanması
daha kolaydır. n azalır ama (aşağıda hesaplanacak) güç analizi yeterliyse
bu kabul edilebilir bir bedeldir.

**Uygulama:** her sembol için pencereler `i = 0, 30, 60, 90, ...` (UFUK
adımıyla), `i` ve `i+UFUK` arası **hiçbir günü** başka bir pencereyle
paylaşmaz. Tüm sonraki testlerde bu **n_eff** (gerçek bağımsız gözlem
sayısı) kullanılır, önceki HAM n (16.367) değil.

## Testler (önceden sabit)

- **Birincil:** Wilson %95 güven aralığı, %50 tabanını dışlıyor mu?
- **İkincil:** İki oran arası fark için Newcombe hibrit %95 GA.
- **Etki büyüklüğü:** Cohen's h = 2·arcsin(√p1) − 2·arcsin(√p2).
- **Çoklu karşılaştırma:** Benjamini–Hochberg FDR, q = 0.05 (test edilen
  tüm p-değerleri: H_A için 1, H_B için 3 [δ=%3,%5,%7] = toplam 4 test).
- **Minimum örneklem / güç:** iki oranlı z-testi için elle hesaplanan
  `n_min = ((z_{α/2}+z_β)² · (p1(1−p1)+p2(1−p2))) / (p1−p2)²`,
  `z_{0.025}=1.96`, `z_{0.20}=0.8416` (güç 0.80), `α=0.05`. Referans
  p1=0.50 (null), p2=ölçülen değer. `statsmodels` bu ortamda mevcut
  değilse (kontrol edilecek) yukarıdaki kapalı-form formül kullanılır ve
  bu KAPANIS'ta açıkça belirtilir.

## Denenecek eşik sayısı (önceden sabit — yeniden tarama YOK)

- **A için:** yalnızca ±%5 (10.09.2026'da zaten seçilmiş değer; yeniden
  tarama yapılmayacak, yalnızca bağımsızlık-düzeltmeli yeniden doğrulama).
- **B için:** {±%3, ±%5, ±%7} — üç eşik, FDR düzeltmeli.
- **C için:** eşik yok (dokunmama senaryosunun nicel maliyet/fayda analizi).

## Durma Kuralları

- **Faz 2.2:** FDR sonrası hiçbir seçenek anlamlı değilse, VEYA iki seçenek
  arasındaki fark GA'da örtüşüyorsa, VEYA güç <0.80 ise → DUR + Model
  Yükseltme Noktası 1, kullanıcıya sun.
- **Holdout'ta birincil test başarısızsa** → karar geri alınır (revert),
  `HATA_HAFIZASI_madde47.md`'ye kayıt, DUR.
