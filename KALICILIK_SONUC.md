# KALICILIK SONUÇ — gösterge ve çizim kalıcılığı (grafik terminali)

**Tarih:** 24.09.2026 · **Dal:** `claude/trusting-pasteur-yfsq5d` · **Taban:** `977bd07`
Sözleşme: `contracts/grafik/kalicilik_sozlesmesi.md` · ADR-5: `contracts/grafik/ADR.md` · Kanıt: `kanit/kalicilik/`

## Önce / sonra

| | Önce | Sonra |
|---|---|---|
| Açık göstergeler | yalnızca React belleği, yenilemede kaybolur (`terminal-durum.ts:43,174`) | `alphawise:grafik:gosterge:v1:<kimlik>:<SEMBOL>`, yenilemede/sembol dönüşünde geri gelir |
| Çizimler | kalıcı (ADR-2) | kalıcı; 2 sızıntı/kayıp kusuru kapatıldı (H-1, H-4) |
| Yazma | her değişiklikte senkron | anahtar başına 300 ms debounce; `pagehide`/gizlenme/kaldırmada boşaltma; yüklenen veri geri yazılmaz |
| Bozuk/eski kayıt (gösterge) | — | sıfırlama/göç + "Kayıtlı göstergeler: …" notu |
| Kota | teknik hata adı gösteriliyordu | "tarayıcı deposu dolu… sayfa yenilenirse kaybolur…" |
| Sıfırlama | yok | "Kayıtlı ayarları sıfırla" (onaylı, klavyeyle erişilebilir) |
| Sekmeler arası | sessiz üzerine yazma | görünür uyarı (son yazan kazanır) |

## Kanıt tablosu (Y13)

Birim testleri: `cd frontend && node --import tsx --test tests/grafik/*.test.ts`.
Uçtan uca: `kanit/kalicilik/e2e/kos.mjs` (gerçek Chromium 1194, gerçek `localStorage`), çıktı `kanit/kalicilik/faz5_e2e_cikti.txt` — **15 geçti, 0 kaldı**.

| Madde | Kanıt |
|---|---|
| S1 göstergeler yenilemede geri gelir | birim: `GOSTERGE KALICILIK: kaydet/yukle gidis-donusu…`, `GOSTERGELERI_YUKLE…` (3) · e2e **E1** |
| S1 sembol değişimi | birim: `…sembol basina ayri…` · e2e **E2** |
| S2 çizimler | e2e **E3**, **E11** (1000 çizim) · birim `KALICILIK (H-4)…` |
| Y7 tek cihaz iki hesap | birim: `GOSTERGE KALICILIK (Y7)…`, `…kacislanir…` · e2e **E4**, **E5**, **E5b** (yazım günlüğüyle, geçici sızıntı dahil) |
| S3 / C4 göç ve bozuk veri | birim: bozuk JSON, nesne olmayan JSON, eksik alan, bilinmeyen sürüm, v0 göçü, tanınmayan kimlik, okuma hatası, yan etkisizlik (8 test) · e2e **E6** |
| S4 / Y9 kota | birim: `(Y9)` 4 test + `kayitHataMetni (Y9)` · e2e **E7** — Chromium'un **kendi** `QuotaExceededError`'u, 19 × 256 KiB'da doldu |
| S5 / Y10 debounce | birim: `GECIKMELI KAYIT` 8 test · e2e **E9** (21 tıklama → **1** yazım), **E10** (pencere içi yenileme ve sekme kapanışı kayıpsız) |
| S6 / C6 / Y12 sıfırlama | birim: `SIFIRLAMA (C6)` 3 test · e2e **E12** (Tab sırası, Enter, onay/vazgeç, geri yazılmama, geri al kapalı) |
| Sekmeler arası | birim: `SEKMELER…` · e2e **E13** (3 sekme) |
| Gizli mod / depo kapalı | birim: `…depo okunamiyorsa (gizli mod)…` · e2e **E8** |
| Y8 hukuki dil (yeni metinler) | `Y8: bileşenin gösterdiği tüm sabit metinler…` — kapı "geri alınamaz" ifadesini yakaladı, metin "geri döndürülemez" yapıldı |

### Test sayıları

| Paket | Taban | Sonra |
|---|---|---|
| `.mjs` | 110/110 | 110/110 |
| `.ts` | 326/327 | **368/369** (+42 yeni test) |

