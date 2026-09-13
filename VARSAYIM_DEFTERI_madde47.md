# VARSAYIM DEFTERİ — Madde 47 (append-only)

## Faz 0

### V-001 [DOĞRULANDI] B1 ve B2 aynı ölçütü işaret ediyor, isabet.py dondurulmuş
Kanıt: `KAPANIS_madde47.md` Bölüm 0.2.

### V-002 [DOĞRULANDI] Y2'nin main.py izni proje kuralıyla çelişiyor, CLAUDE.md üstündür
Kanıt: `KAPANIS_madde47.md`, "Kritik Bulgu" bölümü. `maa/src/main.py`'ye bu
görevde de dokunulmayacak. Model Yükseltme Noktası 2 tetiklenmedi çünkü
`isabet_olcut.py` zaten main.py'ye dokunmayan izole bir mimaride.

### V-003 [DOĞRULANDI] Önceki ölçüm (b347a93) ham n kullanmış, bağımsızlık düzeltmesi yapılmamış
`isabet_olcut.py`/`test_isabet_taban.py`'daki `_taban()` fonksiyonu
`for i in range(len(k) - UFUK)` ile **günlük kaydırılan, tamamen örtüşen**
30 günlük pencereler kullanıyor (n=16.367 HAM, bağımsız değil). Bu görevin
gerektirdiği n_eff/örtüşmeyen pencere düzeltmesi **daha önce yapılmamış**.

