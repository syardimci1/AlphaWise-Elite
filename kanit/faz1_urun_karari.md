# FAZ 1 — Araştırma Sentezi ve Ürün Kararı

**Tarih:** 16 Eylül 2026 · **Yöntem:** 10 ajanlı adversaryal iş akışı (1,16M token,
432 araç çağrısı) + 4 bağımsız doğrulama. Her iddia dosya:satır kanıtına bağlı.

---

## 1.1 — İki çekirdek iddia: ikisi de çürütüldü

Görev metninin C1 ve C2 sözleşmeleri iki mekanizma varsayıyordu. Üçer bağımsız
mercekle çürütmeye çalışıldı; **altı merceğin altısı da çürüttü.**

### İDDİA A — "defter, `godmode/src/main.py`'ye dokunmadan kullanıcı bazlı olur"

**HEDEFİ ayakta, MEKANİZMASI çürük.**

Ayakta kalanlar (kanıtlandı):
- `contextvars` sorunu **yok**: 29 ucun 26'sı senkron `def`; Starlette bunları
  `anyio.to_thread.run_sync` ile threadpool'a atar ve `copy_context()` yapar
  (anyio 4.15.1, starlette 0.41.3 — konteynerden ölçüldü). ContextVar senkron uca ulaşır.
- Cron **curl** kullanıyor, `docker exec` değil (`godmode_paper_otomasyon.sh:234-236`)
  → ASGI ara katmanı yazma yolunda **devrede**.
- Dockerfile CMD değişimi meşru: compose `command:` ile ezmiyor; hiçbir test
  Dockerfile'ı denetlemiyor; **deponun kendi emsali var** — `src/backtest_api.py:3-8`
  açıkça "main.py'ye satır yazmamak için ayrı bir uvicorn süreci" diyor.
- `izlenen.py` tarafı temiz: `src/` içinde main.py dışında ithal eden yok.

**Çürüten üç bulgu:**

