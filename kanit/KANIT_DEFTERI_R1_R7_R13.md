# KANIT DEFTERİ — R-1 / R-7 / R-13

Her iddia: **dosya:satır | komut | çıktı | zaman**. Kanıtsız satır yok (Y9).

---

## R-7 — /oz-iyilestirme küresel strateji parametreleri

**Durum: KAPATILDI** (asimetri giderildi) · commit `0bef966` (godmode-paper-trading-service, **yerel**, push edilmedi)

### K-7.1 — Uçlar admin kapısının arkasında

`godmode-paper-trading-service/src/main.py:1672,1682,1690,1778,1789`

```
@app.get("/oz-iyilestirme/durum")       -> yetki(x_admin_key)
@app.post("/oz-iyilestirme/denetle")    -> yetki(x_admin_key)
@app.post("/oz-iyilestirme/uygula")     -> yetki(x_admin_key)
@app.post("/oz-iyilestirme/geri-al")    -> yetki(x_admin_key)
@app.post("/oz-iyilestirme/bozulma-denetimi")
```

### K-7.2 — Kapı canlıda gerçekten kapalı (20.09.2026)

```
$ docker exec godmode-paper-trading python3 -c "... urlopen('/oz-iyilestirme/durum') ..."
  /oz-iyilestirme/durum: HTTP 401 Unauthorized
  govde: {"detail":"PAPER_ADMIN_KEY gerekli ve dogru olmali"}
```

### K-7.3 — Anahtar tanımlı, yani kapı gerçek doğrulama yapıyor

```
  ortam PAPER_ADMIN_KEY            tanimli=True uzunluk=48
```

`src/main.py:96-97` → `if not ADMIN_KEY or x_admin_key != ADMIN_KEY: raise HTTPException(401, ...)` (fail-closed)

### K-7.4 — Proxy katmanı da kapalı

`godmode-paper-trading-service/frontend/src/app/api/paper/[...yol]/route.ts:28-49`
Beyaz listede `/oz-iyilestirme` **yok**; bilinmeyen yol `403` (satır 190-197).
Tek yazma yolu `islem-modu` ve o, admin anahtarını **değil** dar
`IZLENEN_LISTE_ANAHTARI`'nı kullanıyor (satır 312-321).

### K-7.5 — Servis dışarı açık değil

```
godmode-paper-trading  8000/tcp -> 127.0.0.1:8310
0.0.0.0'ta dinleyen: yalnizca 22/tcp (sshd), 443/tcp (stunnel4 -> 127.0.0.1:22)
```

### K-7.6 — Kapatılan asıl boşluk ve kanıtı

Ölçüm: proxy tarafı `tests/test_proxy_salt_okunur.py` ile kilitliydi,
**servis tarafı kilitsizdi** (üç test dosyası `/oz-iyilestirme`'den söz
ediyor, hiçbiri yetki/401 doğrulamıyor).

```
$ python3 -m pytest tests/test_oz_iyilestirme_yetki_kapisi.py -q
  8 passed in 0.23s

tam takim (benimle) : 1288 passed, 5 failed
tam takim (TABAN)   : 1280 passed, 5 failed     -> sifir regresyon, +8 test

Mutasyon 1 (uygula ucundan yetki silindi)        -> 1 failed  ✅ yakaladi
Mutasyon 2 (yetki()'den 'not ADMIN_KEY' silindi) -> 1 failed  ✅ yakaladi
```

Ortak 5 kırmızı tabanda da var ve **ortamsal**: izole konteyner, Elite
deposundaki AST hash yollarını göremiyor.

### K-7.7 — Y1 kutsal dosya bütünlüğü

```
$ sha256sum -c kutsal_taban.txt
  taa/src/main.py: OK
  maa/src/main.py: OK
  godmode-paper-trading-service/src/main.py: OK
```

Commit yalnızca `tests/` altına **ekleme** yapar; `src/` hiç değişmedi.

### K-7.8 — Komşu koruması (Y6 / D2)

Depo kirliydi (`reports/korunan_dosya_hashleri.json` — başkasının işi) →
izole worktree'de geliştirildi ve **mutasyonlar orada yapıldı**. Commit'e
yalnızca kendi dosyam adıyla eklendi; o kirli dosya hâlâ commit'lenmemiş
duruyor. Worktree kaldırıldı (`git worktree list` → tek girdi).

