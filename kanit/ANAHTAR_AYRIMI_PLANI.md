# ANAHTAR YENİDEN KULLANIMI — emir yüzeyi için dar anahtar

**Tarih:** 20 Eylül 2026
**Durum:** ✅ **UYGULANDI ve YÜRÜRLÜKTE** (20.09.2026) — `EXECUTE_ADMIN_KEY` tanımlı, ayrım canlı

---

## Ölçülen durum

Tek sır (`sha256[:16] = 7e02b48a6b016f45`) **üç serviste, iki farklı amaçla**:

| servis | ne için kullanıyor | gerçekten ne gerekiyor |
|---|---|---|
| `godmode-execution` | kendi kapısı — **emir yüzeyi dahil** (`/mode-a/execute`, `/mode-b/execute`) | tam yetki |
| `godmode-paper-trading` | istemci kimliği; `src/main.py:576,639` → `karar.godmode_degerlendirmesi` | **yalnızca okuma** |
| `alphawise-oanda` | kendi servis kapısı (`src/main.py:17,34`) — ilgisiz işlev, aynı değer | kendi kapısı |

Üçü de `alphawise-net` üzerinde, yani `alphawise-godmode-execution:8000`'e
ulaşabiliyorlar.

**Sonucu:** yalnızca **değerlendirme okumak** için anahtar tutan bir servisin
ortamını okuyan biri **emir gönderebilir**. `alphawise-oanda` ise emir
yüzeyiyle hiç ilgisi olmadığı hâlde onu açan bir sırrı taşıyor.

> ⚠ **DÜZELTME (20.09.2026, aynı gün).** Burada önce şöyle yazmıştım:
> *"`supabase-rest` ve `alphawise-phoenix` de bu değişkenleri taşıyor ama
> farklı bir değerle (`9257354c1ddb41bd`)."* **Bu ölçüm yanlıştı.**
> `docker exec … sh -c` ile yapılmıştı; bu iki konteynerde `sh` bulunmuyor,
> komut başarısız oluyordu ve ben çıkan çıktıyı gerçek anahtar sandım.
> `docker inspect .Config.Env` ile bakıldığında ikisinde de
> `ADMIN_KEY`/`GODMODE_ADMIN_KEY` **hiç yok** (0 eşleşme). Sırrı taşıyan
> canlı konteyner sayısı **tam olarak üç**tür.

---

## Çözüm — deponun kendi deseni

`godmode-paper-trading` zaten bu sorunu bir kez çözmüş: `IZLENEN_LISTE_ANAHTARI`
dar bir anahtardır ve yalnızca tek bir uçta kontrol edilir (`src/main.py:39-52`).
Aynı desen emir yüzeyine uygulandı.

`godmode/execution/src/main.py`:

```python
EXECUTE_ADMIN_KEY = os.getenv("EXECUTE_ADMIN_KEY")

def verify_execute(x_admin_key):
    beklenen = EXECUTE_ADMIN_KEY or ADMIN_KEY   # tanimsizsa geriye uyumlu
    if not beklenen or x_admin_key != beklenen:
        raise HTTPException(401, "Emir anahtari gerekli ve dogru olmali")
```

Okuma uçları `verify_admin`, emir uçları `verify_execute` çağırıyor.

**Geriye uyumluluk bilinçli:** `EXECUTE_ADMIN_KEY` tanımlı değilse
`ADMIN_KEY`'e düşülür, yani bugünkü davranış birebir korunur. Böylece
**dağıtım anı** ile **ayrımın yürürlüğe girdiği an** ayrılabiliyor —
dağıtım tek başına hiçbir şeyi değiştirmiyor.

---

## Kanıt

### Yapı (AST, import etmeden)

```
GET    /health                       ilk_kapi=-             <- bilerek acik
GET    /account                      ilk_kapi=verify_admin
GET    /mode-a/analyze/{ticker}      ilk_kapi=verify_admin
POST   /mode-a/execute/{ticker}      ilk_kapi=verify_execute   <- DAR
GET    /mode-b/signals/{ticker}      ilk_kapi=verify_admin
POST   /mode-b/execute/{ticker}      ilk_kapi=verify_execute   <- DAR
GET    /performance-report           ilk_kapi=verify_admin
GET    /godmode/assessment/{ticker}  ilk_kapi=verify_admin
GET    /godmode/methodology          ilk_kapi=verify_admin
```

### Davranış (izole konteyner, `--network none`, **emir gönderilmedi**)

**Senaryo 1 — ayrım etkin** (`ADMIN_KEY=okuma…`, `EXECUTE_ADMIN_KEY=emir…`):

