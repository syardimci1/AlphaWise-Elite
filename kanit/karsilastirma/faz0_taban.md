# FAZ 0 — TABAN ÇİZGİSİ (karşılaştırma modu)

**Tarih:** 25.09.2026 · **Dal:** `claude/grafik-terminal-comparison-iaz3s1` · **Taban commit:** `f827ca7` (= `origin/main`)

## 0.1 Okunan belgeler

| Belge | Durum |
|---|---|
| `CLAUDE.md` | okundu — korunan dosyalar: `maa/src/cascade.py`, `maa/src/main.py`, `maa/src/llmquant_client.py` |
| `KALICILIK_SONUC.md` | okundu — ADR-5 deseni (tür+kullanıcı+sembol başına anahtar, 300 ms debounce, yankı kapısı, sıfırlama) bu işin kalıcılık dayanağı |
| `contracts/grafik/ADR.md`, `contracts/grafik/kalicilik_sozlesmesi.md` | okundu |
| `HATA_HAFIZASI_grafik.md` | okundu — H-1 (ad alanı kapısı anahtarın tamamı olmalı), H-5 (yankı yazımı) bu işte baştan uygulanır |
| `GRAFIK_TERMINALI_SONUC.md`, `GRAFIK_DEFTERI.md` | **YOK** — `find . -iname "GRAFIK*"` yalnızca `frontend/components/GrafikTerminali.tsx` buldu (pozitif kontrol). Kalıcılık işi de aynı yokluğu kaydetmişti (`kanit/kalicilik/faz0_taban.md`). |
| `contracts/grafik/` içinde C6 karşılaştırma modu tanımı | **YOK** — sözleşme bu işte yazıldı: `contracts/grafik/karsilastirma_modu.md` |

## 0.2 Ölçümler

### Testler

| Paket | Test | Geçen | Kalan |
|---|---|---|---|
| `node --test tests/*.test.mjs` | 114 | 114 | 0 |
| `node --import tsx --test tests/*/*.test.ts` | 369 | 368 | **1** |

Başarısız olan (ÖNCEDEN VAR, grafikle ilgisiz): `UC: admin PDF INDIREBILIR (regresyon yok)`
(`tests/kiracilik/raporlar-rol.test.ts`) — kalıcılık işinin tabanında da aynıydı.

### Tip denetimi (`npx tsc --noEmit -p .`)

2 hata, ikisi de önceden var, ikisi de grafik dışı:
`tests/kiracilik/raporlar-rol.test.ts(164,30)` TS2307 · `tests/koyfin/marker.test.ts(88,55)` TS2345.

### Bundle (`npx next build`)

| Ölçü | Değer |
|---|---|
| Next tablosu | `/dashboard` 88.5 kB · First Load JS **233 kB** |
| `kanit/karsilastirma/bundle_olc.mjs` (7 JS dosyası) | ham **787 988 B** · gzip-9 **232 628 B** |

Build `tsconfig.json`'u değiştirip `next-env.d.ts` üretiyor (bilinen davranış) — geri alındı.

### Korunan dosyalar (`git hash-object`)

```
1c9f41cf0fcc1949935a50042883ec5274351f6b  maa/src/cascade.py
1a9fc06d5558d9806f5ccc07ada77d1c767c853a  maa/src/main.py
98f9841c54ae51ed324bc05f97776571ba2fae13  maa/src/llmquant_client.py
```

## 0.3 Çakışma

`git status --porcelain` → **temiz**; dal `origin/main` ile aynı commit'te. Başka oturumun commit'lenmemiş
kodu bu çalışma kopyasında yok, izole worktree gerekmedi.
`frontend/src/app/dashboard/page.tsx` (Watchlist Sezon 2 çakışma riski) bu işte **hiç değiştirilmedi**:
karşılaştırma modu `GrafikTerminali` bileşeninin içinde kalır, sayfanın ona geçtiği prop'lar aynı.
