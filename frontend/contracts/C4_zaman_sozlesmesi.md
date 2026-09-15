# C4 — Zaman Sözleşmesi

**Tek kural:** İç temsilin TAMAMI (C1.ts_utc, C1.kaynak_zamani_utc,
C2.x_ts_utc) UTC ms epoch (`number`, `Date.UTC(...)` çıktısı) olarak
tutulur. Yerel saat dönüşümü YALNIZCA görüntüleme anında, TEK bir
fonksiyonda yapılır:

```ts
// src/lib/koyfin-zaman.ts (FAZ 2'de yazilacak, C4'un TEK uygulamasi)
export function utcToLocalLabel(ts_utc: number, locale = 'tr-TR'): string {
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric', month: '2-digit', day: '2-digit',
    timeZone: undefined, // TARAYICININ KENDI TZ'SI - kullanicidan sorulmaz
  }).format(new Date(ts_utc))
}
```

## Neden bu kadar katı

`kaynak_haritasi.md`'de görüldüğü gibi kaynak veri gün-hassasiyetinde
tarih string'i döndürüyor (`"2026-09-03"`, saat/TZ bilgisi YOK). Bu
string'ler `Date.UTC(yil, ay-1, gun)` ile **UTC gece yarısı** olarak
parse edilecek — yerel saat diliminde parse edilirse (örn. tarayıcı
`new Date("2026-09-03")` çağrısı bazı motorlarda yerel TZ varsayar)
sınır günlerinde (özellikle UTC-X bölgelerinde) marker BİR GÜN KAYAR.
Bu, FAZ 3 şüphecilik turunun birinci maddesidir ("Marker doğru tarihte
mi — sınır TZ dahil") ve mutasyon testiyle kilitlenecek (FAZ 4 test 1).

## Candle zamanıyla hizalama

`PriceChart.tsx`'teki candle `time` alanı da aynı `"YYYY-MM-DD"`
string formatını taşıyor (`lightweight-charts`'ın "business day" zaman
tipi) — yani marker `time` alanı da AYNI string formatıyla (epoch
DEĞİL) `createSeriesMarkers`'a verilmeli. `x_ts_utc` (epoch) yalnızca
iç mantık/test için tutulur; kütüphaneye verilirken
`utcMsToBusinessDayString(x_ts_utc)` ile geri string'e çevrilir — bu
da C4'ün TEK sorumluluk alanına dahildir (tek fonksiyon, tek yer).
