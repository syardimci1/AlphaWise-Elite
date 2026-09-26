# KARŞILAŞTIRMA MODU SONUÇ — grafik terminali

**Tarih:** 25.09.2026 · **Dal:** `claude/grafik-terminal-comparison-iaz3s1` · **Taban:** `f827ca7` (= `origin/main`)
Sözleşme: `contracts/grafik/karsilastirma_modu.md` · ADR-6: `contracts/grafik/ADR.md` · Varsayımlar: `VARSAYIM_DEFTERI_karsilastirma.md` · Kanıt: `kanit/karsilastirma/`

## Ne yapıldı

Grafik terminaline (`GrafikTerminali.tsx`) **Tek sembol / Karşılaştırma** görünüm düğmeleri eklendi. Karşılaştırmada ana sembol +
en fazla 2 ek sembol, aynı grafikte **ortak bir taban gününe göre yüzde** olarak çizilir. Yeni bağımlılık, yeni API ucu yok;
`dashboard/page.tsx`, `PriceChart.tsx` ve korunan dosyalar değişmedi.

| Dosya | Rol |
|---|---|
| `frontend/src/lib/grafik/karsilastirma.ts` | SAF: seçim (ekle/çıkar/limit/renk yuvası/mod), hizalama + normalize, çizgi verisi, lejant, görünüm kararı, Y8 metinleri |
| `frontend/src/lib/grafik/karsilastirma-kalicilik.ts` | ADR-5 deseninin üçüncü türü (`alphawise:grafik:karsilastirma:v1:<kimlik>:<ANA_SEMBOL>`) |
| `frontend/components/KarsilastirmaGrafigi.tsx` | çoklu `LineSeries` + her zaman görünür lejant + imleç |
| `frontend/components/GrafikTerminali.tsx` | orkestrasyon: mod, sembol formu, veri çekme/önbellek, kalıcılık bağlantısı, mum grafiğini gizleme |
| `kalicilik-sifirlama.ts`, `terminal-durum.ts` | sıfırlama karşılaştırma kaydını da siler; onay/aria metinleri bunu söyler; kota metni |

## Sözleşme → kanıt (Y7, Y13)

Birim: `cd frontend && node --import tsx --test tests/grafik/karsilastirma-*.test.ts` (44 test).
Uçtan uca: `kanit/karsilastirma/e2e/kos.mjs` — gerçek Chromium 1194, gerçek `localStorage`, çıktı `faz5_e2e_cikti.txt` — **15 geçti, 0 kaldı**.

| Madde | Karar | Kanıt |
|---|---|---|
| C1 normalize | Taban = tüm serilerde geçerli kapanış olan **ilk ortak gün**; her seri o gün tam %0; taban öncesi dışarıda ve sayılır | birim 6 test (farklı başlangıç, kayan taban, ortak gün yok…) · e2e **K2** (3 seri tabanda `%0,00`), **K9** |
| C1 ölçek | 1000 kat farklı fiyat → aynı yüzdeler | birim · e2e **K12** (`+%3,74 = +%3,74` …) |
| C2 limit | 3 (ana + 2); 4. **reddedilir**, en eski çıkarılmaz; düğme devre dışı + neden | birim · e2e **K3** (TSLA için istek bile atılmadı) |
| C2 yinelenen/ana/geçersiz | reddedilir, neden `role=status` ile duyurulur | birim (istemci deseni = sunucu `tickerDogrula`, 15 girdi) · e2e **K4** |
| C3 renk/lejant | yuvaya bağlı doğrulanmış palet, eksen etiketinde sembol adı, grafiğin üstünde her zaman görünür lejant | `palet_dogrulama.txt` (tüm çiftler PASS) · birim · e2e **K7** (MSFT çıkınca NVDA rengini korudu) |
| C4 / Y9 boşluk | değer uydurulmaz (null); köprü segmenti saydam; lejantta sayı + tarihler; imleçte "veri yok" | birim · e2e **K5**: eksik gün sütununda turuncu piksel **0**, pozitif kontrol **5** |
| C5 kalıcılık | ADR-5'in aynısı: `adAlaniAnahtari`, 300 ms debounce, H-1 kapısı, H-5 yankı kapısı, sıfırlama, sekme uyarısı | birim 10 test · e2e **K7** (yenileme + B hesabı görmez), **K13** (sıfırlama), **K14** (sekme) |
| C6 mod geçişi | mum grafiği gizlenir, kaldırılmaz; liste tek modda korunur; veri önbellekte | e2e **K6**: yakınlaştırma + çizim + SMA 20 sonrası gidiş-dönüşte mum grafiği ekran görüntüsü **bayt bayt aynı**, MSFT yeniden çekilmedi · **K10** (Delete gizli çizimi silmez) |
| S6 tek seri | ek sembol yok / veri yok / hata / ortak gün yok → mum grafiğine düşer, neden yazılır | birim · e2e **K8**, **K9** |
| Y10 performans | hedef ≤ 1 sn | aşağıda |
| Y11 erişilebilirlik/mobil | yalnız klavyeyle tam akış; 390 px'te taşma yok; çıkar düğmesi 28×28 px | e2e **K1**, **K11** (`k11_390px.png`) |
| Y8 hukuki dil | tüm yeni metinler yasaklı kalıplardan geçer (+ karşılaştırmaya özgü "daha iyi/kazanan/önde/üstün" kalıbı) | birim `Y8: …` + kapının kendisinin testi |

