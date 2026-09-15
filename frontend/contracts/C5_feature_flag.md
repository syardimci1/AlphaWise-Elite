# C5 — Feature Flag: `koyfin_event_overlay`

**Varsayılan: KAPALI.** Sunucu restart'ı gerektirmeden anında
açılıp/kapanabilmeli (Y5 + Faz 5 kill-switch gereksinimi).

## Uygulama kararı (FAZ 2'de yazılacak)

`localStorage` DEĞİL — çünkü (a) URL ile paylaşılabilir olmalı
(C.Filtre kuralı ile aynı sözleşme: durum URL query'de), (b)
kill-switch'in sunucu tarafından TEK noktadan, kullanıcı tarayıcısına
dokunmadan kapatılabilmesi gerekiyor (Faz 5, Bölüm 4 alarm otomasyonu:
"p95>2sn 5dk boyunca → otomatik flag kapat").

Bu iki gereksinim birlikte şunu zorunlu kılıyor: flag durumu
**sunucu tarafında** (env var veya küçük bir config uç noktası)
tutulur, `NEXT_PUBLIC_KOYFIN_EVENT_OVERLAY` env değişkeniyle build-time
DEĞİL, `/api/config/koyfin-flag` gibi HER İSTEKTE okunan runtime bir
uçla kontrol edilir — env var olsaydı kapatmak yeniden build/deploy
gerektirirdi (Y5 atomik geri alınabilirlik + Faz5 kill-switch "10sn
içinde" hedefiyle ÇELİŞİRDİ).

Whitelist modu (Faz 5 ön-koşul kontrolü): aynı config ucu, sorgu
parametresi `?koyfin_preview=<token>` ile eşleşen istekler için flag
durumundan BAĞIMSIZ olarak açık döner — gerçek canary altyapısı
olmadığında "yumuşak açılış" eşdeğeri budur.
