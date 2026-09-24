# FAZ 0 — TABAN ÇİZGİSİ (gösterge ve çizim kalıcılığı)

**Tarih:** 24.09.2026 · **Dal:** `claude/trusting-pasteur-yfsq5d` · **Taban commit:** `977bd07` (origin/main)

## 0.1 Okunan belgeler

| Belge | Durum |
|---|---|
| `CLAUDE.md` | okundu — korunan dosyalar: `maa/src/cascade.py`, `maa/src/main.py`, `maa/src/llmquant_client.py` |
| `contracts/grafik/ADR.md` | okundu — ADR-2 (C3 çizim kalıcılığı) bu işin dayanağı |
| `kanit/grafik/faz1_kesif.md` | okundu |
| `GRAFIK_DEFTERI.md`, `GRAFIK_TERMINALI_SONUC.md`, `HATA_HAFIZASI_grafik.md`, `VARSAYIM_DEFTERI_grafik.md` | **YOK** — depo kökünde ve alt dizinlerde `find` ile arandı, pozitif kontrol (`contracts/grafik/ADR.md` bulundu) başarılı. Eşdeğer bilgi doğrudan koddan çıkarıldı (FAZ 1). |
| `contracts/grafik/*.md` | yalnızca `ADR.md` var; ayrı bir "C3 sözleşmesi" dosyası yok, C3 ADR-2 içinde tanımlı |

## 0.2 Ölçümler

### Testler (`npm test` = `node --test tests/*.test.mjs && node --import tsx --test tests/*/*.test.ts`)

| Paket | Test | Geçen | Kalan |
|---|---|---|---|
| `.mjs` | 110 | 110 | 0 |
| `.ts` | 327 | 326 | **1** |

Başarısız olan (ÖNCEDEN VAR, grafikle ilgisiz): `UC: admin PDF INDIREBILIR (regresyon yok)` —
`tests/kiracilik/raporlar-rol.test.ts:145`, `404 !== 200` (rapor dosyası bu ortamda diskte yok).

### Tip denetimi (`npx tsc --noEmit -p .`)

**2 hata, ikisi de önceden var, ikisi de grafik dışı:**
- `tests/kiracilik/raporlar-rol.test.ts(164,30)` TS2307
- `tests/koyfin/marker.test.ts(88,55)` TS2345

`grafik` geçen hata satırı: **0**.

### Bundle (`next build`, `/dashboard`)

| Ölçü | Değer |
|---|---|
| Next tablosu | `/dashboard` 86.8 kB · First Load JS **231 kB** |
| Kendi ölçümüm (7 JS dosyası, `app-build-manifest.json`) | ham **781 857 B** · gzip-9 **230 869 B** |

Not: gzip toplamı (230.9 kB) Next tablosundaki 231 kB ile örtüşüyor → tablo rakamı **gzip**tir
(ADR risk kaydındaki V-009 belirsizliği bu ölçümle kapanıyor). Ölçüm betiği: `app-build-manifest.json`'daki
`/dashboard/page` JS dosyalarının `zlib.gzipSync(level 9)` toplamı.

Build `tsconfig.json`'u değiştirip `next-env.d.ts` üretiyor (ADR T4, bilinen davranış) — geri alındı.

### Korunan dosyalar (`git hash-object`)

```
1c9f41cf0fcc1949935a50042883ec5274351f6b  maa/src/cascade.py
1a9fc06d5558d9806f5ccc07ada77d1c767c853a  maa/src/main.py
98f9841c54ae51ed324bc05f97776571ba2fae13  maa/src/llmquant_client.py
```

## 0.3 Çakışma

`git status --porcelain` → temiz (build artıkları geri alındıktan sonra). Çalışma dalı `origin/main`'den açıldı.

## 0.4 Araç tuzağı

Aramalar `command grep -r` / `find` ile yapıldı; pozitif kontrol olarak bilinen dosya (`cizim-kalicilik.ts`) her aramada bulundu.

## Not — oturumun açıldığı depo

Bu oturum `syardimci1/godmode-paper-trading-service` deposunda başlatıldı. O depoda grafik terminali,
`EventOverlayLayer.tsx`, çizim reducer'ı, `contracts/grafik/` ve herhangi bir `localStorage` kullanımı
**tüm git geçmişinde (71 commit, tüm dallar) yok**. Grafik terminali bu depoda (`AlphaWise-Elite`) bulundu;
iş burada yapıldı.
