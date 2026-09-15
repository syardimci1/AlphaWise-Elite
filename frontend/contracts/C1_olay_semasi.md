# C1 — Olay Şeması (Event)

İmza tarihi: FAZ 1 (bkz. `kaynak_haritasi.md` — 4 kaynağın canlı örnekleriyle doğrulandı).

```ts
interface KoyfinOlay {
  id: string;                 // deterministik hash — kaynak kalici id vermiyor
  tip: '13F' | 'DARK_POOL' | 'CONGRESS' | 'INSIDER';
  symbol: string;              // buyuk harf ticker
  ts_utc: number;               // ISO-8601 UTC -> ms epoch (gercek olay tarihi)
  kaynak: string;               // orn. "congress_trading:fmp", "sec_edgar_13f_direct"
  ozet: string;                 // tek satirlik insan-okunur ozet (tooltip basligi)
  detay_url?: string | null;    // varsa kamu kaynagi linki (bkz. kaynak_haritasi.md — 2/4 kaynakta yok)
  ham_veri_ref: Record<string, unknown>; // kaynak servisin dondurdugu HAM satir (degistirilmeden)
  confidence: number;           // [0,1] — veri guvenilirlik/tamlik skoru (dogruluk TAHMINI degil)
  kaynak_zamani_utc: number;    // olayin RESMEN ACIKLANDIGI/DOSYALANDIGI tarih (ts_utc'den FARKLI olabilir)
}
```

## Alan kararları

- **`ts_utc` vs `kaynak_zamani_utc` ayrımı ZORUNLU:** kaynak_haritasi.md'de
  4 kaynaktan 3'ünde (congress, insider, 13F) bu iki tarih CANLI veride
  farklı çıktı (STOCK Act ~45 gün, 13F ~45 gün, Form4 medyan 2 iş günü
  gecikme). Tek bir zaman alanı olsaydı hangi tarihin kastedildiği
  belirsiz kalırdı.
- **`confidence` bir OLASILIK DEĞİL, bir VERİ TAMLIK skorudur** — "bu
  işlem karlı mıydı" gibi bir tahmin taşımaz, yalnızca kaynağın kendi
  verisinin ne kadar doğrulanmış/tam olduğunu taşır (örn. 13F'te
  cusip_dogrulandi=false → 0.7; insider'da hibe/ödül kaydı → 0.6).
- **`id` deterministik türetilir** (kaynak alanlarının hash'i) —
  aynı olayın iki kez çekilmesi (önbellek/yenileme) AYNI id'yi
  üretmeli (bkz. C3 idempotentlik, FAZ 4 test 9).
- **`ham_veri_ref` hiç dönüştürülmeden saklanır** — normalize sırasında
  kaybolan bir alana ihtiyaç duyulursa (debug, gelecekte yeni bir görsel
  ihtiyaç) kaynağa geri dönmeye gerek kalmaz.
