# FAZ 1 — Keşif

## ALARM şeması (toplayici.py)
Olay nesnesi: `{kaynak, zaman (ISO ya da None), duzey ∈ {kritik,alarm,uyari,bilgi}, mesaj, ham, sonraki_normal_kayit, yas_gun}`.
Kaynak sonucu: `{kaynak, yol, durum ∈ {okundu,kismen_okundu,okunamadi,kaynak_yok}, gerekce, olaylar[], ad, aciklama, olay_sayisi}`.
`/bildirimler` yanıtı: `{ozet, bildirimler[], kesilen, kaynak_durumlari[], sessiz_mi, sessizlik_guvenilir_mi, not, bayatlik_notu}` — spec'in C9 önerdiği `{bildirimler, meta:{toplam,bayat,kategori}}`'den daha zengin ve zaten belgelenmiş; C9 bu gerçek şemayla GÜNCELLENECEK, değiştirilmeyecek.

## Bildirim-servisi API'si (gerçek, port dışarı 8350 varsayılan ama konteyner içi `alphawise-bildirim:8000`)
`GET /bildirimler?azami=40&yalnizca_alarm=true` — Next.js route (`/api/bildirimler`) `servisProxy()` ile bu uca vekillik ediyor, `BILDIRIM_URL` env değişkeniyle yapılandırılıyor. Doğrudan tarayıcı→8350 bağlantısı YOK ve OLMAMALI (C1 revize).

## İ-6 rol kapısı deseni
`frontend/src/app/api/bildirimler/route.ts`: `rolKapisi(req, izinliRoller(env, VARSAYILAN_ROLLER=['admin','partner']), ...)`. 403 dönerse `BildirimMerkezi.tsx` bileşeni TAMAMEN gizlenir (`erisimYetkisizMi` → `gizli=true` → `return null`), hata mesajı da göstermez — "yetkisiz" ile "arızalı" karışmıyor (Değişmez Kural, dosyanın kendi yorumunda açık).

## "Bayat alarm güncel görünüyor" kök nedeni (08.09.2026, spec'te "03.09" olarak anılmış — tarih farkı VARSAYIM_DEFTERI'nde işaretli)
Kök neden: mutabakat alarmı SADECE `ALARM_godmode_paper.log`'da aranıyordu; "sorun kapandı" bilgisi ayrı, günlük döndürülen `godmode_paper_mutabakat_*.log` dosyalarındaydı. Yalnızca alarm dosyası okunduğunda kapanış hiç görülmüyordu. Düzeltme: `desen_oku()` + `bayatlik_isaretle()` — TÜM kayıtlar (alarm+normal) okunur, her alarm için "bu alarmdan sonra aynı kaynaktan kaç normal kayıt geldi" sayılır (`sonraki_normal_kayit`), UI bunu `bayatlikMetni()` ile "N gün önce · sonrasında M normal kayıt geldi (büyük olasılıkla kapandı)" diye gösterir. Kayıt SİLİNMEZ — yorumu kullanıcı yapar.
**Regresyon testi**: bu tam senaryo `bildirim-ozet.test.mjs` içinde zaten kapsanıyor (FAZ 5'te doğrulanacak, test edilen dosya + satır kaydedilecek).

## Gerçek boşluklar (spec'in Y-maddeleriyle örtüşen, DOĞRULANMIŞ eksikler)

| Boşluk | Kanıt | İlgili Yasa |
|---|---|---|
| **Okundu/okunmadı kalıcılığı YOK** | `BildirimMerkezi.tsx` içinde bildirim-bazlı "okundu" state'i, localStorage anahtarı, ayrı unread-sayaç yok. `rozetSayisi()` her zaman kritik+alarm TOPLAMINI döner — kullanıcı panosu açıp baksa bile rozet sıfırlanmaz. | Y10 |
| **Otomatik yenileme (polling) YOK** | `useEffect` içinde `setInterval` yok, yalnızca mount'ta tek `fetch`. Kullanıcı sayfayı yenilemeden yeni alarmı görmez. | (spec ADR-001'in YANLIŞ varsaydığı "zaten var" durumu — gerçekte YOK, gerçek boşluk) |
| **Erişilebilirlik sıfır** | `grep aria-\|onKeyDown\|tabIndex\|role=` → 0 eşleşme (yorum dışı). Klavye ile aç/kapa yok, ekran okuyucu etiketi yok. | Y12 |

## Zaten var olan, spec'in yeniden icat ETMEMESİ gereken kısımlar

| Spec maddesi | Gerçek karşılığı | Sonuç |
|---|---|---|
| S1 (API entegrasyonu) | `/api/bildirimler` route + `servisProxy` + `rolKapisi` | Zaten var, dokunulmayacak |
| S2 (bayatlık/kategori) | `bayatlik_isaretle` (olgusal sayaç) + rol kapısı (sistem-gizli/kullanıcı-görünür yerine admin/partner-only) | Zaten var VE spec'in süre-bazlı ADR-002'sinden daha doğru; ADR-002 REDDEDİLECEK |
| S5 (fail-loud) | `durumOzeti(null)` → "Bildirim servisi yanıt vermedi" + `sessiz_mi`/`guvenilir_sessizlik` üçlü mantık | Zaten var |
| Y8 (kimlik sızıntısı çerçevesi) | İçerik kullanıcıya özel değil (herkes için aynı); gerçek sınır ROL, kullanıcı değil. `bildirimler-rol.test.ts` (174 satır) bu sınırı zaten test ediyor. | Spec'in "x-user-id ad alanlı bildirim" öncülü YANLIŞ VARSAYIM — düzeltildi |

## Taban test sayısı
`bildirim-ozet.test.mjs`: 18 test. `bildirimler-rol.test.ts`: mevcut (rol kapısı, sızıntı yok senaryosu dahil).

→ FAZ 2'ye geçiliyor (yalnızca 3 gerçek boşluk için tasarım: S4/Y10, polling, S6/Y12).