1. **KORUNAN main.py'nin KENDİSİ ham SQL yazıyor.** `main.py:906-910` (`SELECT *
   FROM karar`, `SELECT * FROM sinyal_gozlem`) ve `main.py:1015-1019` (`FROM islem`).
   `defter.baglanti()` çıplak `sqlite3.Connection` döndürüyor (`defter.py:89-99`).
   → "defter.py okumaları filtreler" önerisi bu iki sorguya **dokunamaz**;
   `/kayitlar` ve `/islemler` tüm kullanıcıların satırlarını döndürür.
   *Kaçış:* kolon değil **yol bazlı kiracılık** (kullanıcı başına ayrı `.sqlite`).
   O zaman ham SQL kendiliğinden doğru kapsamda çalışır. Hedefi kurtarır, mekanizmayı yıkar.

2. **Mutabakat kapısı sessizce işlevsiz kalır.** `main.py:721 emir_engelli = fark > 1e-9`,
   `fark = defter_adet - broker_adet`. Defter kullanıcıya bölünür, broker **tek ve
   paylaşımlı** kalır → başka bir kullanıcı aynı sembolü tuttuğu an fark ≤ 0 olur ve
   01.09.2026'da ölçülen gerçek kusura (`main.py:686-704`: K/Z 9,2 kat şişmiş +
   açığa satış riski) karşı konmuş "hayalet pozisyon" kapısı **herkes için** kapanır.
   `main.py:744 etkin_adet = min(defter_adet, broker_adet)` de kullanıcıyı kendi
   hissesiyle sınırlamaz.

3. **Risk tavanı kullanıcı başına çatlar.** `main.py:544 pv = istemci().hesap()
   ["portfolio_value"]` **paylaşılan** hesabın özkaynağı; `main.py:553` maruziyet ise
   kullanıcı-filtreli defterden. %60 tavan her kullanıcı için ayrı ayrı **tüm hesabın**
   özkaynağına göre ölçülür → 5 kullanıcı hesap genelinde %300'e çıkabilir.
   Bu bir **risk limiti ihlalidir**. `_istemci` küresel tekil önbellek (`main.py:71-74`)
   yüzünden "her kullanıcıya kendi Alpaca hesabı" da dışarıdan çözülemez.

Ek: `_TRAILING_DURUMLARI` (`main.py:283`) yalnızca sembolle anahtarlı bellek-içi
sözlük; `/strateji-durumu` ve `/rapor` salt-okunur uçlarında A'nın trailing tepesi
B'ye sızar.

**Sonuç:** Servis, main.py'ye dokunmadan "kullanıcı başına veri saklar" hâle
**getirilebilir** (dosya-başına-defter ile). Ama **doğru** çoklu kullanıcı davranışı
(hayalet pozisyon kapısı + broker otoritesi + risk tavanı) `main.py:544/640/667-745/71-74`
değişmeden **sağlanamaz**.

### İDDİA B — "decision_log atfı, `maa/src/main.py`'ye dokunmadan proxy ile yazılır"

**HEDEFİ ayakta, MEKANİZMASI imkânsız.** Beş bağımsız kanıt zinciri:

1. **Proxy `decision_log_id`'yi öğrenemez.** Üç INSERT de `RETURNING`'siz
   (`maa/src/main.py:611-614, :1016-1019, :1047-1055`); `/decide` yanıtında
   (`:652-661`) ve `/narrative-verified`'da (`:1024 return result`) id yok.
   MAA'nın 18 ucunun hiçbirinde `Request`/`Header`/`Depends` parametresi **yok**
   (grep: 0 eşleşme) → dışarıdan user_id geçirmenin de yolu yok.
2. **Frontend'de Postgres sürücüsü yok** (`package.json`: @supabase/*, next, react,
   lightweight-charts) ve konteynerde `DB_*` ortam değişkeni verilmiyor
   (`docker-compose.yml:98-111`). Birleştirmenin ikinci yarısı fiziksel olarak imkânsız.
3. **Satırların %98'i proxy'den geçmiyor.** Beyaz liste yalnızca
   `portfolio-signal/adaptive_rotation`, `narrative-verified/<T>`, `memory/<T>`
   geçiriyor; `/decide` **403** (`route.ts:218-222`) ve tek çağırıcısı sunucu-içi
   `signal-ledger/src/main.py:91`. Canlı dökümü: `god_mode`=79, `bilinmiyor`=147,
   `llm_cascade`=4 → proxy kararların **%1,7'sine** temas ediyor.
4. **Havuz + önbellek atfı bozuyor.** `route.ts:104` havuzu: N eşzamanlı kullanıcı →
   1 MAA çağrısı → 1 satır. `route.ts:78` 15 dk TTL: önbellek isabetinde MAA'ya
   **hiç gidilmez** → kullanıcının isteği **sıfır** satır üretir.
   `DIS_SINIR_MS=1_200_000` (20 dk) yüzünden 504 sonrası dakikalarca sonra satır yazılabilir.
5. **(ticker, zaman) eşleştirmesi gerçek veride çakışıyor.** Canlı ölçüm: MSFT
   id=150 @01:49:53.559 ve id=151 @01:49:59.119 — **5,56 sn**; SCHD 18 sn, CAT 19 sn.
   `decided_at` DB tarafında `now()` ile üretiliyor, proxy o değeri hiç görmez.

Ek yapısal kusurlar: `decision_log`'un birincil anahtarı **(id, decided_at) çiftidir**
(`002:166`; `002:53` "cannot create a unique index without the column decided_at")
ve id'ler geçmişte migration 003 ile **toplu yeniden numaralandı** (`003:85-105`).
Tek sütunlu bir atıf, böyle bir bakım sırasında sessizce yanlış karara işaret eder.
Trigger yolu da kapalı: `get_db_connection` hiç `SET LOCAL` yapmıyor, TimescaleDB'de
`postgres_fdw`/`dblink` **yok** (`\dx`: yalnızca plpgsql + timescaledb), pg16 ve pg17
ayrı konteynerler.

Ayrıca tasarım **fail-open**: yetki bilgisi asıl tablonun dışında olduğu için
`decision_log`'u okuyan yeni her kod join'i unuttuğunda hata almaz, **herkesin**
verisini alır — RLS'li bir `user_id` sütununun tam tersi.

**Sonuç:** "MAA değişmeden atıf yapılabilir" **doğru**, ama C2'nin tarif ettiği
`decision_log_id` + proxy mekanizması **icra edilemez**. Doğru biçim: `decision_log`
sistem denetim günlüğü olarak kalır; proxy kullanıcının **kendi** kaydını
(gördüğü ticker/zaman/sonuç) RLS'li bir tabloya yazar.

---

## 1.1b — Tamamlık eleştirisinin bulduğu ve Faz 1'in ATLADIĞI şeyler

Dördü bağımsız olarak doğrulandı:

| # | bulgu | doğrulama |
|---|---|---|
| D1 | **Beşinci HTTP yüzeyi**: `godmode/execution` Alpaca'ya **gerçek emir** gönderiyor (`submit_order` :264 ve :408), `/account` ve `/performance-report` hesabın tamamını döndürüyor. Frontend `/api/godmode/` ile **bağlı**. | ✅ |
| D2 | `/api/maa/memory/{ticker}` **beyaz listede** (`middleware.ts:114`) ve cognee'nin **tek global** `"alphawise_decisions"` dataset'ini sorguluyor (`maa/src/main.py:1082`). Yani tarayıcıdan çapraz-kullanıcı karar geçmişine **ulaşılabiliyor**. İddia B çürütmesinin "sızıntı yolu yok" sonucu **yanlıştı**. | ✅ |
| D3 | defter `journal_mode=delete` — **WAL yok**, yazar okuyucuyu bloke eder. Yol bazlı kiracılık bunu çözer, kolon bazlı **ağırlaştırır**. | ✅ |
| D4 | **Kullanıcı oluşturma yolu hiç yok** — tüm depoda `signUp`/`createUser` = **0**. Faz 3 "kullanıcı B" gerektiriyor; B'yi yaratacak yol yok. | ✅ |

Diğer kritik bulgular (ajan kanıtlı, tekrar doğrulanmadı):
- **Hız sınırlama tek "ortak" kovada** (`middleware.ts:135-147`, kodun kendi yorumu
  bunu "tek kullanıcı varsayımı" diye gerekçelendiriyor) → A, B'yi 429'a düşürür.
- **Kota/kredi muhasebesi API anahtarı başına** (`gamma-exposure-service/main.py:117`)
  → A günün 25 GEX isteğini bitirir, B tüm gün hizmet alamaz. CLAUDE.md'nin
  Bütçe Onay Kuralı kullanıcı başına **uygulanamaz**.
- **MAA proxy önbelleği YOL anahtarlı** (`route.ts:78,100,167`) → A kredi yakar,
  B 15 dk bedava okur ve A için üretilmiş yanıt gövdesini aynen alır.
- **Üç `/oz-iyilestirme/*` ucu küresel strateji parametrelerini değiştiriyor**
  (`main.py:1690,1778,1789`) → bir kullanıcının uyguladığı sürüm ötekinin
  karar kodlarını değiştirir.
- `izlenen_semboller.json` **çıkış hedefi, stop-loss, trailing yüzdesi** ve
  22 kayıtlık değişiklik geçmişi taşıyor — izleme listesi değil, **ticaret niyeti**.
- `/api/raporlar/[dosya]` rotası `_req`'i **hiç kullanmıyor** → oturum kimliği oraya ulaşmıyor.
- `servisProxy` tipinde **başlık alanı yok** (`servis-proxy.ts:40-49`) — kullanıcıyı
  aşağı taşımak için değişmesi gereken asıl dosya bu (korumasız).
- Bildirim tek sabit telefon numarasına gidiyor (`whatsapp_notify.sh:44-52`).
- Redis'te kullanıcı boyutu kazanması gereken bir sınıf **var**: `gex:quota:*`.
  Görev bağlamındaki "Redis'te kullanıcı bileşeni gerekmiyor" hükmü **yanlış**.

---

## 1.2 — Y9: Mevcut defterin sahipliği (DUR-SEÇENEK)

### Taban veri — görev metnindeki sayı eskimiş

| tablo | görev metni | ölçüm (16.09, iki kez) |
|---|---|---|
| `karar` | 1244 | **1332 → 1339** (ölçüm sırasında büyüdü) |
| `islem` | 8 | 8 |
| `sinyal_gozlem` | 748 | 836 |

Cron hafta içi günde 4 kez çalışıyor (`0 16,18,20,21 * * 1-5`), ~176 karar/gün.
**Sonuç 1:** Geri-doldurma göçü, otomasyon **durdurulmadan** yapılamaz — yoksa
göç sırasında sahipsiz yeni satırlar oluşur.

**Sonuç 2 — ölçek yanlış anlaşılmış:** 1339 kararın **1319'u (%99)** cron'un
ürettiği `BEKLE` satırı. Yalnızca **13'ü AL** ve yalnızca **8'i** gerçek bir broker
emrine bağlı. "Kullanıcıya ait" sayılabilecek gerçek hacim 1244 değil,
**13 karar + 8 MSFT alımı (toplam 19-20 adet, hiç satış yok)**.

### Seçenekler ve ölçülen riskleri

| | seçenek | fayda | risk |
|---|---|---|---|
| **A** | Sistem/admin kullanıcısına ata | En güvenli izolasyon; yeni kullanıcı temiz başlar | Ürünün "Kanıt Odası" değer önerisi ilk gerçek kullanıcı için **sıfırlanır**: `/performans`, `/kapanmis-turlar`, `/kar-zarar` boş döner. 19 adetlik açık MSFT pozisyonu ekranda sahipsiz kalır ve `/mutabakat` (`main.py:959-970`) bunu **kalıcı uyumsuzluk alarmına** çevirir |
| **B** | Legacy (kullanıcısız) bırak | Hiçbir veri dokunulmaz; en az müdahale | **Fail-open**: `user_id IS NULL` satırlar filtreden ya sessizce geçer ya kaybolur. Daha kötüsü `performans.kapanmis_turlar` FIFO eşleştirmesi legacy **ALIŞ** ile yeni kullanıcının **SATIŞINI** eşleştirip o kullanıcıya ait olmayan bir kâr üretir |
| **C** | İlk kayıt olan kullanıcıya ata | Defterde temiz görünür; sürekliliği korur | Broker'da karşılığı **yok**: 19 MSFT adedi, nakit ve alım gücü tek Alpaca hesabında ortak. İkinci kullanıcının emri hesabın `buying_power`'ını tükettiğinde ilk kullanıcının pozisyon açma yeteneği düşer |

**Ortak gerçek:** Tek Alpaca hesabı olduğu sürece hangi seçenek seçilirse seçilsin
defterdeki atıf **broker seviyesinde kozmetiktir**. Ayrıca A ile C **aynı kişiye
çıkıyor**: ilk kayıt olan kullanıcı (`selcuk@alphawise.test`, 2026-08-03 16:26)
zaten `admin`. İkisi arasındaki tek gerçek fark, kuralın **gelecekte** nasıl
davranacağıdır (sabit sistem kimliği mi, "ilk gelen" kuralı mı).

---

## 1.1c — Ajan hükmünün DÜZELTİLMESİ: Alpaca kullanıcı başına ayrılabilir

Çürütme ajanı şunu yazmıştı: *"Tek dışarıdan çözüm 'her kullanıcıya kendi Alpaca
hesabı'dır; o da `main.py:71-74`'teki küresel tekil istemci önbelleği yüzünden
imkânsızdır."* **Bu hüküm fazla güçlü — ölçülerek yanlışlandı.**

```python
# alpaca_paper.py:38-52  (KORUMASIZ — Y1 listesinde de, depo manifestinde de YOK)
class AlpacaPaper:
    def __init__(self, api_key: str | None = None, secret: str | None = None):
        self.api_key = anahtar_dogrula(api_key or os.getenv("ALPACA_PAPER_API_KEY"), ...)
        ...
    def _basliklar(self) -> dict:                      # ← ÇAĞRI ANINDA okunuyor
        return {"APCA-API-KEY-ID": self.api_key, "APCA-API-SECRET-KEY": self.secret, ...}
```

İki olgu:
1. `__init__` kimlik bilgisini **parametre olarak kabul ediyor** — sabit kodlanmamış.
2. `_basliklar()` her istekte `self`'ten okuyor; `istemci()` tekil nesneyi döndürse
   bile bu metot **ContextVar'dan kullanıcıya özel kimlik çözebilir**.

`alpaca_paper.py` korumasız olduğu için bu değişiklik `main.py`'ye dokunmaz.

### Bunun R-1'e etkisi — riskin yönü tersine dönüyor

R-1 (mutabakat ve risk tavanının kırılması) **defterin bölünüp broker'ın
bölünmemesinden** doğuyordu: `fark = defter_adet − broker_adet` asimetrik hâle
geliyordu. Eğer **ikisi birden** kullanıcıya bölünürse:

| | defter | broker | `fark` anlamlı mı | risk tavanı |
|---|---|---|---|---|
| bugün | global | global | ✅ evet | ✅ doğru |
| defter bölünür, broker tek | kullanıcı | **global** | ❌ daima ≤ 0 → kapı ölü | ❌ %60 × N |
| **ikisi de bölünür** | kullanıcı | kullanıcı | ✅ **evet** | ✅ **doğru** |

Yani **üçüncü satır, `main.py`'ye dokunmadan ulaşılabilir** ve hayalet-pozisyon
kapısını da risk tavanını da korur. Bu, Faz 1'in en önemli bulgusudur ve
seçenek listesini değiştirir.

**Bedeli:** her kullanıcı için ayrı bir Alpaca kâğıt hesabı ve anahtar çifti
gerekir. Bu bir **ürün/işletme kararıdır** (hesap sağlama), teknik engel değil.
Y2 (sıfır yeni harcama) açısından: Alpaca kâğıt hesapları ücretsizdir, ama
hesap açma **kullanıcı eylemi** gerektirir — bu yüzden karar sizindir.

## 1.1d — Deponun KENDİ korunan-dosya listesi Y1'den geniş

`godmode-paper-trading-service/araclar/korunan_dosya_manifesti.py` makine ile
zorlanan bir liste tutuyor ve `tests/test_hizalama_sozlesmesi.py:203-207` bunu
her testte doğruluyor:

| dosya | kilit türü | Y1 listemde var mıydı |
|---|---|---|
| `src/strateji.py` | tam blob SHA-1 (**hiç değişmez**) | ❌ yoktu |
| `src/risk.py` | tam blob SHA-1 (**hiç değişmez**) | ❌ yoktu |
| `src/simulasyon.py` | docstring'siz AST | ❌ yoktu |
| `src/main.py` | docstring'siz AST | ✅ vardı |

Çapa 5'ten **8 dosyaya** çıkarıldı. Ayrıca **çapraz doğrulama**: benim AST aracım
ve deponun kendi aracı `src/main.py` için **aynı** özeti üretti (`dbd47e6f4946`)
— iki bağımsız uygulama aynı sonuca vardı.

Pratik sonuç: `strateji.py` ve `risk.py` **tek bayt** bile değişemez. Risk tavanı
mantığı `risk.py`'de yaşıyorsa, kullanıcı başına kota fikri oraya da dokunamaz —
bu Faz 2'de ölçülecek.
