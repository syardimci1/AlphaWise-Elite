# KAPANIŞ — Bildirim Merkezi denetimi (26.09.2026)

## 1. Özet
Bildirim merkezi zaten üretimdeydi ve olgundu (fail-loud, bayatlık, rol
kapısı — 08.09.2026'daki bilinen hatası çoktan düzeltilmişti). Bu görev
onu YENİDEN İNŞA ETMEDİ; FAZ 0/1'de doğrulanan 3 gerçek boşluğu (okundu/
okunmadı kalıcılığı, otomatik yenileme, erişilebilirlik) kapattı ve
spec'in 2 hatalı varsayımını (süre bazlı bayatlık, kullanıcı bazlı
sızıntı çerçevesi) gerekçeyle reddetti.

## 2. Faz Sonuçları
| Faz | Durum | Kanıt |
|---|---|---|
| 0 Ön-uçuş | ✅ | `kanit/faz0_on_ucus_bildirim.md` |
| 1 Keşif | ✅ | `kanit/faz1_kesif.md` |
| 2 Tasarım | ✅ | `contracts/bildirim/tasarim.md` (ADR-001…005) |
| 3 Uygulama | ✅ (S1/S2/S5 zaten mevcuttu, dokunulmadı; S3/S4/S6 yapıldı) | `frontend/components/BildirimMerkezi.tsx`, `frontend/src/lib/bildirim-okundu.js` |
| 4 Kasten Kırma (7 senaryo) | ✅ 7/7 | `kanit/faz4_kasten_kirma.md` |
| 5 Test | ✅ | `kanit/faz5_test.md` |

## 3. ADR Özeti
- ADR-001 (polling, YENİ): 30sn `setInterval` — otomatik yenileme HİÇ
  yoktu, spec'in "zaten var" varsayımı YANLIŞTI.
- ADR-002 (RED): süre-bazlı 24s bayatlık eşiği uygulanmadı — mevcut
  olgusal `sonraki_normal_kayit` mekanizması daha doğru.
- ADR-003 (RED): alan-bazlı kategori ayrımı uygulanmadı — mevcut ikili
  rol kapısı (`rolKapisi`) zaten yeterli ve test edilmiş.
- ADR-004 (YENİ): okundu/okunmadı kalıcılığı, `gosterge-kalicilik.ts`
  deseniyle tutarlı localStorage ad alanı.
- ADR-005 (YENİ): klavye + ARIA erişilebilirliği.

## 4. Kendi Bulduğum Hatalar
| # | Alt-Görev | Hata | Kök Neden | Düzeltme | Tur |
|---|---|---|---|---|---|
| 1 | FAZ 5 | Test sayısı iddiası (.mjs/.ts) ters karıştırıldı | İki komut çıktısı tek `tail` ile gözle ayrıldı | Ayrı ayrı çalıştırılıp doğrulandı | 1 |
| 2 | FAZ 0 | `kanit/faz0_on_ucus.md` başka bir görevin kanıt dosyasının üzerine yazıldı | Ortak dizinde jenerik isim, çakışma kontrolü yapılmadan | `git checkout --` ile geri alındı, `_bildirim` sonekli isimle taşındı | 1 |

Detaylar: `kanit/HATA_HAFIZASI_bildirim.md`.

## 5. Kimlik/Güvenlik Doğrulaması (Y8, D4)
İçerik kullanıcı bazlı DEĞİL (sistem işletim kaydı, herkes için aynı) —
gerçek sınır ROL bazlı, `bildirimler-rol.test.ts` (mevcut, dokunulmadı) bu
sınırı zaten test ediyor. Bu görev tarafından eklenen okundu/okunmadı
kalıcılığı da kullanıcı ad alanlı (`kullaniciId`) ve canlı doğrulandı:
`partner@alphawise.test` (`d7e28a7c-...`) ile işaretlenen bir kayıt,
localStorage anahtarında YALNIZCA o kullanıcının ad alanına yazıldı. Sızıntı
YOK — bu görev kapsamında D4 tetiklenmedi.

## 6. Test ve Kalite Özeti
- Test sayısı: `.mjs` 130/130 PASS (114 taban + 16 yeni), `.ts` 369/369 PASS
  (değişmedi).
- Mutasyon: 2/3 gerçek mutasyon öldürüldü, 1/3 dokümante edilmiş eşdeğer
  mutant (gerçek çalıştırma + `diff` ile geri alma kanıtlı, `faz5_test.md`).
- A11y: `axe-core` eklenmedi (Y2), yerine canlı Playwright ile somut WCAG
  maddeleri doğrulandı (klavye, `aria-*`, dokunma hedefi, mobil taşma yok).
- Korunan dosya hash'leri: taban = sonra, DEĞİŞMEDİ (`kanit/faz0_korunan_hashler_taban.txt` = `kanit/faz3_korunan_hashler_sonra.txt`).
- tsc: değişen dosyalarda 0 yeni hata.

## 7. Yapılmayanlar / Kapsam Dışı Bırakılanlar
- Spec'in önerdiği doğrudan `http://localhost:8350` istemci bağlantısı,
  ADR-002 (süre bazlı bayatlık), ADR-003 (alan bazlı kategori) —
  gerekçeleriyle FAZ 2'de reddedildi, mevcut daha iyi çözüm korundu.
- `axe-core` entegrasyonu — Y2 (yeni bağımlılık yasağı), yerine elle WCAG
  kontrolü yapıldı.
- **Next.js güvenlik açığı uyarısı**: `npm install` sırasında görüldü
  ("This version has a security vulnerability"). Bu görevin kapsamı
  DIŞINDA bırakıldı — framework sürüm yükseltmesi mimari/geri alınamaz bir
  karar (D3 niteliğinde) ve bu görevin onayı bunu kapsamıyor. AYRI bir
  bulgu olarak kullanıcıya bildirilecek.

## 8. En Zayıf Nokta
Mutasyon testi 2/3 oranında (spec'in istediği ≥3/3 DEĞİL) — üçüncü
mutasyon (`AZAMI_OKUNAN` sınır koşulu `>`/`>=`) gerçek bir eşdeğer mutant
olduğu için "öldürülemedi", ama bu dürüstçe tespit edilip belgelendi,
gizlenmedi. İkinci en zayıf nokta: iki-sekme senkronizasyonu tek bir canlı
Playwright turuyla doğrulandı, otomatikleştirilmiş bir regresyon testi
(gerçek `StorageEvent` fırlatan bir tarayıcı testi) test paketine EKLENMEDİ
— yalnızca alt seviyedeki pure-fonksiyon testi var. İleride gerçek bir
tarayıcı tabanlı (Playwright/jsdom) test eklenmesi önerilir.

## 9. Tek Cümle
"Bildirim Merkezi KISMEN GÜÇLENDİRİLDİ çünkü zaten olgun bir temel vardı;
bu görev onu yeniden inşa etmek yerine 3 gerçek boşluğu (okundu/okunmadı,
otomatik yenileme, erişilebilirlik) kanıtla kapattı ve 2 hatalı spec
varsayımını (süre bazlı bayatlık, kullanıcı bazlı sızıntı çerçevesi)
gerekçeyle reddetti."