Tek başarısız test **önceden var ve grafikle ilgisiz**: `UC: admin PDF INDIREBILIR` (`tests/kiracilik/raporlar-rol.test.ts:145`, `404 !== 200`).

### Mutasyon testi (`kanit/kalicilik/mutasyon.sh`, çıktı `faz5_mutasyon_cikti.txt`) — 8/8 öldü

| # | Mutasyon | Öldüren |
|---|---|---|
| M1 | debounce kaldırıldı | birim, 5 test |
| M2 | şema sürüm kontrolü bozuldu | birim, 1 test |
| M3 | ad alanı anahtarı sabitlendi (kimlik yok sayılır) | birim, 10 test |
| M4 | H-1 kapısı geri alındı | e2e **E5b** — *ilk turda HAYATTA kaldı* (debounce sızan yazımı gizliyordu); E5b eklenerek öldürüldü |
| M5 | yankı kapısı kaldırıldı | e2e E11 |
| M6 | sıfırlamada bekleyen yazım iptali kaldırıldı | birim, 1 test |
| M7 | boşaltma kaldırıldı | birim, 2 test |
| M8 | kota tanıma bozuldu | birim, 3 test |

### Tip denetimi, bundle, korunan dosyalar

- `npx tsc --noEmit`: **2 hata, ikisi de tabandaki** (`raporlar-rol.test.ts:164`, `koyfin/marker.test.ts:88`); yeni hata 0.
- `/dashboard` JS (7 dosya): ham 781 857 → 787 780 B (**+5 923**), gzip-9 230 869 → 232 591 B (**+1 722, %0,75**). Next tablosu 231 → 233 kB.
  Next tablosundaki rakamın **gzip** olduğu bu ölçümle doğrulandı (ADR risk kaydı V-009).
- Korunan dosyalar önce/sonra aynı:
  `1c9f41cf… maa/src/cascade.py`, `1a9fc06d… maa/src/main.py`, `98f9841c… maa/src/llmquant_client.py`.
- Karar yolu (Y4): değişen dosyalar yalnızca `frontend/components/GrafikTerminali.tsx`, `frontend/src/lib/grafik/*`, `frontend/tests/grafik/*`,
  `contracts/grafik/*`, `kanit/kalicilik/*`, `HATA_HAFIZASI_grafik.md`, bu dosya.

## Performans (C5 / Y10)

Gerçek Chromium, `JSON.stringify + localStorage.setItem`, 200 tekrar (P1; `performance.now` çözünürlüğü 0,1 ms):

| Yük | Karakter | p50 | p95 | azami |
|---|---|---|---|---|
| gösterge (6 açık) | 95 | 0,0 ms | 0,1 ms | 0,2 ms |
| 100 çizim | 19 370 | 0,1 ms | 0,2 ms | 2,6 ms |
| 1000 çizim | 194 510 | 2,4 ms | **6,0 ms** | 23,1 ms |
| 5000 çizim | 976 910 | 15,2 ms | **25,7 ms** | 39,4 ms |

Hedef "p95 ≤ 50 ms" 5000 çizimde bile sağlanıyor. **300 ms gerekçesi:** tek yazım ucuz; sorun art arda gelen yazım patlamaları
(E9: 21 tıklama → debounce öncesi 21, sonrası 1 yazım). 300 ms ardışık insan tıklamalarını kapsar; debounce'un kayıp penceresi
`pagehide` + `visibilitychange→hidden` + kaldırmada boşaltmayla kapatıldı (E10). Yazım `localStorage`'ın doğası gereği hâlâ
ana thread'de ve senkron; ölçülen en kötü durum (5000 çizimde azami 39,4 ms) 50 ms uzun-görev eşiğinin altında.

