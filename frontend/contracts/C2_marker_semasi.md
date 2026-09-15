# C2 — Marker Şeması

FAZ 1'de canlı doğrulandı: `lightweight-charts` v5'in `createSeriesMarkers()`
API'si `{time, position, shape, color, text}` alan adlarını GERÇEKTEN
bekliyor (bkz. `bench/faz1_canli_kanit.md` ekran görüntüsü kanıtı).

```ts
interface KoyfinMarker {
  event_id: string;       // C1.id ile birebir eslenir (tooltip'te C1'e geri donus icin)
  x_ts_utc: number;       // C1.kaynak_zamani_utc'den turetilir (V-002 COZULDU: piyasa olayi ACIKLANDIGI an "gorur", ts_utc DEGIL)
  y_fiyat: number | null; // o tarihteki candle'in HIGH'i (aboveBar) - candle yoksa null -> marker atlanir
  renk_tipi: '13F' | 'DARK_POOL' | 'CONGRESS' | 'INSIDER'; // C2 kendi renk paletini tip'ten turetir, C1.kaynak'i degil
  ikon_tipi: 'arrowUp' | 'arrowDown' | 'circle' | 'square'; // lightweight-charts'in SeriesMarkerShape kumesiyle SINIRLI
  tooltip_ref: string;     // event_id ile ayni - tooltip komponenti C1'i event_id'den cozer
}
```

## TEK KURAL (Zaman Sözleşmesi C4 ile bağlı)

`x_ts_utc` HER ZAMAN UTC ms epoch'tur. Kullanıcıya gösterilecek yerel
saat dönüşümü marker şemasının İÇİNDE YAPILMAZ — yalnızca render katmanının
en dış noktasında, tek bir `utcToLocal()` fonksiyonu üzerinden (bkz. C4).
Bu, marker şemasını test edilebilir ve saf (pure) tutar.

## Renk/ikon eşleme kararı (VARSAYIM V-006, VARSAYIM_DEFTERI'nde işaretli)

| tip | ikon | renk | gerekçe |
|---|---|---|---|
| CONGRESS | `arrowDown`/`arrowUp` (satış/alış) | `#e63946` (kırmızı) | FAZ 1 canlı testte satış için arrowDown doğrulandı |
| INSIDER | `arrowDown`/`arrowUp` | `#f4a261` (turuncu) | congress ile aynı yön mantığı, farklı renk — karıştırılmamalı |
| 13F | `circle` | `#457b9d` (mavi) | yön taşımaz (pozisyon açıklaması, alım/satım değil) |
| DARK_POOL | `square` | `#6a4c93` (mor) | eşik-aşımı olayı, yön taşımaz |

Bu tablo bir TASARIM VARSAYIMIDIR, kullanıcı testiyle değişebilir —
VARSAYIM_DEFTERI_koyfin.md V-006'da yanlışlanma koşuluyla kayıtlı.