### V-004 [VARSAYILDI] BEKLE'yi puanlamak proje invaryantını ihlal edebilir — RİSK
Commit `232d1a0` ("olculemedi durumu gercek notr'dan ayrildi") ve
`isabet_olcut.py`'nin kendi gerekçesi: BEKLE = "ölçülemedi" (yetersiz
katman), fiyat hareketine bakıp doğru/yanlış demek "ölçülemedi'yi bir
piyasa çağrısına çevirir" — tam olarak 232d1a0'ın kapattığı hata sınıfı.
**Risk:** görev metninin B seçeneği (BEKLE'yi |getiri|<δ ile puanlamak)
bu ilkeyi ihlal edebilir. **Yanlışsa ne olur:** BEKLE yanlışlıkla bir
piyasa tahmini gibi değerlendirilmiş olur, ki proje bunun tam tersini
savunuyor. Bu yüzden B, Faz 1'de **betimleyici** (puanlama değil) olarak
ölçülecek ve Faz 2'de bu gerilim açıkça tartışılacak.

## Faz 1 — Ölçüm

### V-005 [DOĞRULANDI] Bağımsızlık düzeltmesi uygulandı — n HAM 11.373'ten n_eff 382'ye düştü
Geliştirme setinde (holdout kilitli), örtüşmeyen 30 günlük pencerelerle
(sembol başına ~38 pencere × 10 sembol) n_eff=382. Kanıt: `faz1_olcum.py`
çıktısı.

### V-006 [DOĞRULANDI] A (±%5): n_eff düzeltmesi sonrası bulgu ESKİ ölçümle TUTARLI ama literal H_A REDDEDİLİYOR
p_hat=0,5105, Wilson %95 GA=[0,4605; 0,5602] — **%50'yi kapsıyor**.
Cohen's h=+0,0209 (ihmal edilebilir). p=0,682 (anlamlı değil).
**Önceki HAM ölçümün raporladığı %47,7 bu aralığın İÇİNDE** — yani
bağımsızlık düzeltmesi seçimi DEĞİŞTİRMİYOR, tersine DOĞRULUYOR.

**Önemli kavramsal not:** H_A'nın kendisi ("taban %50'den anlamlı
farklılaşır") bu eşik için YANLIŞ çerçevelenmiş bir hipotez olabilir.
b347a93'ün orijinal gerekçesi ±%5'i "yazı-tura referansına EN YAKIN eşik"
olduğu için seçti — yani **amaç zaten %50'ye YAKIN olmaktı**, ondan
UZAKLAŞMAK değil. Bu durumda H_A'nın reddedilmesi bir başarısızlık değil,
tasarım hedefinin gerçekleştiğinin kanıtı olabilir. Bu gerilim Faz 2'de
kullanıcıya açıkça sunulacak, tek taraflı yorumlanmayacak.

### V-007 [DOĞRULANDI] B (BEKLE, gerçek `decision_log` verisi): ciddi biçimde yetersiz örnek
`decision_log` tablosundan gerçek BEKLE kararları çekildi (canlı Postgres,
harici harcama yok — Y3 korunuyor). **n=12** değerlendirilmiş BEKLE kararı,
**yalnızca 4 benzersiz karar günü** (8/12'si tek bir günde, 2026-08-03).
δ=3%: 2/12, Wilson=[0,047;0,448], p=0,021 (nominal anlamlı GİBİ görünüyor).
δ=5%: 5/12, Wilson=[0,193;0,680], p=0,564.
δ=7%: 7/12, Wilson=[0,320;0,807], p=0,564.
**n_eff(B) ≤ 4** (benzersiz gün sayısı) — hiçbir eşik için n_min
karşılanmıyor (en düşük gereksinim bile 10+).

### V-008 [DOĞRULANDI] BH-FDR: 4 test (A:1, B:3), q=0,05 → **HİÇBİRİ anlamlı değil**
| Test | p | FDR sonrası anlamlı mı |
|---|---|---|
| A (eşik=5%, n_eff=382) | 0,68231 | HAYIR |
| B (δ=3%, n=12) | 0,02090 | HAYIR |
| B (δ=5%, n=12) | 0,56370 | HAYIR |
| B (δ=7%, n=12) | 0,56370 | HAYIR |

### V-009 [DOĞRULANDI] Kendi bulduğum ek hata: `decision_log`'da bir yinelenen satır
BEKLE verisinde 12 satırdan biri tam yinelenen (`NVDA, 2026-08-02, 0.1356`
iki kez). `HATA_HAFIZASI_madde47.md`'ye kaydedildi.

### V-010 [DOĞRULANDI] Sembol bazında heterojenlik (Simpson kontrolü)
±%5 eşiğinin sembol başına tabanı **0,211 (NVDA) ile 0,914 (JEPI) arasında**
değişiyor — düşük volatiliteli ETF'ler (JEPI, SCHD) neredeyse hep "doğru",
yüksek volatiliteli büyüme hissesi (NVDA) neredeyse hep "yanlış" çıkıyor.
Bu klasik Simpson ters-yön paradoksu değil (toplu yön tekil semboller
tarafından tersine çevrilmiyor) ama **havuzlanmış %51 tabanının, çok
farklı davranan sembolleri maskelediğini** gösteriyor. Bu, görevin
kapsamı dışında bir tasarım sorusu (sabit vs volatiliteye-göreli bant) —
`[AÇIK SORU]` olarak işaretlendi, bu görevde çözülmedi.

### Şüphecilik Turu (Faz 1.4) — yazılı cevaplar
- **Cherry-picking:** A için yalnızca ±%5 test edildi (ön-kayıt gereği,
  yeniden tarama yok). B için 3 eşik denendi, **BH-FDR uygulandı** — hiçbiri
  hayatta kalmadı.
- **Bağımsızlık:** Pencereler örtüşüyordu (günlük kaydırma, 29 gün ortak).
  n_eff düzeltmesi (örtüşmeyen pencereleme) **uygulandı**: A için 382,
  B için gerçek veri kümesi zaten küçük ve kümelenmiş (n_eff≤4).
- **Holdout sızıntısı:** Holdout'a (2024-09-06 sonrası) **bakılmadı** —
  ölçüm fonksiyonu `tarih_ust` parametresiyle açıkça kesildi, kod incelemesi
  ile doğrulanabilir.
- **Veri sürümü:** Ön-kayıtta belirtilen kaynak (`qlib-service/.../us_data`)
  kullanıldı, sapma yok.
- **Örnek yeterliliği:** A için yeterli (n_eff=382 ≥ n_min). B için **hiçbir
  eşikte yeterli değil** (n_eff≤4 ≪ n_min).
- **Simpson paradoksu:** V-010'da ele alındı — ters yön yok ama ciddi
  heterojenlik var, açık soru olarak kaydedildi.
- **Seçim yanlılığı:** "En iyi görünen pencere" seçilmedi; ön-kayıtta
  sabitlenen kronolojik geliştirme/holdout bölmesi ve KARAR_EVRENI
  (10 sembol, gerçek karar evreni) kullanıldı.

**Faz 1 Bitiş Kapısı:** (a)-(f) sağlandı. → **Faz 1 KAPANDI.**

## Faz 2

### V-011 [AÇIK SORU] Sabit ±%5 bandı, sembol volatilitesine göre çok farklı davranıyor
JEPI/SCHD (düşük vol.) tabanı ~%90, NVDA (yüksek vol.) ~%21. Sabit bir
göreli bant yerine volatiliteye normalize bir bant (örn. ATR/β ayarlı)
daha tutarlı olabilir mi? Bu görevin kapsamı dışında, kullanıcıya
bildiriliyor.

### V-012 [AÇIK SORU] `decision_log`'daki yinelenen satırın kök nedeni
Hata Hafızası Hata #1'e bakınız. Bu görev yalnızca okuma yaptı; kök neden
araştırması ayrı bir görev gerektirir.