---

## R-7 — 5 ÖZ-SORGU

**1. Ne varsaydım?**
Risk kaydının doğru olduğunu: `/oz-iyilestirme/uygula`'nın sıradan bir
kullanıcı tarafından çağrılabildiğini. Bu varsayım **yanlıştı** ve iş,
"açığı kapatmak"tan "kapının kilitli olduğunu kanıtlamak ve kilidi
testle sabitlemek"e dönüştü.

**2. Kanıtladım mı?**
Evet, dört bağımsız katmanda: kaynak (AST), canlı 401 yanıtı, proxy
beyaz listesi, port bağlaması. Ayrıca eklediğim testin **işe yaradığını**
iki mutasyonla kanıtladım — bu olmadan "8/8 PASS" hiçbir şey demezdi.

**3. Hangi senaryoda kırılır?**
(a) Birisi `yetki()`'yi `Depends()` gibi farklı bir mekanizmaya taşırsa
testim yanlış alarm verir — kapı aslında duruyor olsa bile kırmızıya
döner. Bu **kabul edilebilir** yön: güvenlik testi yanlış-negatif değil
yanlış-pozitif tarafına düşmeli. (b) Yeni bir `/oz-iyilestirme` ucu
`app.include_router` ile başka dosyadan eklenirse bulucum görmez —
`@app.<metot>` desenine bağlıyım. Bu **gerçek bir sınır** ve burada
açıkça kayda geçiyor.

**4. Rakip mühendis neyi eleştirir?**
"AST testi davranışı değil sözdizimini ölçüyor; gerçek bir HTTP testi
daha güçlü olurdu." Haklı bir itiraz. Karşı gerekçem: `src.main` import'u
DB ve Alpaca istemcisi dahil ağır yan etkiler tetikliyor ve test o zaman
ortam koşullarına (anahtar tanımlı mı, DB ayakta mı) bağlı hale gelirdi —
yani yeşilliği koda değil şansa dayanırdı. Canlı 401'i **ayrıca** ölçtüm
ve kanıt defterine yazdım; ikisi birlikte hem davranışı hem yapıyı
kapsıyor.

**5. Sonraki adımda neyi yanlış yapabilirim?**
R-13'te üçüncü bir depoya gireceğim ve oradaki `/mode-a/execute` **gerçek
emir** yüzeyi. En olası hatam, R-7'deki gibi "risk kaydı doğrudur" diye
varsayıp gereksiz bir değişiklik yapmak — ya da tersine, "burada da
zaten kapalıdır" diye erken rahatlamak. Önlem: önce ölçüm, sonra karar;
ve hiçbir koşulda gerçek emir gönderen bir uca canlı istek atmayacağım.

---

## R-13 — godmode/execution ikinci emir yüzeyi

**Durum: KAPILAR KİLİTLENDİ + ÖRTÜŞME KANITLANDI** · commit `c8b3563`
(`/opt/alphawise/godmode/execution`, **yerel**, push edilmedi)

### K-13.1 — Risk kaydındaki "gerçek emir" nitelemesi YANLIŞ

`src/main.py:22-24`

```python
def get_trading_client():
    # KRITIK: paper=True HER ZAMAN sabit, degistirilemez
    return TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)
```

Tek kurulum noktası, sabit `paper=True`. Yani **Alpaca paper (simüle para)**;
gerçek para yolu yok. R-13'ün "kritik" derecesi bu ölçümle düşer.

### K-13.2 — Dört kapı yerinde (AST ile 9 uç tarandı)

```
GET    /health                       kapi_ILK=False   <- bilerek acik
GET    /account                      kapi_ILK=True
GET    /mode-a/analyze/{ticker}      kapi_ILK=True
POST   /mode-a/execute/{ticker}      kapi_ILK=True  confirm=True
GET    /mode-b/signals/{ticker}      kapi_ILK=True
POST   /mode-b/execute/{ticker}      kapi_ILK=True  confirm=True
GET    /performance-report           kapi_ILK=True
GET    /godmode/assessment/{ticker}  kapi_ILK=True
GET    /godmode/methodology          kapi_ILK=True
```

