# FAZ 4 — Kasten Kırma (7 senaryo)

Gerçek `alphawise-bildirim` konteyneri (production, healthy) + gerçek üretim
verisiyle (25 açık kayıt) izole test konteyneri (`bildirim-denetim-test`,
`alphawise-net`+`supabase_default`), gerçek Supabase oturumu
(`partner@alphawise.test`) üzerinden canlı doğrulandı.

| # | Senaryo | Yöntem | Sonuç |
|---|---|---|---|
| 1 | 0 bildirim | `bildirim-ozet.test.mjs:11` ("hicbir olay yok...") | ✅ Zaten test kapsamında, "alarm yok" doğru üretiliyor |
| 2 | Tüm bildirimler bayat | `bildirim-ozet.test.mjs:70` + **canlı kanıt**: gerçek listede 22/25 kayıt "sonrasında N normal kayıt geldi (büyük olasılıkla kapandı)" gösteriyor, kayıt SİLİNMEDİ | ✅ |
| 3 | Bildirim servisi çökük | `bildirim-ozet.test.mjs:25` ("servis hic yanit vermediyse") + `route.ts`'in `servisProxy` 15sn timeout | ✅ |
| 4 | 50+ bildirim (performans) | `bildirim-okundu.test.mjs`: 500 sentetik kayıt, `okunmamisSayi` <200ms (ölçülen gerçek süre testte loglanır, sınır altında) | ✅ |
| 5 | İki sekmede aynı anda okundu işaretleme | **Canlı Playwright**: 2 gerçek tarayıcı sekmesi, aynı oturum. Sekme 2'de bir kayıt okundu işaretlendi → Sekme 0'a reload YAPILMADAN geçildi → rozet 23'ten 22'ye düştü (native `storage` olayı doğrulandı, kod: `BildirimMerkezi.tsx` `window.addEventListener('storage', ...)`) | ✅ |
| 6 | role='user' sistem-gizli içeriği görmeye çalışırsa | `bildirimler-rol.test.ts` (174 satır, mevcut) — 403 + bileşen tam gizlenir, sızıntı yok | ✅ Zaten test kapsamında (dokunulmadı) |
| 7 | Geçersiz kullanıcı kimliği | `bildirim-okundu.test.mjs`: boş string/`null` kimlikle `okunanlariOku`/`okunduIsaretle` çökmez, farklı ad alanına karışmaz. Bileşen tarafında `if (!kullaniciId) return` koruması zaten var (kod incelemesiyle doğrulandı, `BildirimMerkezi.tsx`) | ✅ |

## Canlı doğrulama detayları (ek kanıt)

- Gerçek giriş: `partner@alphawise.test`, gerçek `kullaniciId=d7e28a7c-d217-4abd-8fa5-ddc93d869d60` — `/api/config/kimlik` ucundan doğru çekildi.
- localStorage anahtarı doğrulandı: `alphawise:bildirim:okundu:v1:d7e28a7c-d217-4abd-8fa5-ddc93d869d60` = `["3dbd79fe"]` (tasarımdaki ADR-004 formatıyla birebir).
- Klavye: `Tab` ile bildirim satırına odaklanıldı, `Enter` ile okundu işaretlendi (fare kullanılmadan) — `aria-label` "Okunmadi..." → "Okundu isaretli kayit" değişti.
- `Escape`: panel içinde odak varken panel kapandı (`aria-expanded` kalktı).
- Mobil (390×844): yatay taşma YOK (`document.body.scrollWidth === window.innerWidth`), dokunma hedefi 40px (WCAG 2.5.5 eşiği 24px üzeri).
- Konsol: 0 hata, 0 uyarı (`browser_console_messages`).
- Ağ: 5 ardışık `/api/bildirimler` isteği, tümü 200 OK, hiç 429/500 yok.
- Ekran kanıtı: `faz4_mobil_390px.png` (çalışma dizininde).

## Temizlik
`bildirim-denetim-test` konteyneri ve imajı test sonunda kaldırıldı
(`docker rm -f` + `docker rmi`). Üretim `alphawise-bildirim` konteynerine
DOKUNULMADI (yalnızca okundu, healthy durumu korundu).
