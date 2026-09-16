# FAZ 1.5 — Risk Haritası

Her risk: **olasılık × etki**, ölçülen kanıt, azaltma. "Tek yönlü kapı" (Y11)
kriterleri: (a) veri kalıcı dönüşür, (b) >100 satır etkilenir, (c) 3. taraf
senkron kaybı riski.

| # | risk | olasılık | etki | Y11 tek yönlü mü | azaltma |
|---|---|---|---|---|---|
| **R-1** ⟳ | **DÜZELTİLDİ (bkz. 1.1c):** Defter kullanıcıya bölünüp **broker bölünmezse** güvenlik kapıları işlevsiz kalır. `fark = defter_adet − broker_adet` her zaman ≤ 0 olur; 01.09.2026'da ölçülen 9,2 kat şişmiş K/Z kusuruna karşı konmuş kapı herkes için kapanır. Risk tavanı %60 → hesap genelinde %300 | **kesin** (matematiksel) | **kritik** — gerçek para yolu değil ama gerçek emir yolu | **(c) EVET** — Alpaca ile senkron kaybı | **Kullanıcı başına Alpaca hesabı `alpaca_paper.py`'de (KORUMASIZ) ContextVar ile çözülebilir** — `_basliklar()` kimliği çağrı anında okuyor. O zaman iki taraf da bölünür ve kapılar ÇALIŞIR. Alternatif: defteri hiç bölmemek |
| **R-2** | Göç sırasında cron yeni satır yazar → sahipsiz kayıt | **yüksek** (günde 4 çalışma) | orta | (a) kısmen | Göç öncesi cron'u durdur; `ALTER TABLE ... DEFAULT` ile yerinde göç |
| **R-3** | SQLite `journal_mode=delete` — yazar/okuyucu birbirini bloke eder; `busy_timeout=5000` | **yüksek** (çok kullanıcıda) | orta — "database is locked" | hayır | **Yol bazlı kiracılık bunu kendiliğinden çözer**; kolon bazlı **ağırlaştırır**. Ya da WAL'a geç |
| **R-4** | Kota/kredi tükenmesi: A günün 25 GEX isteğini bitirir, B hizmet alamaz | **kesin** | yüksek — ödeme yapan müşteriye hizmet reddi | hayır | Redis sayacına kullanıcı boyutu (`gex:quota:<user>:<gun>`); **Bütçe Onay Kuralı bunsuz uygulanamaz** |
| **R-5** | Proxy önbelleği çapraz sızıntı + maliyet atfı bozulması (15 dk TTL, yol anahtarlı) | **kesin** | yüksek | hayır | Önbellek anahtarına kullanıcı eklemek krediyi **ikiye katlar** → bütçe kuralıyla çatışır. Alternatif: paylaşılan sonucu açıkça "paylaşılan" olarak işaretlemek |
| **R-6** | Testler kırılır: `defter` 16, `izlenen` 9 test dosyasında (birleşim 24/75). 8 test `izlenen.DOSYA_YOLU`'nu monkeypatch ediyor — yol ContextVar'dan türerse yamalar **sessizce işlevsiz** kalır | **kesin** | orta | hayır | Test uyarlaması iş kalemine dahil; ayrıca `defter.kur()` `CREATE TABLE IF NOT EXISTS` olduğu için mevcut deftere sütun **eklenmez** — ayrı ALTER göçü gerekir (`defter.py:107-132` deseni) |
| **R-7** | `/oz-iyilestirme/uygula` küresel strateji parametrelerini değiştirir → bir kullanıcının ayarı ötekinin karar kodunu değiştirir | orta | yüksek | (a) EVET — ayar geri alınabilir ama kararlar üretilmiş olur | Uçları kiracı başına ayır **veya** admin'e kilitle |
| **R-8** | Kullanıcı B yaratılamıyor — `signUp` tüm depoda **0** | **kesin** | **FAZ 3 BLOKE** | hayır | Sağlama yolu (davet/kayıt) bu işin ön koşulu; Supabase admin API ile tohum kullanıcı |
| **R-9** | Bildirim tek sabit numaraya gidiyor → A'nın portföyü B'ye | orta | yüksek (dışarı sızma) | (c) EVET — WhatsApp'a gitti mi geri alınamaz | Alıcı kavramı eklenene kadar bildirimleri kullanıcı verisinden **arındır** |
| **R-10** | Yedek/geri yükleme kiracı-körü; tek dosya. "Kullanıcı verimi sil" (KVKK) karşılanamaz | düşük (bugün) | orta | (a) EVET | Yol bazlı kiracılık bunu da kolaylaştırır (dosya başına yedek/silme) |
| **R-11** | `user_portfolio` tablosu yaratılırsa, `maa/src/main.py:127`'deki filtresiz `DELETE FROM user_portfolio` **tüm kullanıcıların** satırlarını siler. Dosya korunuyor → düzeltilemez | orta | **kritik** | (a) EVET | Tabloyu **hiç yaratma**; yeni tablo BAŞKA adla kurulsun. İsim tuzağı: TimescaleDB `user_portfolio` (yok) ≠ Supabase `user_portfolios` (var) |
| **R-12** | `/api/maa/memory/{ticker}` cognee'nin tek global dataset'ini beyaz listeden açıyor → tarayıcıdan çapraz-kullanıcı karar geçmişi | **kesin** | yüksek | hayır | Dataset adına kullanıcı boyutu eklemek `maa/src/main.py:1082`'yi (KORUNAN) değiştirmeyi gerektirir **veya** ucu beyaz listeden çıkarmak (korumasız, tek satır) |
| **R-13** | `godmode-execution` ikinci emir yüzeyi — `/mode-a/execute` tek global ADMIN_KEY ile gerçek emir gönderiyor | orta | **kritik** | (c) EVET | Bu servis Faz 1 envanterine sonradan girdi; kapsam kararı gerekiyor |

## Tek yönlü kapı özeti (Y11)

Y11 kriterlerinden en az birini karşılayanlar: **R-1 (c), R-7 (a), R-9 (c),
R-10 (a), R-11 (a), R-13 (c)**. Bunların her biri için standart Y5 revert
**yeterli değildir** ve ek kanıt yükü gerekir.

Geri kalanlar (R-2…R-6, R-8, R-12) standart Y5 ile karşılanır.


## R-14 (yeni) — deponun kendi korunan listesi Y1'den geniş

`strateji.py` ve `risk.py` tam blob SHA-1 ile kilitli (`korunan_dosya_manifesti.py:27`),
`simulasyon.py` ve `main.py` AST ile. Risk tavanı / pozisyon boyutlandırma mantığı
`risk.py`'de yaşıyorsa, kullanıcı başına kota oraya **dokunamaz**.
**Olasılık:** kesin · **Etki:** orta · **Y11:** hayır ·
**Azaltma:** Faz 2'de `risk.py`'nin kullanıcı boyutuna ihtiyaç duyup duymadığı
ölçülür; duyuyorsa bu ikinci bir Y8 istisnası talebidir.