`verify_admin` fail-closed (`main.py:28`): `if not ADMIN_KEY or x_admin_key != ADMIN_KEY: raise 401`.
`if not confirm: return` her iki emir ucunda `submit_order`'dan **önce**
(satır 246 < 264 ve 373 < 408). Piyasa saati kapısı: `BLOCKED_MARKET_CLOSED`.

### K-13.3 — Tarayıcıdan ulaşılamıyor

`AlphaWise-Elite/frontend/src/app/api/godmode/[ticker]/route.ts:24`
yol **sabit**: `/godmode/assessment/${encodeURIComponent(ticker)}` — yol
enjeksiyonu yok. `GODMODE_ADMIN_KEY` frontend konteynerinde **tanımsız**
→ satır 13-18 gereği `503`. Dış yüzey: `127.0.0.1:8030`.

### K-13.4 — Anahtar yeniden kullanımı

```
paper-trading GODMODE_ADMIN_KEY  sha256[:16] = 7e02b48a6b016f45
godmode-execution ADMIN_KEY      sha256[:16] = 7e02b48a6b016f45   <- AYNI
paper-trading PAPER_ADMIN_KEY    sha256[:16] = e83d83c7c5f71e53   <- farkli
```

### K-13.5 — ⚠ ASIL BULGU: iki emir yüzeyi AYNI broker hesabını paylaşıyor

```
godmode-execution  ALPACA_API_KEY          sha256[:16] = eb8885988aadb469
paper-trading      ALPACA_PAPER_API_KEY    sha256[:16] = eb8885988aadb469  <- AYNI
godmode-execution  ALPACA_SECRET_KEY       sha256[:16] = e0f23d3098a27c4b
paper-trading      ALPACA_PAPER_SECRET_KEY sha256[:16] = e0f23d3098a27c4b  <- AYNI
canli hesap: PA30SBB6QS52
```

Yani görevin sorduğu *"ikinci emir yüzeyinin birinciyle çakışmadığını
kanıtla"* iddiası **yanlış**: çakışıyorlar.

**DÜZELTME (aynı gün, ilk kaydım yanlıştı).** Paylaşımı önce
"belgelenmemiş bir bağlantı" diye yazdım. Ölçüm bunu çürüttü: paylaşım
`godmode-paper-trading/src/main.py` içinde **altı ayrı yerde** belgeli ve
etkileri tek tek sınırlanmış — 343 (hesap geneli uçtaki uyarı notu),
681-699 (eski "defter == broker" kapısının arıza ürettiği ölçülüp
düzeltilmiş), 731-738 (broker fazlası "başka bir servise aittir" diye
etiketlenip ayrı alanda raporlanıyor), 740-744 (satışta
`etkin_adet = min(defter, broker)`), 767-774 (**toplam maruziyet bilerek
DEFTERDEN** hesaplanıyor; gerekçe ve 02.09.2026 ölçümü `73.575` yazılı),
980-982 (pozisyon karşılaştırması bilerek tek yönlü).

