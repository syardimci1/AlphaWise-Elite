# FAZ 1 — KEŞİF: kalıcılık bugün nerede var, nerede yok

**Tarih:** 24.09.2026 · **Taban:** `977bd07`

## 1. Çizimler (C3 / ADR-2) — VAR, bağlı, test edilmiş

| Parça | Kanıt |
|---|---|
| Saf modül | `frontend/src/lib/grafik/cizim-kalicilik.ts` — `anahtarUret` (`:47`), `kaydet` (`:102`), `yukle` (`:124`), `sil` (`:163`) |
| Anahtar | `alphawise:grafik:cizim:v1:<kimlik>:<SEMBOL>`, parçalar `encodeURIComponent` ile kaçışlı (`:33-41`) |
| Şema | `{v:1, cizimler:[...]}`; v0 düz dizi göç edilir, bilinmeyen sürüm sıfırlanır + uyarı (`:146-160`) |
| Test | `tests/grafik/cizim-kalicilik.test.ts` — 18 test, hepsi geçiyor |
| Bileşen bağlantısı | `components/GrafikTerminali.tsx:356-371` yükleme, `:375-388` kaydetme |

### Bulunan kusurlar (bileşen bağlantısında, modülde değil)

**H-1 — kullanıcı değişiminde ad alanı sızıntısı (Y7).**
Kaydetme efektinin kapısı yalnızca sembolü karşılaştırıyor (`GrafikTerminali.tsx:376`:
`yuklenenSembol !== symbol`). Aynı sembolde `etkinKimlik` A→B değişirse, aynı commit'te önce yükleme
efekti (`:356`) B'nin çizimlerini `cizimGonder` ile KUYRUĞA koyar, ardından kaydetme efekti (`:375`) hâlâ
A'nın çizimlerini tutan `cizimDurum.cizimler` ile çalışır ve onları **B'nin anahtarına yazar**
(React, bir efektte verilen state güncellemesini aynı commit'teki sonraki efektlere göstermez).
Bugün tetiklenebilirliği: `dashboard/page.tsx:420` kimlik prop'u geçmiyor ve çekilen kimlik yalnızca
`null → kimlik` geçişi yapıyor (o geçişte `yuklenenSembol` henüz `null` olduğu için kapı tutuyor).
Yani **şu an gizli**, ama `kullaniciKimligi` prop'u değişen ilk çağıranla gerçek bir kiracı sızıntısına dönüşür.
Düzeltme maliyeti küçük: kapı, sembol yerine yüklenen **ad alanının tamamını** (kimlik+sembol) karşılaştırmalı.

**H-2 — her değişiklikte senkron yazma (Y10).** `:382` her çizim değişikliğinde (geri al/yinele dahil)
`JSON.stringify` + `localStorage.setItem`'ı ana thread'de, render sonrası hemen çalıştırıyor. Debounce yok.

**H-3 — sekmeler arası sessiz üzerine yazma (Y8).** `storage` olayı dinlenmiyor. İki sekme aynı sembolü
açıkken, birinin kaydettiği çizim diğerinin bir sonraki kaydıyla uyarısız siliniyor.

## 2. Göstergeler — kalıcılık YOK

| Kanıt | Anlamı |
|---|---|
| `terminal-durum.ts:43` `gostergeler: GostergeKimlik[]` | seçim yalnızca `TerminalDurum` içinde |
| `terminal-durum.ts:174` `bosTerminalDurum()` → `gostergeler: []` | her mount boş başlıyor |
| `GrafikTerminali.tsx:156` `useState<TerminalDurum>(bosTerminalDurum)` | React belleği; sayfa yenilenince gider |
| `command grep -rn "kaydet\|yukle(\|localStorage" components src` | göstergeler için hiçbir depo çağrısı yok; tek kalıcılık çağrıları çizimlere ait (`:367`, `:382`) |
| `gosterge-tanim.ts:182` | `gostergeKimlikMi` "seçili gösterge listesi localStorage'dan gelir" diye yorumlanmış — kapı hazır, bağlantı hiç yapılmamış |

**Neden eksik:** ADR-2 yalnızca çizimleri kapsıyor; gösterge seçimi için ne anahtar ne şema tanımlandı.

## 3. Gösterge "parametreleri" — ne kalıcı olabilir?

`gosterge-tanim.ts:20`: `GostergeKimlik = 'sma20' | 'sma50' | 'ema20' | 'bollinger20' | 'rsi14' | 'macd'`.
Periyot kimliğin içinde sabit, renk tanımda sabit (`renkler`), arayüzde periyot/renk düzenleyici **yok**.
Kullanıcının değiştirebildiği tek şey **görünürlük** (hangi ön-ayarların açık olduğu).
→ Kalıcı olacak: açık gösterge kimliklerinin listesi. Periyot ve renk kimlikten türediği için ayrıca saklanmaz;
saklamak, düzenlenemeyen sabitleri kopyalamak olurdu.

## 4. VWAP

ADR-3: **kapsam dışı** (gün içi veri yok; günlük barla VWAP yanlış sayıyı doğru isimle sunmak olurdu).
Terminalde VWAP göstergesi yok → kalıcılaştırılacak bir VWAP durumu da yok. Bu iş VWAP eklemez.

## 5. Çizim araçları

`terminal-durum.ts:83-92`: trend, yatay, dikey, dikdörtgen, fib, metin, ölçüm — 7 araç. Hepsi `Cizim`
şemasına düşer ve C3 ile zaten kalıcıdır; istemde sayılan beş araç (trend, Fibonacci, dikdörtgen, metin, ölçüm)
bunların alt kümesi.

## 6. Test altyapısı kısıtı

jsdom yok, bileşen render edilemiyor (`GrafikTerminali.tsx:6-8`). Karar mantığı saf modüllere konup
`node:test` ile sınanacak; bileşenin kendisi için gerçek tarayıcıda (önceden kurulu Chromium) bir uçtan uca
koşum yapılacak ve kanıt olarak raporlanacak.
