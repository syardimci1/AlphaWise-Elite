# R-1 / R-7 / R-13 — KAPANIŞ RAPORU

**Tarih:** 20 Eylül 2026 · **Kapsam kararı:** Seçenek **A**

---

## 1. Kapsam kararı

Kullanıcı **A**'yı seçti: Kapsam A değişmiyor, `decision_log`/defter tek
sistem hesabı kalıyor. **R-1 kapsam dışı.** Sıra: R-7 → R-13.

R-1'in neden tek başına yapılamayacağı kayıtlıdır: defteri kullanıcıya
bölüp broker'ı bölmemek, `fark = defter_adet − broker_adet` ifadesini her
zaman ≤ 0 yapar ve 01.09.2026'da ölçülen 9,2 kat şişmiş K/Z kusuruna karşı
konmuş kapıyı **herkes için** işlevsizleştirir.

---

## 2. Madde madde sonuç

### R-7 — `/oz-iyilestirme` küresel strateji parametreleri

| | |
|---|---|
| **Durum** | ✅ Kapatıldı — ama iddia edildiği biçimde değil |
| **Commit** | `0bef966` (godmode-paper-trading-service, **yerel**) |
| **Dağıtım** | Gerekmedi — yalnızca `tests/` altına ekleme, çalışma zamanı değişmedi |

**İddia çürütüldü.** Uçların dördü de `yetki(x_admin_key)` çağırıyordu;
canlı anahtarsız çağrı `HTTP 401` döndü, `PAPER_ADMIN_KEY` tanımlıydı
(48 karakter), proxy beyaz listesinde bu uçlar hiç yoktu ve servis
`127.0.0.1:8310`'a bağlıydı.

**Gerçek boşluk asimetriydi:** proxy katmanı `test_proxy_salt_okunur.py`
ile kilitliydi, servis katmanı kilitsizdi.

**Kanıt:** 8/8 PASS · tam takım `1280 → 1288 passed` (sıfır regresyon,
+8 test; aynı 5 kırmızı tabanda da var ve ortamsal) · 2 mutasyon yakalandı.

### R-13 — `godmode/execution` ikinci emir yüzeyi

| | |
|---|---|
| **Durum** | ⚠ Kapılar kilitlendi; dar bir gözlem (R-15) **açık bırakıldı (D3)** |
| **Commit** | `c8b3563` (`/opt/alphawise/godmode/execution`, **yerel**) |
| **Dağıtım** | Gerekmedi — yalnızca `tests/` altına ekleme |

**"Gerçek emir" nitelemesi yanlıştı:** `paper=True` sabit kodlu, tek
kurulum noktası. Alpaca **paper** hesabı.

**Dört kapı yerindeydi, hiçbiri testli değildi** — kilitlendi:
`paper=True` sabit · `/health` dışında 8 ucun 8'inde `verify_admin` ilk
ifade · `confirm` varsayılanı `False` ve kapı `submit_order`'dan önce ·
piyasa kapalıysa `BLOCKED_MARKET_CLOSED`.

**Kanıt:** 13/13 PASS · tam takım `101 → 114 passed` (sıfır regresyon,
+13 test) · 4 mutasyon yakalandı · hiçbir emir gönderilmedi.

**Paylaşılan hesap — ilk iddiam yanlıştı, geri aldım.** İki emir yüzeyi
gerçekten aynı Alpaca hesabını (`PA30SBB6QS52`) kullanıyor, ama bunu
"belgelenmemiş bir bağlantı" diye kaydetmem hataydı: paylaşım
`godmode-paper-trading/src/main.py` içinde **altı ayrı yerde** belgeli
(343, 681-699, 731-738, 740-744, 767-774, 980-982), maruziyet ve
boyutlandırma **bilerek defterden** türetiliyor ve ekip aynı sayıyı
02.09.2026'da zaten ölçmüş. (bkz. Hata #4)

**Geriye kalan dar gözlem — R-15, AÇIK:** `zarar_durumu_belirle(pv, ...)`
payı **defterden**, paydayı **paylaşılan hesaptan** alıyor. Eşik
`%20 × 101.060 = 20.212 $`, oysa defterin bağlı sermayesi `9.876 $`.
Yani "zarar eşiği aşılırsa sistem kendini kapatır" güvencesi bu servis
için pratikte tetiklenemez. Tehlike üretmiyor (kapı gevşek tarafa
kayıyor, yanlış tarafa değil) ama güvence iddia ettiği kadar dar değil.
Düzeltme Y1 korumalı dosyada durdurma eşiğini değiştirmek demek —
**D3** sayıldı ve otonom yapılmadı.

---

## 3. Kendi hatalarım

Dördü de `HATA_HAFIZASI_R1_R7_R13.md` içinde tam kayıtlı:

1. **Ortam değişkeni adını kodun içindeki değişken adıyla karıştırdım** —
   `ADMIN_KEY` sorguladım, kod `PAPER_ADMIN_KEY` okuyor. Neredeyse
   *"tüm admin yüzeyi kapalı"* diye raporlayacaktım.