**Ölçülen sınırlar (Y14):** Chromium kotası ≈ 5 M karakter (19 × 256 KiB'da doldu). 1000 çizim ≈ 195 K karakter → tek sembolde
≈ 25 000 çizim kotayı doldurur. Kota dolunca uygulama çalışmaya devam eder, E7'deki uyarı görünür.

## Bulunan hatalar

| # | Özet | Durum |
|---|---|---|
| H-1 | Aynı sembolde kullanıcı A→B değişiminde A'nın çizimleri B'nin anahtarına yazılıyordu (gerçek Chromium'da ölçüldü) | düzeltildi, E5/E5b |
| H-4 | Yinelenen çizim kimliği → kayıt reducer'da bütünüyle reddedilip önceki sembolün çizimleri yeni sembole yazılıyordu | düzeltildi, birim test |
| H-5 | Debounce eklenince yüklenen verinin "yankı" yazımı 300 ms içinde başka sekmenin yeni kaydını eziyordu | düzeltildi, E11/M5 |
| H-2, H-3 | Senkron yazım; sekmeler arası sessiz üzerine yazma (FAZ 1) | S5 ve S6 ile giderildi |

Ayrıntı ve 5 Neden: `HATA_HAFIZASI_grafik.md`.

## Kararlar (soru sorulmadı, gerekçeyle)

1. **Depo:** oturum `godmode-paper-trading-service` deposunda açıldı; orada grafik terminali, `EventOverlayLayer.tsx`, çizim reducer'ı,
   `contracts/grafik/` ve `localStorage` kullanımı tüm geçmişte yok. Terminal bu depoda (`AlphaWise-Elite`) bulundu, iş burada yapıldı.
2. **Veri şekli:** istemdeki kullanıcı başına tek blob (`{v, semboller:{…}}`) yerine tür+kullanıcı+sembol başına ayrı anahtar (ADR-5):
   mevcut çizim kayıtları göç gerektirmez, farklı sembollerdeki sekmeler çakışmaz, yazım maliyeti tek sembolle sınırlı.
3. **Gösterge seçimi sembole aittir:** kaydı olmayan bir sembol boş seçimle açılır. **Davranış değişikliği:** eskiden oturum boyunca açık
   göstergeler sembol değişince de açık kalıyordu. İstemdeki "kullanıcı + sembol ad alanı" bunu gerektiriyor. Depo kapalıyken
   (gizli mod) eski davranış korunur: seçim sembolden sembole taşınır.
4. **Gösterge parametreleri:** yalnızca görünürlük kalıcı; periyot/renk kimlikte ve tanımda sabit, düzenleyici yok (C1).
5. **VWAP:** terminalde yok (ADR-3, gün içi veri yok) → kalıcılaştırılacak VWAP durumu da yok.
6. **Sekmeler arası:** otomatik yeniden yükleme yerine görünür uyarı (ping-pong riski yok, kayıp sessiz değil).
7. **Ayrı kalıcılık bayrağı eklenmedi (Y11):** terminal bayrağı kapalıyken hiçbir depo erişimi yok; kaydı olmayan kullanıcı için varsayılan
   görünüm değişmedi; sıfırlama, kalıcılık öncesi hale dönüşü sağlar.

## Yapılmayanlar / sınırlar (açıkça)

- **Bileşen `node:test` ile render edilemiyor** (jsdom yok, eklenmedi). Bileşen davranışı gerçek Chromium'da sınandı; düzenek
  `playwright-core`'u **projeye eklemeden** geçici bir dizinden kullanır (çalıştırma talimatı `kos.mjs` başında). Fiyat barları deterministik
  bir test fikstürüdür (piyasa verisi değildir); ağ uçları sahte. Gerçek Next sunucusu + middleware + gerçek veriyle uçtan uca koşum **YAPILMADI**.
- Sıfırlama yalnızca **o anki sembol** için; "tüm semboller" sıfırlaması yok (anahtar taraması gerektirir, istenmedi).
- Sekmeler arası birleştirme yok: aynı sembolde iki sekme → son yazan kazanır (uyarıyla).
- Eski anahtarların temizlenmesi/tahliyesi yok: kullanıcının değiştirdiği her sembol bir anahtar bırakır (gösterge kaydı ~95 karakter).
- Kota hatası sonrası yazım otomatik yeniden denenmez; bir sonraki değişiklik yeniden dener (E7).
- S3 ve S4 aynı dosyalarda iç içe olduğu için **tek commit** (`833f38f`); diğer dilimler ayrı commit.
- `VARSAYIM_DEFTERI_grafik.md`, `GRAFIK_DEFTERI.md`, `GRAFIK_TERMINALI_SONUC.md` depoda yoktu; eşdeğer bilgi koddan çıkarıldı (`kanit/kalicilik/faz1_kesif.md`).
- **Gözlenen, dokunulmayan (önceden var):** depo kapalıyken çizim yükleme efekti erken döner; sembol değişince önceki sembolün çizimleri
  ekranda kalır (`GrafikTerminali.tsx`, yükleme efektinin `depo === null` dalı). Kaydedilmedikleri için veri karışmaz; yalnızca görünüm.