```
emir ucu + OKUMA anahtari        -> HTTP 401    <- ASIL KAZANIM
emir ucu + YANLIS anahtar        -> HTTP 401
emir ucu + ANAHTARSIZ            -> HTTP 401
okuma ucu + OKUMA anahtari       -> HTTP 200    <- paper-trading calismaya devam eder
okuma ucu + YANLIS anahtar       -> HTTP 401
okuma ucu + EMIR anahtari        -> HTTP 401    <- ayrim IKI YONLU
```

**Senaryo 2 — geriye uyumluluk** (`EXECUTE_ADMIN_KEY` tanımsız):

```
emir ucu + OKUMA anahtari        -> HTTP 500    <- kapiyi GECTI (kanit)
emir ucu + YANLIS anahtar        -> HTTP 401
okuma ucu + OKUMA anahtari       -> HTTP 200
```

`500`, kanıtın kendisidir: kimlik doğrulama geçti, sonra ağsız konteynerde
piyasa-saati DNS çağrısı düştü. Emir gönderilmedi (ağ yok, `confirm` yok).

### Test ağı

| | önce | sonra |
|---|---|---|
| `test_emir_yuzeyi_guvenlik_kapilari.py` | 13 | **18** |
| tam takım | 114 | **119** |
| kırmızı | 0 | **0** |

Eklenen dört sözleşme: emir uçları **dar** kapıyı kullanır · okuma uçları
**okuma** kapısını kullanır (aksi hâlde ayrım sessizce bir kesintiye
dönüşürdü) · `verify_execute` hem geriye uyumlu hem fail-closed ·
`EXECUTE_ADMIN_KEY` ortamdan okunur.

Ayrıca bir **meta-test**: en sinsi gerileme "kapı yok" değil, **yanlış
kapı**dır. Emir ucu `verify_admin` çağırırsa eski denetim onu temiz
sayardı; yeni denetim yakalıyor — sentetik kaynakla doğrulandı.

---

## Uygulama adımları

```bash
# 1) DAGITIM — davranisi DEGISTIRMEZ (EXECUTE_ADMIN_KEY henuz tanimsiz)
cd /opt/alphawise/godmode/execution
docker compose up -d --no-deps godmode-execution

# 2) YENI ANAHTAR uretilir ve YALNIZCA emir gonderecek tarafa verilir
#    (bugun: operator/cron. paper-trading ve oanda ALMAZ.)
#    /opt/alphawise/godmode/execution/.env icine:
#      EXECUTE_ADMIN_KEY=<yeni sir>

# 3) Yeniden kurulur ve ayrim yururluge girer
docker compose up -d --no-deps godmode-execution
```

**Geri alma:** `.env`'den `EXECUTE_ADMIN_KEY` satırı silinir, konteyner
yeniden kurulur → `ADMIN_KEY`'e düşer, bugünkü davranış geri gelir.
Kod değişikliğini geri almak gerekmez.

---

## Adım 2 kimseyi kırmıyor — ÖLÇÜLDÜ

`EXECUTE_ADMIN_KEY` tanımlandığı an, `ADMIN_KEY` ile emir gönderen **her**
çağıran 401 almaya başlar. Bu yüzden "emir gönderen başka kim var?" sorusu
**iki bağımsız yöntemle** arandı (`/opt/alphawise` geneli, 32.730 `.py`
dosyası dahil):

| yöntem | sonuç |
|---|---|
| `grep -rn -e "mode-a/execute" -e "mode-b/execute"` | 16 satır, **hepsi** `/godmode/execution/` içinde |
| `find … -print0 \| xargs -0 grep -ln "mode-[ab]/execute"` | 2 dosya: `src/main.py` ve bu görevin test dosyası |

**Sonuç: execution dışında emir uçlarını çağıran kod yok.** Dolayısıyla
yeni anahtar yalnızca operatörün/cron'un eline geçmeli; `paper-trading`
ve `oanda` hiçbir şey kaybetmez — paper-trading zaten yalnızca okuma
yapıyor (`src/main.py:576,639`).

> Yöntem notu: bu arama önce **yanlış olumsuz** verdi (boru zincirindeki
> bir filtre sonucu yutmuştu). Pozitif kontrol — aramanın bilinen bir
> geçişi bulduğunu doğrulamak — hatayı ortaya çıkardı. Olumsuz bir
> güvenlik bulgusu, aracın çalıştığı kanıtlanmadan kabul edilmemeli.

### İlgili mevcut koruma

