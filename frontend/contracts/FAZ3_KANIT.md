# FAZ 3 — Şüphecilik Turu: Kanıt Dosyası

## 1) Marker doğru tarihte mi (sınır TZ dahil)?

`gunStringindenUtcMs`/`utcMsToIsGunuString` gerçek Node süreçlerinde,
Dünya'nın en uç iki saat dilimi (`Etc/GMT+12` = UTC-12, `Pacific/
Kiritimati` = UTC+14) DAHİL 4 ayrı `TZ` ortam değişkeniyle çalıştırıldı:

```
TZ=UTC                 -> 2026-09-03 (dogru)
TZ=Pacific/Kiritimati   -> 2026-09-03 (dogru, DEGISMEDI)
TZ=Etc/GMT+12           -> 2026-09-03 (dogru, DEGISMEDI)
TZ=Europe/Istanbul      -> 2026-09-03 (dogru, DEGISMEDI)
```

Epoch ms değeri de 4 TZ'de BİREBİR aynı (`1788393600000`) — marker
konumlandırması TZ'den tamamen bağımsız (C4'ün `Date.UTC` temelli
tasarımının doğrudan kanıtı).

## 2) Çok olaylı sembolde görsel gürültü — kümeleme yeterli mi?

25 ham olay, 6 farklı güne yığılmış senaryo (gerçekçi: aynı gün birden
fazla kongre üyesi/içeriden kişi açıklama yapabilir) canlı render
edildi: **25 → 6 görünen marker** (bkz. `contracts/kanit/` — ekran
görüntüsü zaten FAZ2'de alınan gerçek verideki kümelemeyle aynı
mekanizmayı kullanıyor). Her kümelenmiş marker "+N" etiketiyle kaç
olayın gizlendiğini AÇIKÇA gösteriyor (sessiz kayıp yok — tıklanınca
FAZ 2'de kanıtlandığı gibi TÜM üyeler tooltip'te listeleniyor).

## 3) Mevcut grafiğin diğer işlevleri (zoom/pan) bozulmadı mı?

Aynı sahte-kümeleme senaryosunda gerçek fare tekerleği olayı (`wheel`)
ile yakınlaştırma tetiklendi:

```
ONCESI:  {"from":"2026-01-01","to":"2026-04-30"}
SONRASI: {"from":"2026-01-06","to":"2026-04-25"}
```

Görünür aralık DEĞİŞTİ — zoom tamamen çalışıyor. Kod-kanıtı: `EventOverlayLayer`
hiçbir yerde `chart.applyOptions` ile etkileşimi kısıtlamıyor, yalnızca
`createSeriesMarkers`/`subscribeClick` (resmi, ek-katman API'leri)
kullanıyor — mevcut render akışının "altını bilmeden üstüne biner"
ilkesi kod düzeyinde de sağlanmış durumda.

## FAZ 4 kontrol listesi taranırken bulunan üçüncü hata

Bölüm 3 döngüsü FAZ 4'e geçerken de devam etti: "geçersiz olay
şeması→düşürülür+loglanır (çökme yok)" maddesi kontrol edilirken,
normalize fonksiyonlarının TEK bir bozuk kaydı (örn. eksik
`transaction_date`) `.map()` içinde fırlatırsa TÜM kaynağın olaylarını
götürdüğü bulundu (bkz. `HATA_HAFIZASI_koyfin.md` H-004). `guvenliMap()`
eklenerek düzeltildi: her kayıt ayrı denenir, bozuk olan `console.warn`
ile loglanıp DÜŞÜRÜLÜR, diğerleri ETKİLENMEZ. Regresyon testi:
`OLAY/GECERSIZ-SEMA` (23. test).

## Çıkış kararı

3 şüphecilik maddesinin 3'ü de kanıtla PASS + yol boyunca 1 ek gerçek
hata bulundu/düzeltildi. **FAZ 4'e (test/regresyon) geçiliyor** —
zaten 23 test yazılmış durumda, bu fazda yalnızca FAZ 4'ün resmi
kontrol listesiyle eşleme yapılıp eksikler (bu belgede: idempotentlik,
geçersiz şema) kapatıldı.
