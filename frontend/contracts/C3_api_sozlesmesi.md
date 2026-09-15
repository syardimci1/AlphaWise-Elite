# C3 — API Sözleşmesi

Y2 gereği (sıfır yeni harcama/uç): overlay katmanı YALNIZCA aşağıdaki
4 MEVCUT Next.js API route'unu kullanır — hiçbiri değiştirilmez,
hiçbiri yeni parametre almaz. Bunlar zaten salt-okuma, zaten önbellek
başlıklı (bkz. backend servislerin kendi Redis önbellekleri).

| Tip | Route (DEĞİŞMEZ) | Backend uc | Idempotent mi |
|---|---|---|---|
| CONGRESS | `/api/congress-trading/[ticker]` | `congress-trading-service:8210/trades/{ticker}` | Evet — aynı ticker aynı pencerede aynı sonucu verir (Redis önbellekli) |
| INSIDER | `/api/insider-trading/[ticker]` | `insider-trading-service:8250/insider/{ticker}` | Evet |
| DARK_POOL | **YENİ frontend route GEREKMİYOR** — `finra-darkpool-service:8200/regsho/{ticker}` zaten var, yalnızca frontend'de bu uca bir proxy route EKSİK (bkz. VARSAYIM V-007: bu, Y2'yi ihlal eder mi?) | | |
| 13F | `/api/sec-edgar-13f/[ticker]` | `sec-edgar-13f-service:8240/holders/{ticker}` | Evet |

## V-007 ÇÖZÜMÜ (Y2 sınırının netleştirilmesi)

Y2 "yeni API/abonelik yok" diyor — bu, **dış** (ücretli/üçüncü taraf)
kaynak eklememeyi kastediyor. `finra-darkpool-service` ZATEN üretimde
çalışan, ücretsiz, anahtarsız bir servistir; `/regsho/{ticker}` ZATEN
onun bir ucu. Eksik olan tek şey, frontend'in kendi iç proxy katmanında
(`src/app/api/`) bu uca giden BİR route dosyası — mevcut 3 örnekle
BİREBİR AYNI kalıpta (`/api/finra-darkpool/[ticker]` zaten VAR ama
`/darkpool/{ticker}` özet ucuna gidiyor, `/regsho/{ticker}`'a değil).
Bu, "yeni dış API" değil, mevcut dahili proxy kalıbının aynı servise
ikinci bir ucu için tekrarıdır — Y2 ihlali SAYILMAZ (VARSAYIM_DEFTERI
V-007, DUR-SOR eşiği aşılmadı, ama açıkça kayıt altına alınmalı).

## Sayfalama / önbellek

Overlay katmanı kendi sayfalama mantığı EKLEMEZ — 4 route da zaten
tam listeyi (backend'in kendi sınırlarıyla, örn. congress limit=100)
tek seferde döndürüyor. Önbellek başlıkları backend servislerin kendi
Redis TTL'lerinden gelir (7 gün 13F, günlük congress/insider) — overlay
katmanı bunları OKUR, üzerine yazmaz.