`godmode-paper-trading/src/guard.py:123-132` iç servis adreslerini beyaz
listeye bağlıyor ve gerekçesi tam da bu sırdır:
*"istek God Mode'un ADMIN anahtarını başlıkta taşıdığı için, saldırganın
kontrolündeki bir adrese yönlendirilmek o anahtarı SIZDIRIRDI."*
Dar anahtar bu korumanın yerini almaz, onu tamamlar: adres zehirlenmesi
olsa bile sızacak anahtar artık **emir gönderemez**.

---

## UYGULAMA SONUCU (20.09.2026)

Dağıtım iki adımda yapıldı ve **ikisi arasında bir kusur yakalandı**.

### Adım 1 — kod dağıtıldı, davranış değişmedi

`b7aed3d69804 → f9269ed5b4b7`, 6 sn recreate, 11 sn'de healthy.
`EXECUTE_ADMIN_KEY` henüz tanımsız olduğu için `verify_execute` `ADMIN_KEY`'e
düştü. Canlı doğrulandı: emir ucu + doğru anahtar → `200
BLOCKED_MARKET_CLOSED` (piyasa kapalı, emir yok), yanlış/anahtarsız → 401.

### Adım 2 — anahtar üretildi ve uygulandı

`openssl rand -hex 24` (48 karakter, mevcut anahtarlarla aynı uzunluk),
`sha256[:16] = 2d0ecb38828dfab0` — `ADMIN_KEY`'in `7e02b48a6b016f45`
değerinden farklı olduğu doğrulandı. `.env`'e yorumuyla birlikte eklendi;
`.env` `*.env` ve `.env.*` kurallarıyla git'te izlenmiyor, depo temiz
kaldı. Yedek depo **dışına** alındı.

### ⚠ ARADA YAKALANAN KUSUR — ve neden canlı doğrulama şarttı

Anahtar tanımlandıktan sonraki ilk doğrulamada bir satır beklenenden
farklı çıktı:

```
mode-b + EMIR anahtari -> HTTP 401 {"detail":"Admin key gerekli ve dogru olmali"}
```

Mesajın **"Admin key"** demesi teşhisin anahtarıydı — bu `verify_execute`'un
değil `verify_admin`'in metni. Sebep: emir uçları önizleme için **içeride**
okuma uçlarını çağırıyor (`mode_a_analyze` / `mode_b_signals`) ve
çağıranın `x_admin_key`'ini olduğu gibi iletiyordu. Dış kapı geçiliyor,
**iç kapı** reddediyordu.

**Mode-a'da bu maskelenmişti:** piyasa saati kapısı o satırdan önce
dönüyor, dolayısıyla hafta sonu yapılan doğrulamada mode-a `200`
veriyordu. Piyasa açılınca aynı şekilde kırılacaktı — yani kusur,
yalnızca piyasa açıkken ortaya çıkan bir arıza olarak üretimde
bekleyebilirdi.

Düzeltme (`0418269`): iç delegasyona servisin **kendi** `ADMIN_KEY`'i
geçilir. Çağıran yetkisini `verify_execute` ile zaten kanıtlamıştır; bu
dışarıdan gelen bir istek değil, aynı süreç içinde fonksiyon çağrısıdır.
Test eklendi (`test_IC_DELEGASYON_cagiranin_anahtarini_ILETMEZ`) — piyasa
kapalıyken de piyasa-açık arızasını yakalıyor. 18 → 20 test, tam takım
119 → **121**, mutasyonla doğrulandı.

### Düzeltme sonrası canlı durum

```
mode-a + OKUMA -> 401        mode-a + EMIR -> 200 BLOCKED_MARKET_CLOSED
mode-b + OKUMA -> 401        mode-b + EMIR -> 200 (onizleme dondu)
okuma  + OKUMA -> 200        okuma  + EMIR -> 401      <- ayrim IKI YONLU
```

Broker: emir **166 → 166**, pozisyon **12 → 12** — hiçbir emir
gönderilmedi. Kredi harcanmadı: MAA'ya 0 karar/LLM çağrısı.

**Ders:** AST testi kabloyu kanıtlar, davranışı kanıtlamaz. Bu kusur
yalnızca canlı istekle görünür oldu — ve mode-a'da onu bile maskeleyen
bir kapı vardı. İki uç noktayı da ayrı ayrı sınamak belirleyici oldu.

---

## Kapsam dışı (bilinçli)

Mevcut paylaşılan sırrın **döndürülmesi** (rotation) bu planda yok. Dar
anahtar eklendikten sonra `ADMIN_KEY` hâlâ üç serviste ortaktır — ama artık
**emir gönderemez**. Sırrın kendisini yenilemek ayrı bir işlemdir ve üç
servisin eşzamanlı güncellenmesini gerektirir.
