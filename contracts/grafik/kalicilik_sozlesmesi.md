# KALICILIK SÖZLEŞMESİ — gösterge ve çizim (grafik terminali)

**Tarih:** 24.09.2026 · **Dayanak:** ADR-2 (çizim kalıcılığı), ADR-5 (bu sözleşme) · **Keşif:** `kanit/kalicilik/faz1_kesif.md`

## C1 — Kapsam

| Veri | Kalıcı mı | Not |
|---|---|---|
| Açık göstergeler: `sma20`, `sma50`, `ema20`, `bollinger20`, `rsi14`, `macd` | **EVET** | kullanıcının değiştirebildiği tek gösterge parametresi görünürlüktür |
| Gösterge periyodu / rengi | hayır | kimlikte ve `GOSTERGE_TANIMLARI`'nda sabit; arayüzde düzenleyici yok |
| VWAP | hayır | terminalde yok (ADR-3, gün içi veri yok) |
| Çizimler: trend, yatay, dikey, dikdörtgen, fib, metin, ölçüm | **EVET** (ADR-2, değişmedi) | `Cizim` şeması `cizim-model.ts` otoritesinde |
| Zaman dilimi, seçili araç, yarım çizim noktaları, seçili çizim, geri al yığını | hayır | oturum içi etkileşim durumu; istenmedi |

## C2 — Anahtar şeması

Tek ad alanı fonksiyonu (`adAlaniAnahtari`, `cizim-kalicilik.ts`) iki türe de hizmet eder:

```
alphawise:grafik:cizim:v1:<kimlik>:<SEMBOL>      (ADR-2, değişmedi)
alphawise:grafik:gosterge:v1:<kimlik>:<SEMBOL>   (yeni)
```

- `<kimlik>` ve `<SEMBOL>` `encodeURIComponent` ile kaçışlanır (ayraç enjeksiyonu → ad alanı çakışması yok).
- Sembol `toUpperCase()` (yerelden bağımsız) ile normalize edilir.
- Bileşen kimlik olmadan **ne okur ne yazar** (kimlik uydurulmaz; `anonim` ad alanı modülde var ama bileşen kullanmaz).

## C3 — Veri şekli

```jsonc
// gösterge anahtarı
{ "v": 1, "gostergeler": ["sma20", "rsi14"], "guncelleme_utc": 1758700000000 }
// çizim anahtarı (ADR-2, değişmedi)
{ "v": 1, "cizimler": [ /* Cizim */ ] }
```

`guncelleme_utc` bilgi amaçlıdır; okurken doğrulanmaz (eksikse kayıt yine geçerlidir).
`gostergeler` okurken kanonik sıraya dizilir, tekrarlar ve bilinmeyen kimlikler ayıklanır (sayısı uyarıya yazılır).

## C4 — Göç stratejisi

| Okunan | Sonuç | Kullanıcıya |
|---|---|---|
| anahtar yok | boş seçim | uyarı yok |
| `{v:1, gostergeler:[...]}` | yüklenir | bilinmeyen kimlik varsa "N gösterge tanınmadığı için atlandı" |
| düz dizi (v0) | göç edilir | "eski sürüm (v0) göç edildi" |
| başka `v` | sıfırlanır | "bilinmeyen sürüm (v=X) sıfırlandı" |
| bozuk JSON / eksik `gostergeler` | sıfırlanır | "bozuk kayıt sıfırlandı" |
| depo okunamıyor | boş seçim, uygulama çalışır | "depo okunamadı: …" |

Uyarılar terminalin not satırında "Kayıtlı göstergeler: …" / "Kayıtlı çizimler: …" önekiyle görünür.
`yukle` **yan etkisizdir**; bozuk kaydın üzerine bir sonraki kayıt yazar.

## C5 — Yazma stratejisi

- Her anahtar için **300 ms** debounce (`KAYIT_GECIKMESI_MS`). Aynı anahtara pencere içinde gelen
  yazımlar tek yazıma iner; farklı anahtarlar (başka sembol, başka tür) birbirini iptal etmez.
- **Veri kaybı kapıları:** bekleyen yazımlar `pagehide`, `visibilitychange→hidden` ve bileşen
  kaldırılırken **anında boşaltılır**. Sembol değişiminde eski sembolün bekleyen yazımı kendi
  (eski) anahtarına gider — yazım anındaki anahtar ve veri kapanışta yakalanır.
- Gerekçe ve ölçüm: `KALICILIK_SONUC.md` §Performans.

## C6 — Sıfırlama

- "Kayıtlı ayarları sıfırla" düğmesi: yerel `<button>` (Tab ile odaklanır, Enter/Space ile çalışır),
  `aria-label` taşır, `window.confirm` ile onay ister.
- Kapsam: **o anki kullanıcı + o anki sembol**, iki anahtar birden. Bekleyen yazımlar önce iptal edilir
  (aksi halde silinen kayıt 300 ms sonra geri yazılırdı), sonra iki anahtar silinir, gösterge seçimi ve
  çizim belgesi boşaltılır.

## Sekmeler arası

Başka bir sekme aynı ad alanına yazarsa (`storage` olayı) not satırında uyarı gösterilir; bu sekmedeki
bir sonraki değişiklik onun üzerine yazacaktır (son yazan kazanır). Otomatik birleştirme yapılmaz
(ADR-5, alternatif C).