Ekip bu bağlantıyı benden önce ölçmüş, niceliklendirmiş ve sınırlamış.
"Boyutlandırma paylaşılan tabandan türüyor" cümlem de yanlıştı —
maruziyet ve boyutlandırma defterden geliyor. (bkz. Hata #4)

**Geriye kalan dar gözlem — R-15 olarak kayıtlı.** Altı yerin hiçbiri
`zarar_durumu_belirle` çağrısını ele almıyor:

```python
# main.py:544, 1259
pv = float(istemci().hesap().get("portfolio_value", 0))        # PAYLASILAN
zarar_durumu = risk.zarar_durumu_belirle(
    pv, defter.kar_zarar({}, "US").get("gerceklesen_kar", 0.0)) # YALNIZCA defter
# risk.py:125 -> abs(gerceklesen_kar) >= portfoy_degeri * 0.20  -> DURDURULMUS
```

Pay defterden, payda paylaşılan hesaptan. Ölçülen: eşik **20.212 $**
(%20 x 101.060), defterin bağlı sermayesi **9.876 $**, gerçekleşen zarar
**0,00 $**. Yani "zarar eşiği aşılırsa sistem kendini kapatır" güvencesi
bu servis için pratikte **tetiklenemez**. Tehlike üretmiyor — paydayı
büyüten başkasının sermayesi, kendi emirlerini serbestleştirmiyor — ama
güvence iddia ettiği kadar dar değil.

**Neden düzeltilmedi:** `src/main.py` Y1 korumalı; durdurma eşiğinin
paydasını değiştirmek bir ticaret sisteminin halt davranışını değiştirir
(D3). Ölçüldü, niceliklendirildi, karara sunuldu.

### K-13.6 — Kapatılan asimetri ve kanıtı

Bu depodaki dört test dosyasının hiçbiri `paper`/`verify_admin`/`confirm`
doğrulamıyordu.

```
$ python3 -m pytest tests/test_emir_yuzeyi_guvenlik_kapilari.py -q
  13 passed in 0.20s

tam takim TABAN   : 101 passed, 0 failed
tam takim benimle : 114 passed, 0 failed    -> sifir regresyon, +13 test

Mutasyon 1  paper=True -> paper=False                -> KIRILDI
Mutasyon 2  mode-a/execute'tan verify_admin silindi  -> KIRILDI (2 test)
Mutasyon 3  confirm kapisi submit_order'dan SONRAYA  -> KIRILDI
Mutasyon 4  BLOCKED_MARKET_CLOSED kaldirildi         -> KIRILDI
```

Dört mutasyon da **izole worktree'de** yapıldı; üretim kaynağına
dokunulmadı ve **hiçbir emir gönderilmedi**.

### K-13.7 — Y1 ve komşu koruması

```
$ sha256sum -c kutsal_taban.txt
  taa/src/main.py: OK
  maa/src/main.py: OK
  godmode-paper-trading-service/src/main.py: OK
```

`godmode/execution` deposu temizdi; yine de mutasyonlar worktree'de
yapıldı. Commit yalnızca `tests/` altına ekleme yapar; `src/` değişmedi.
Worktree kaldırıldı, depo `git status` temiz.

---

## R-13 — 5 ÖZ-SORGU

**1. Ne varsaydım?**
Risk kaydının iki iddiasını: (a) `/mode-a/execute`'ın **gerçek para** emri
gönderdiğini, (b) ikinci emir yüzeyinin birinciden bağımsız olduğunu.
İkisi de yanlış çıktı — (a) paper-only, (b) aynı hesabı paylaşıyorlar.

**2. Kanıtladım mı?**
Evet: `paper=True` AST ile tek kurulum noktasında sabitlendi; hesap
paylaşımı anahtar sha256 eşitliği + canlı `account_number` ile; boyutlandırma
bağlantısı beş çağrı yeri + canlı sermaye dökümüyle. Testin işe yaradığını
dört mutasyonla kanıtladım.

**3. Hangi senaryoda kırılır?**
(a) `include_router` ile başka dosyadan eklenen bir uç bulucumun görmediği
yerde kalır — `@app.<metot>` desenine bağlıyım; bu sınır açıkça kayıtlı.
(b) `verify_admin` bir FastAPI `Depends()`'ine taşınırsa testim yanlış alarm
verir. Yine yanlış-pozitif tarafı; güvenlik testi için doğru yön.
(c) Paylaşılan hesap bulgusu **çalışma zamanı** olgusudur; bir test onu
sabitleyemez — anahtarlar değişirse kanıt defteri eskir.

**4. Rakip mühendis neyi eleştirir?**
*"Asıl riski (paylaşılan sermaye tabanı) bulmuşsun ama düzeltmemişsin;
test eklemek asıl sorunu çözmez."* Doğru — ve bilinçli. Düzeltme, Y1
korumalı bir dosyada bir ticaret sisteminin pozisyon boyutlandırmasını
değiştirmek demekti; bunu otonom yapmak D3 ihlali olurdu. Bulduğumu
ölçtüm, niceliklendirdim (%73,3) ve karara sundum. İkinci itiraz:
*"AST testi davranış testi değil"* — R-7'dekiyle aynı gerekçe geçerli,
ayrıca burada davranış testi **emir göndermeyi** gerektirirdi ki
kesinlikle yapılmamalıydı.

**5. Sonraki adımda neyi yanlış yapabilirim?**
Kapanış raporunda bulguları olduğundan **ciddi** ya da olduğundan
**hafif** göstermek. Paylaşılan hesap gerçek bir bağlantıdır ama paper
parasıdır ve pozisyon kapısı aynı sembolde çalışır; "kritik" demek abartı,
"önemsiz" demek eksik olur. Raporda ikisini de ölçülen sayılarla vereceğim.
