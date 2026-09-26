# FAZ 2 — Tasarım (Bildirim Merkezi denetimi/sertleştirme)

Bu tasarım, orijinal V5 spec'inin greenfield varsayımını DEĞİL, FAZ 0/1'de
doğrulanmış gerçek mimariyi temel alır. Spec'in üç ADR'si gözden geçirilip
gerçeğe göre KABUL/RED/REVİZE edildi; yalnızca 3 doğrulanmış boşluk (okundu/
okunmadı, otomatik yenileme, erişilebilirlik) için yeni kod yazılacak.

## ADR-001 (REVİZE): Polling
**Bağlam:** Spec, pollingin zaten var olduğunu varsayıp yalnızca aralığını
tartışıyordu (30sn). Gerçekte HİÇ otomatik yenileme yok — `BildirimMerkezi.tsx`
yalnızca mount'ta bir kez `fetch('/api/bildirimler')` çağırıyor.
**Karar:** 30 saniyelik `setInterval` polling eklenecek (Y2 gereği yeni
bağımlılık yok — mevcut `fetch` + native `setInterval`).
**Gerekçe:** WebSocket yeni sunucu bileşeni ister (Y2 ihlali). 30sn, sistemin
diğer servislerindeki (R-15 bekçisi 15dk, mutabakat günlük) tetikleme
sıklığına göre yeterince duyarlı ve middleware'deki `sinyal` sınıfı hız
sınırına (60/dk) rahatça sığar (30sn'de 2 istek/dk, sınırın çok altında).
**Alternatif:** Manuel yenile düğmesi (reddedildi: kullanıcı R-15/mutabakat
gibi kritik alarmları kaçırabilir — sessiz sistem hatası riski, Y11 ruhuna
aykırı).

## ADR-002 (RED): Süre bazlı bayatlık eşiği
**Spec'in önerisi:** 24 saatten eski bildirimler "geçmiş" sayılsın.
**Red gerekçesi:** Gerçek sistemde bu SORUNU DAHA KÖTÜ yapardı. Bir alarm
(örn. R-15 geçiş penceresi, mutabakat sorunu) 25 saat boyunca ÇÖZÜLMEDEN açık
kalabilir — süre bazlı eşik bunu "geçmiş/önemsiz" gibi gösterirdi, ki bu tam
olarak 08.09.2026 hatasının tersi bir sessiz hata sınıfı yaratırdı. Mevcut
`sonraki_normal_kayit` mekanizması (bu alarmdan SONRA aynı kaynaktan kaç
normal kayıt geldi) olgusal ve doğru: yalnızca gerçekten yeni normal kayıt
geldiyse "büyük olasılıkla kapandı" der, süre geçmesiyle DEĞİL.
**Sonuç:** ADR-002 UYGULANMAYACAK. Mevcut mekanizma korunur.

## ADR-003 (RED, gerekçe revize): Kategori ayrımı
**Spec'in önerisi:** `kategori` alanı: sistem-gizli vs kullanıcı-görünür,
middleware'de rol bazlı filtre.
**Gerçek durum:** Bu ZATEN VAR ama farklı isimle/yerde — `route.ts` içinde
`rolKapisi()` ile TÜM besleme (kısmi alan filtreleme değil, ikili kapı:
admin/partner görür, diğerleri 403+tam gizleme görür). İçerik kullanıcı bazlı
değil (herkes için aynı sistem-işletim kaydı), bu yüzden alan bazlı kategori
ayrımı GEREKSİZ — ikili rol kapısı yeterli ve zaten `bildirimler-rol.test.ts`
ile test edilmiş (174 satır, sızıntı yok senaryosu dahil).
**Sonuç:** ADR-003 UYGULANMAYACAK, mevcut ikili kapı korunur.

## ADR-004 (YENİ): Okundu/okunmadı kalıcılığı (Y10 boşluğu)
**Bağlam:** Her bildirim id'si (kaynak+zaman+mesaj üçlüsünden türetilmiş,
zaten `tekille()` içinde kullanılan aynı anahtar) için okunma durumu
gerekiyor; şu an hiç yok.
**Karar:** `frontend/src/lib/grafik/gosterge-kalicilik.ts` deseniyle TUTARLI
bir localStorage anahtarı: `alphawise:bildirim:okundu:v1:<kullaniciId>`
(değer: okunmuş bildirim id'lerinin JSON dizisi, üst sınır 500 — kaynak
`/bildirimler?azami=40` zaten üst sınırlı olduğu için pratikte hiç dolmaz).
Bildirim id'si: `sha256(kaynak|zaman|mesaj)` ilk 16 hex — çakışma riski
ihmal edilebilir, deterministik, sıralamadan bağımsız.
**Gerekçe:** KALICILIK_SONUC.md/WATCHLIST_SONUC.md bulunamadı (FAZ 0);
gösterge-kalıcılığı deseni depodaki TEK doğrulanmış emsal ve aynı ad alanı
kuralını (kullanıcı bazlı) izliyor. `kullaniciId` `/api/bildirimler`
yanıtından DEĞİL, oturum context'inden alınacak (bkz. S4 uygulaması —
middleware zaten `x-alphawise-kullanici` başlığını aşağı akışa taşıyor,
ama bu API GET'te bileşene dönmüyor; tarayıcı tarafında kullanıcı kimliği
zaten dashboard'da mevcut context/hook'tan okunuyor — S4'te doğrulanacak).
**İki sekme senkronizasyonu:** `window.dispatchEvent(new StorageEvent(...))`
+ `window.addEventListener('storage', ...)` — spec'in S4 kod örneğiyle
uyumlu, native API, yeni bağımlılık yok (Y2).
**Rozet düzeltmesi:** `rozetSayisi()` artık ham kritik+alarm toplamı değil,
"okunmamış" kritik+alarm sayısını dönecek (bildirim id'si `okundu` listesinde
YOKSA sayılır).