2. **"Tek frontend var" varsaydım** — üç frontend varmış; `/oz-iyilestirme`
   proxy'si başka depodaydı. **Bu hatanın sınıfı kayıtlı hafızamda zaten
   vardı**; kuralı bilmek yetmedi, negatif bulgu üretirken tetiklenmedi.
3. **Bir güvenlik kapısını "kör" ilan ettim** — kod yorumu (`main.py:980-982`)
   tek yönlü karşılaştırmanın bilinçli ve belgeli olduğunu gösterdi.
4. **"Belgelenmemiş" dedim; altı yerde belgeliymiş** — ve bunu commit
   ettikten *sonra* fark ettim. `pv`'nin ne için kullanıldığını
   doğrulamadan "boyutlandırma" dedim. Hata #3 ile **aynı kök**: grep bir
   konum bulur, bağlam bulmaz. Commit metni de düzeltildi.

**Ortak ders:** dördü de **yanlış** bir olumsuzlama üretti ve dördü de
"ölçtüm" kılığındaydı. Y9'a eklenen kural: *kanıtın kendisi de denetlenmelidir —
ölçtüğüm şey, iddia ettiğim şey mi?* Pratik karşılığı: olumsuz bir ölçüm
sonucu için **pozitif kontrol** göster. Testlerde mutasyon neyse, ölçümde
pozitif kontrol odur.

---

## 4. Öz-inceleme özeti

Her iki maddede de 5 öz-sorgu yanıtlandı (`KANIT_DEFTERI_R1_R7_R13.md`).
Öne çıkan iki itiraf:

- **AST testleri davranış testi değildir.** Gerekçem: `src/main.py`
  import'u DB/Alpaca yan etkileri tetikliyor ve testin yeşilliğini ortam
  koşullarına bağlardı. R-13'te ayrıca davranış testi **emir göndermeyi**
  gerektirirdi — kesinlikle yapılmamalıydı. Canlı 401 ölçümünü ayrıca
  yaptım; ikisi birlikte yapıyı ve davranışı kapsıyor.
- **Kendi bulgumu kendim çürüttüm ve bunu commit ettikten sonra fark
  ettim.** İlk "paylaşılan taban" tespitim yanlıştı; ekip onu benden önce
  ölçüp sınırlamıştı. Geriye kalan gerçek gözlem (R-15) çok daha dar ve
  onu da düzeltmedim — Y1 korumalı dosyada durdurma eşiğini değiştirmek
  D3 olurdu. Ölçtüm, niceliklendirdim, karara sundum.

**Bilinen sınır (ikisinde de):** bulucularım `@app.<metot>` desenine bağlı;
`include_router` ile başka dosyadan eklenen bir uç görülmez.

---

## 5. Kutsal dosyaların durumu (Y1)

Her fazda doğrulandı, **hiçbiri değişmedi**:

```
taa/src/main.py                          : OK
maa/src/main.py                          : OK
godmode-paper-trading-service/src/main.py: OK
```

Not: Y1 listesi `godmode-paper-trading-service/main.py` diyor; o yolda
dosya **yok**, servisin gerçek girişi `src/main.py` ve korunan olarak o
kabul edildi.

Her iki commit de yalnızca `tests/` altına **ekleme** yapar; hiçbir
`src/` dosyası değişmedi. Mutasyonların tamamı izole worktree'lerde
yapıldı, ikisi de sonrasında kaldırıldı.

---

## 6. Komşu koruması (Y6 / Y16 / D2)

- `godmode-paper-trading-service` **kirliydi** (`reports/korunan_dosya_hashleri.json`
  — başkasının işi) → izole worktree kullanıldı, commit'e yalnızca kendi
  dosyam adıyla eklendi, o dosyaya **dokunulmadı**.
- `godmode/execution` temizdi; yine de mutasyonlar worktree'de yapıldı.
- Komşu oturum (`godmode-paper-trading-service-06`) R-7 commit'i için
  **önceden** bilgilendirildi; R-13 bulgusu da iletildi.
- Her iki worktree kaldırıldı; iki depo da `git worktree list` tek girdi.

---

## 7. Tek cümle sonuç

**R-7 ve R-13'te iddia edilen açıklar ölçümle çürütüldü — kapılar zaten
yerindeydi ama testsizdi, ikisi de kilitlendi (21 test, 6 mutasyon, sıfır
regresyon); paylaşılan broker hesabı hakkındaki ilk bulgumu da ölçüm
çürüttü (ekip onu altı yerde belgelemiş ve sınırlamıştı) ve geriye
doğrulanmış tek bir dar gözlem kaldı: zarar-durdurma eşiğinin paydası
paylaşılan hesaptan, payı defterden geliyor; eşik 20.212 $ iken defterin
bağlı sermayesi 9.876 $ olduğu için durdurma bu servis için pratikte
tetiklenemez — korumalı dosya ve D3 olduğundan açık bırakıldı ve kullanıcı
kararına sunuldu.**