### Y10 — gerçek Chromium, 5 tekrar (`K15`)

| Yük | tık → boyanmış kare (medyan / azami) | `setData` → kare (medyan / azami) |
|---|---|---|
| 3 sembol × 2 yıl (≈ 522 işlem günü) | 68,3 / **81,9 ms** | 16,3 / 22,3 ms |
| 3 sembol × 1500 bar (terminal üst sınırı) | 88,4 / **102,5 ms** | 20,3 / 22,9 ms |

Saf hizalama+normalize (3 × 504 gün) birim testinde ≤ 50 ms sınırıyla kilitli. Ağ süresi dahil DEĞİL (sahte uç; veri önbellekteyken geçiş ölçüldü).

### Test sayıları, mutasyon, tip denetimi, bundle, korunan dosyalar

| | Taban | Sonra |
|---|---|---|
| `.mjs` | 114/114 | 114/114 |
| `.ts` | 368/369 | **412/413** (+44 yeni) |
| kalıcılık e2e (regresyon) | 15/15 | **15/15** (`faz5_kalicilik_regresyon_cikti.txt`) |
| karşılaştırma e2e | — | **15/15** |

Tek başarısız test önceden var ve grafikle ilgisiz: `UC: admin PDF INDIREBILIR` (`tests/kiracilik/raporlar-rol.test.ts`).

**Mutasyon** (`kanit/karsilastirma/mutasyon.sh`, çıktı `faz5_mutasyon_cikti.txt`) — **11/11 öldü**: köprü saydamlığı yok (M1), her seri
kendi ilk gününe göre (M2), LOCF (M3), 4. sembolde en eskiyi at (M4), yinelenen denetimi yok (M5), renk sıraya bağlı (M6), anahtar
kimliği yok sayar (M7), sıfırlama karşılaştırmayı silmez (M8) — birim; H-6 kapısı yok (M9), Delete koruması yok (M10), mum grafiği
kaldırılıyor (M11) — e2e. *İlk koşuda M9 hayatta kaldı:* K2'ye bağlanmıştı ve H-6'nın ikinci düzeltmesinden sonra K2 grafiği hiç
kaldırmıyordu; K6'ya bağlandı (elle doğrulandı: K1, K6, K13, K15 dördü de öldürüyor).

- `npx tsc --noEmit`: 2 hata, **ikisi de tabandaki**; yeni hata 0 (arada kendi testimde çıkan TS2339 düzeltildi — `strict: false`).
- `/dashboard` JS (7 dosya, `kanit/karsilastirma/bundle_olc.mjs`): ham 787 988 → 803 909 B (**+15 921**), gzip-9 232 628 → 237 339 B
  (**+4 711, %2,0**). Next tablosu First Load 233 → 237 kB.