## ADR-005 (YENİ): Erişilebilirlik (Y12 boşluğu)
**Karar:** Zil düğmesine `aria-label`, `aria-expanded`, `aria-controls`;
panel `role="region"` + `aria-label`; `Escape` ile kapama; her bildirim
satırına `tabIndex=0` + `Enter`/`Space` ile okundu işaretleme. Mobil:
mevcut `flexWrap` düzeni zaten 390px'te taşmıyor (FAZ 4'te Playwright ile
doğrulanacak) — yalnızca dokunma hedefi boyutu (`minHeight`) zaten 40px,
WCAG 2.5.5 (24px) eşiğinin üzerinde, ek değişiklik gerekmiyor.

## C1–C10 durumu (spec sözleşmeleri, gerçeğe göre güncellendi)
| Kod | Spec önerisi | Gerçek durum | Aksiyon |
|---|---|---|---|
| C1 | Doğrudan port 8350 | `/api/bildirimler` proxy | Değişmeyecek, dokunulmayacak |
| C2 | 24s bayatlık | Olgusal `sonraki_normal_kayit` | ADR-002 RED |
| C3 | kategori alanı | İkili rol kapısı | ADR-003 RED |
| C4 | Zil+panel UI | Zaten var (`BildirimMerkezi.tsx`) | A11y eklenecek (ADR-005) |
| C5 | Polling>WebSocket | Kabul, ama polling HİÇ yoktu | ADR-001 UYGULA |
| C6 | middleware kimlik | Zaten var (`rolKapisi`) | Dokunulmayacak |
| C7 | localStorage kalıcılık | YOK (boşluk) | ADR-004 UYGULA |
| C8 | 503+mesaj | Zaten var (`durumOzeti(null)`) | Dokunulmayacak |
| C9 | `{bildirimler,meta}` şeması | Gerçek şema daha zengin (bkz. FAZ 1) | Şema DEĞİŞTİRİLMEYECEK, yalnızca belgelenecek |
| C10 | `git revert` | Standart | Kapanışta uygulanacak |

## UI değişikliği kapsamı
Yalnızca `frontend/components/BildirimMerkezi.tsx` (polling + a11y + okundu
state) ve yeni `frontend/src/lib/bildirim-okundu.ts` (saf, test edilebilir
okundu/okunmadı mantığı — mevcut `bildirim-ozet.js` desenine uygun ayrı
modül, Y6/test-önce disiplinine uygun). `bildirim-ozet.js`'e yalnızca
`rozetSayisi()` imzası genişletilecek (geriye dönük uyumlu: 2. parametre
opsiyonel `okunanIdSeti`).

→ FAZ 3'e geçiliyor.