- Korunan dosyalar önce/sonra aynı: `1c9f41cf… cascade.py`, `1a9fc06d… main.py`, `98f9841c… llmquant_client.py`.
  `git diff origin/main -- maa/ frontend/src/app/dashboard/page.tsx frontend/components/PriceChart.tsx` → boş.

## Y3 — "normalize edilmiş karşılaştırma doğru mu, yanıltıcı mı?"

| Yanıltma riski | Durum |
|---|---|
| Kütüphanenin yüzde modu: taban "ilk **görünür** değer", kaydırınca kayar | **Kullanılmadı**; taban sabit bir gün, lejantta yazılı |
| Farklı başlangıçlı seriler "aynı %0" ama farklı günlerden | **Önlendi**: ortak taban günü; taban öncesi bar sayısı notta |
| Eksik gün düz çizgiyle köprülenir (kütüphane varsayılanı — H-7) | **Önlendi**: saydam segment, piksel testiyle kanıtlı |
| LOCF sahte "%0 günlük değişim" üretir | **Uygulanmadı** |
| Düzeltilmemiş bölünme −%50 "performans" gibi görünür | **İşaretlenir**: tek günde > %40 hareket notta; düzeltme durumu kaynağa göre değişiyor (Tiingo düzeltilmiş, defeatbeta belirsiz) ve **iddia edilmiyor** |
| Tek günlük veri "adası" çizgi olarak görünmez | **Sınır**: imleçte değeri okunur, boşluk sayımında görünür |
| Hiçbir seride olmayan gün (ör. ortak tatil) | **Sınır**: takvim verisi olmadan "eksik" denemez; eksende yer almaz (tek-sembol grafiğiyle aynı) |
| Sonuç taban gününe çok duyarlıdır | Taban günü lejantın ilk satırında; dönem seçici **yok** (V-12) |

## Bulunan hatalar

| # | Özet | Durum |
|---|---|---|
| H-7 | lightweight-charts 5.2.1 çizgi serisi whitespace'i köprülüyor; "whitespace ver" yaklaşımı eksik günü sessizce enterpole ederdi | FAZ 1'de ölçüldü, tasarım buna göre yapıldı (K5, M1) |
| H-6 | Karşılaştırma grafiği kaldırılırken yok edilmiş grafikte `removeSeries` → tüm terminal çöküyordu; yeni sembol yüklenirken grafik gereksiz yere sökülüyordu | düzeltildi (K6, M9) |
| — | Çıkar düğmesi 390 px'te 25×20 px (WCAG 2.5.8 altı) | 28×28 yapıldı, K11 kilitliyor |

Ayrıntı ve 5 Neden: `HATA_HAFIZASI_grafik.md`. Düzenekteki kendi hatalarım da kayıtlı: K11 ilk koşuda 1280 px açıldı
(`newPage()` viewport almıyor) — düzeltilip `innerWidth === 390` doğrulaması eklendi.

## Yapılmayanlar / sınırlar (açıkça)

- **Gerçek Next sunucusu + middleware + gerçek piyasa verisiyle uçtan uca koşum YAPILMADI.** Bileşen gerçek Chromium'da, sahte uçlar ve
  deterministik fikstürlerle sınandı (fikstürler piyasa verisi değildir). Üretim DB'sine gerek olmadı (D1 tetiklenmedi).
- Karşılaştırma yalnızca **günlük**; haftalık/aylık yok (ADR-6 §dilim). Dönem seçici yok; 1500 bar penceresi, taban lejantta.
- Karşılaştırma modunda **PNG yok** (düğme gizli; gizli mum grafiğinin PNG'si yanıltırdı).
- Çizim ve göstergeler karşılaştırma grafiğinde yok (fiyat birimli; yüzde eksende anlamsız) — tek-sembol grafiğinde korunuyor.
- Ek sembol verisi yalnızca oturum boyunca önbellekte; sayfa yenilenince yeniden çekilir. Hatalı sembol, çıkar+ekle ile yeniden denenir;
  otomatik yeniden deneme yok.
- Sembol limiti 4+'ya genişletilmedi (D3 tetiklenmedi): 4. renk tüm-çiftler CVD eşiğini geçmiyor.
- Y12 zaman kutusu ölçülmedi/raporlanmadı.
