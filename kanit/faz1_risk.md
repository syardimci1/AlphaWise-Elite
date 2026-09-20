# FAZ 1.5 — Risk Haritası

Her risk: **olasılık × etki**, ölçülen kanıt, azaltma. "Tek yönlü kapı" (Y11)
kriterleri: (a) veri kalıcı dönüşür, (b) >100 satır etkilenir, (c) 3. taraf
senkron kaybı riski.

| # | risk | olasılık | etki | Y11 tek yönlü mü | azaltma |
|---|---|---|---|---|---|
| **R-1** ⟳ | **DÜZELTİLDİ (bkz. 1.1c):** Defter kullanıcıya bölünüp **broker bölünmezse** güvenlik kapıları işlevsiz kalır. `fark = defter_adet − broker_adet` her zaman ≤ 0 olur; 01.09.2026'da ölçülen 9,2 kat şişmiş K/Z kusuruna karşı konmuş kapı herkes için kapanır. Risk tavanı %60 → hesap genelinde %300 | **kesin** (matematiksel) | **kritik** — gerçek para yolu değil ama gerçek emir yolu | **(c) EVET** — Alpaca ile senkron kaybı | **Kullanıcı başına Alpaca hesabı `alpaca_paper.py`'de (KORUMASIZ) ContextVar ile çözülebilir** — `_basliklar()` kimliği çağrı anında okuyor. O zaman iki taraf da bölünür ve kapılar ÇALIŞIR. Alternatif: defteri hiç bölmemek |
| **R-2** | Göç sırasında cron yeni satır yazar → sahipsiz kayıt | **yüksek** (günde 4 çalışma) | orta | (a) kısmen | Göç öncesi cron'u durdur; `ALTER TABLE ... DEFAULT` ile yerinde göç |
| **R-3** | SQLite `journal_mode=delete` — yazar/okuyucu birbirini bloke eder; `busy_timeout=5000` | **yüksek** (çok kullanıcıda) | orta — "database is locked" | hayır | **Yol bazlı kiracılık bunu kendiliğinden çözer**; kolon bazlı **ağırlaştırır**. Ya da WAL'a geç |
| **R-4** ✅ | **KAPATILDI (İ-7, `efb013d`)** — kullanıcı başına sayaç + yumuşak pay (%80). Kod hazır, servis henüz dağıtılmadı. Önceki hâli: | **kesin** | yüksek — ödeme yapan müşteriye hizmet reddi | hayır | Redis sayacına kullanıcı boyutu (`gex:quota:<user>:<gun>`); **Bütçe Onay Kuralı bunsuz uygulanamaz** |
| **R-5** | Proxy önbelleği çapraz sızıntı + maliyet atfı bozulması (15 dk TTL, yol anahtarlı) | **kesin** | yüksek | hayır | Önbellek anahtarına kullanıcı eklemek krediyi **ikiye katlar** → bütçe kuralıyla çatışır. Alternatif: paylaşılan sonucu açıkça "paylaşılan" olarak işaretlemek |
| **R-6** | Testler kırılır: `defter` 16, `izlenen` 9 test dosyasında (birleşim 24/75). 8 test `izlenen.DOSYA_YOLU`'nu monkeypatch ediyor — yol ContextVar'dan türerse yamalar **sessizce işlevsiz** kalır | **kesin** | orta | hayır | Test uyarlaması iş kalemine dahil; ayrıca `defter.kur()` `CREATE TABLE IF NOT EXISTS` olduğu için mevcut deftere sütun **eklenmez** — ayrı ALTER göçü gerekir (`defter.py:107-132` deseni) |
| **R-7** ✅⟳ | **ÖLÇÜLDÜ, İDDİA ÇÜRÜTÜLDÜ (20.09.2026, `0bef966`).** Uçlar zaten admin kapısının arkasındaydı; gerçek boşluk kapının testsiz olmasıydı. Aşağıya bakın. | — | — | hayır (ölçüldü) | Servis tarafı kapı testle kilitlendi |
| **R-8** | Kullanıcı B yaratılamıyor — `signUp` tüm depoda **0** | **kesin** | **FAZ 3 BLOKE** | hayır | Sağlama yolu (davet/kayıt) bu işin ön koşulu; Supabase admin API ile tohum kullanıcı |
| **R-9** ✅⟳ | **DÜZELTİLDİ ve KISMEN KAPATILDI (20.09.2026, `04bf9be`).** Özgün metin yanlıştı — ölçüm düzeltti. Aşağıya bakın. | — | — | hayır (ölçüldü) | Rol kapısı `/api/bildirimler`'e eklendi |
| **R-10** | Yedek/geri yükleme kiracı-körü; tek dosya. "Kullanıcı verimi sil" (KVKK) karşılanamaz | düşük (bugün) | orta | (a) EVET | Yol bazlı kiracılık bunu da kolaylaştırır (dosya başına yedek/silme) |
| **R-11** | `user_portfolio` tablosu yaratılırsa, `maa/src/main.py:127`'deki filtresiz `DELETE FROM user_portfolio` **tüm kullanıcıların** satırlarını siler. Dosya korunuyor → düzeltilemez | orta | **kritik** | (a) EVET | Tabloyu **hiç yaratma**; yeni tablo BAŞKA adla kurulsun. İsim tuzağı: TimescaleDB `user_portfolio` (yok) ≠ Supabase `user_portfolios` (var) |
| **R-12** | `/api/maa/memory/{ticker}` cognee'nin tek global dataset'ini beyaz listeden açıyor → tarayıcıdan çapraz-kullanıcı karar geçmişi | **kesin** | yüksek | hayır | Dataset adına kullanıcı boyutu eklemek `maa/src/main.py:1082`'yi (KORUNAN) değiştirmeyi gerektirir **veya** ucu beyaz listeden çıkarmak (korumasız, tek satır) |
| **R-13** ⚠⟳ | **ÖLÇÜLDÜ, KISMEN DÜZELTİLDİ (20.09.2026, `c8b3563`).** "Gerçek emir" nitelemesi yanlıştı (`paper=True` sabit). Dört kapı yerindeydi ve testle kilitlendi. **Ama iki emir yüzeyi aynı broker hesabını paylaşıyor** ve bu, boyutlandırma tabanını bağlıyor. Aşağıya bakın. | kesin (ölçüldü) | orta | hayır — paper parası | Kapılar kilitlendi; sermaye tabanı paylaşımı **AÇIK** (D3) |

## Tek yönlü kapı özeti (Y11)

Y11 kriterlerinden en az birini karşılayanlar: **R-1 (c), R-7 (a), R-9 (c),
R-10 (a), R-11 (a), R-13 (c)**. Bunların her biri için standart Y5 revert
**yeterli değildir** ve ek kanıt yükü gerekir.

Geri kalanlar (R-2…R-6, R-8, R-12) standart Y5 ile karşılanır.


## R-9 — özgün metin YANLIŞTI, ölçüm düzeltti (20.09.2026)

Özgün iddia şuydu: *"Bildirim tek sabit numaraya gidiyor → A'nın portföyü
B'ye."* Ölçüldüğünde iki ayrı şeyin karıştırıldığı görüldü.

**WhatsApp ayağı — risk yok, zaten kapalı.** `olay-tarayici-service/src/
bildirim.py` okundu: mesaj şablonu sabit ve yalnızca **kamuya açık olay**
bilgisi taşıyor (SEC 8-K kodları, kurum yayın başlığı, kaynak). Portföy,
pozisyon, kullanıcı kimliği **geçmiyor**. Ayrıca `BILDIRIM_ETKIN` varsayılanı
`0` — servis ayağa kalktığında kimseye mesaj gitmiyor. Yani "A'nın portföyü
B'ye" senaryosu bu yolda **kurulamaz**.

**Asıl açık başka yerdeydi — aynı adı taşıyan besleme ucu.**
`/api/bildirimler`, `bildirim-service`'in topladığı **sistem işletim
kayıtlarını** rol kapısı olmadan her oturum açmış kullanıcıya veriyordu.
Canlı yanıttan ölçülen satırlar:

```
[ana:claude1] ALARM: claude CALISMIYOR (pane_pid=3960990).
              Yeniden baslatiliyor: 'claude --continue' (ardisik deneme: 1/6)
godmode_paper MUTABAKAT ALARMI: Kontrol calistirilamadi ...
              ALARM: Haftalik egitim BASARISIZ veya HIC TETIKLENMEDI!
```

Yani otomasyonun tmux pencerelerinde yeniden başlatılan Claude oturumlarıyla
yürüdüğü, süreç kimlikleri ve iç sağlık durumu. Sınıf **SİSTEM-GİZLİ**,
kullanıcı-gizli değil — raporlar ucunda kapatılanla aynı sınıf. Çapraz
kullanıcı sızıntısı **değil** (içerik herkes için aynı), bu yüzden kullanıcı
bazlı bölmek yanlış çözüm olurdu; doğru çözüm rol kapısıdır.

**Alınan ders:** risk kaydına yazılan bir cümle, ölçülmeden önce bir
**hipotezdir**. R-9 iki ayrı bileşeni ("bildirim") tek ada bağladığı için
gerçek açığı gizliyordu.

---

## ÖLÇÜLEN DIŞ YÜZEY (20.09.2026) — tüm risk sıralamasını etkiler

Bugüne kadarki risk metinleri örtük olarak "kaydolan ilk gerçek müşteri"
senaryosuna dayanıyordu. O senaryonun ön koşulu ölçüldü ve **bugün
sağlanmıyor**:

| ölçüm | sonuç |
|---|---|
| `0.0.0.0`'ta dinleyen | yalnızca **22/tcp (sshd)** ve **443/tcp (stunnel4)** |
| stunnel 443 nereye bağlıyor | `connect = 127.0.0.1:22` — yani **SSH**, web değil |
| `alphawise-frontend` | `127.0.0.1:3000` — **dışarı açık değil** |
| diğer ~60 servis | hepsi `127.0.0.1` |
| dış tünel (cloudflared/ngrok/tailscale/frp) | **yok** |
| ufw | 22, 80, 443, 60000:61000/udp açık; 80'de dinleyen yok |

**Sonuç:** uygulamanın bugün **kamuya açık bir yüzeyi yok**; erişim host'a
SSH gerektiriyor. Bu, yapılan düzeltmeleri gereksiz kılmaz — yayına
alınmadan önce kapatılmaları doğru olan şeydir — ama **aciliyet
sıralamasını** değiştirir: R-7 ve R-13 bugün ne tarayıcıdan ne internetten
erişilebilir durumda (ayrıca hiçbir frontend rotası o uçlara referans
vermiyor, ölçüldü). Kalan gerçek yüzeyleri host kabuğu erişimi ve
`alphawise-net` içinden SSRF'tir — farklı bir sınıf.

---

## R-7 — iddia ölçümle çürütüldü (20.09.2026)

Özgün iddia: *"`/oz-iyilestirme/uygula` küresel strateji parametrelerini
değiştirir → bir kullanıcının ayarı ötekinin karar kodunu değiştirir."*

Ölçüm, korumanın **iki katmanda zaten var** olduğunu gösterdi:

1. **Servis:** dört `/oz-iyilestirme` ucunun dördü de `yetki(x_admin_key)`
   çağırıyor. Canlı: anahtarsız `GET /oz-iyilestirme/durum` → `HTTP 401`.
   `PAPER_ADMIN_KEY` üretimde tanımlı (48 karakter), yani kapı gerçek
   doğrulama yapıyor ve fail-closed.
2. **Proxy:** `godmode-paper-trading-service/frontend/.../paper/[...yol]/route.ts`
   beyaz listesinde bu uçlar **hiç yok**; bilinmeyen yol `403`. Tek yazma
   yolu (`islem-modu`) admin anahtarını değil dar liste anahtarını kullanıyor.

**Gerçek boşluk asimetriydi:** proxy katmanı testle kilitliydi, servis
katmanı değildi. `0bef966` ile kapatıldı (8 test, 2 mutasyon).

---

## R-13 — "gerçek emir" yanlıştı; asıl bulgu paylaşılan hesap

**Düzeltilen niteleme:** `/mode-a/execute` gerçek para emri göndermiyor.
`get_trading_client()` içinde `paper=True` **sabit kodlu** ve tek kurulum
noktası (`godmode/execution/src/main.py:24`). Alpaca **paper** hesabı.

**Yerinde bulunan dört kapı:** `paper=True` sabit · `/health` dışında 8 ucun
8'inde `verify_admin` ilk ifade · `confirm` varsayılanı `False` ve kapı
`submit_order`'dan önce · piyasa kapalıysa `BLOCKED_MARKET_CLOSED`.
Hiçbiri testli değildi; `c8b3563` ile kilitlendi (13 test, 4 mutasyon).

### Paylaşılan broker hesabı — ilk iddiam YANLIŞTI, geri alındı

İki servis gerçekten aynı Alpaca paper hesabını kullanıyor
(`PA30SBB6QS52`; `ALPACA_API_KEY` ile `ALPACA_PAPER_API_KEY`'in
`sha256[:16]`'ları birebir `eb8885988aadb469`).

Bunu önce *"belgelenmemiş bir bağlantı"* diye kaydettim. **Yanlıştı.**
Paylaşım `godmode-paper-trading/src/main.py` içinde **altı ayrı yerde**
belgeli ve etkileri tek tek ele alınmış:

| satır | ne yapılmış |
|---|---|
| 343 | Hesap geneli değeri döndüren uç, *"bu değer godmode/execution gibi AYNI paper hesabını kullanan diğer servislerin pozisyonlarını da içerir"* notunu taşıyor |
| 681-699 | Eski "defter == broker" kapısının **arıza** ürettiği ölçülmüş (NVDA/CAT/GOOGL/WDC kalıcı BEKLE) ve kapı düzeltilmiş |
| 731-738 | Broker fazlası açıkça *"başka bir servise aittir"* diye etiketleniyor, ayrı alan olarak raporlanıyor |
| 740-744 | Satış tarafında otorite broker: `etkin_adet = min(defter, broker)` |
| 767-774 | **Toplam maruziyet bilerek DEFTERDEN hesaplanıyor**, broker hesap genelinden değil — gerekçesi ve 02.09.2026 ölçümü (`73.575`'i godmode/execution'a ait) yazılı |
| 980-982 | Pozisyon karşılaştırması bilerek tek yönlü |

Yani ekip bu bağlantıyı benden önce ölçmüş, niceliklendirmiş ve
sınırlamış. Benim "boyutlandırma paylaşılan tabandan türüyor" cümlem de
yanlıştı: maruziyet ve boyutlandırma defterden geliyor.

### ⚠ R-15 (YENİ, AÇIK) — zarar eşiğinde pay/payda uyuşmazlığı

Geriye **tek ve dar** bir gözlem kalıyor; bu, yukarıdaki altı yerin
hiçbirinde ele alınmamış:

```python
# main.py:544, 1259
pv = float(istemci().hesap().get("portfolio_value", 0))        # PAYLASILAN hesap
zarar_durumu = risk.zarar_durumu_belirle(
    pv, defter.kar_zarar({}, "US").get("gerceklesen_kar", 0.0)) # YALNIZCA defter

# risk.py:125
if gerceklesen_kar < 0 and abs(gerceklesen_kar) >= portfoy_degeri * 0.20:
    return DURDURULMUS
```

**Pay defterden, payda paylaşılan hesaptan.** Ölçülen değerlerle:

| | |
|---|---|
| eşik (`%20 × portfoy_degeri`) | **20.212 $** |
| defterin bağlı sermayesi (MSFT) | **9.876 $** |
| defterin gerçekleşen zararı | **0,00 $** |

Yani "zarar eşiği aşılırsa sistem kendini kapatır" güvencesi, bu servisin
kendi kitabının **iki katından fazla** bir zarara ayarlanmış durumda —
pratikte bu servis için **tetiklenemez**. Tehlike üretmiyor (paydayı
büyüten şey başkasının sermayesi, kendi emirlerini serbestleştirmiyor),
ama güvence **iddia ettiği kadar dar değil**.

- **Olasılık:** kesin (ölçüldü) · **Etki:** düşük-orta (paper parası;
  kapı yanlış tarafa değil, gevşek tarafa kayıyor) · **Y11:** hayır
- **Neden kapatılmadı:** `src/main.py` Y1 korumalı ve payda seçimini
  değiştirmek bir ticaret sisteminin durdurma eşiğini değiştirir — **D3**.
- **Seçenekler:** (a) paydayı defter sermayesinden türetmek (D3, korumalı
  dosya); (b) iki yüzeye ayrı paper hesabı — kod değişikliği gerektirmez,
  yalnızca altyapı; (c) bilinçli kabul edip **bu satırın yanına da** diğer
  altı yerdeki gibi bir not düşmek — en ucuzu.

---

## R-14 (yeni) — deponun kendi korunan listesi Y1'den geniş

`strateji.py` ve `risk.py` tam blob SHA-1 ile kilitli (`korunan_dosya_manifesti.py:27`),
`simulasyon.py` ve `main.py` AST ile. Risk tavanı / pozisyon boyutlandırma mantığı
`risk.py`'de yaşıyorsa, kullanıcı başına kota oraya **dokunamaz**.
**Olasılık:** kesin · **Etki:** orta · **Y11:** hayır ·
**Azaltma:** Faz 2'de `risk.py`'nin kullanıcı boyutuna ihtiyaç duyup duymadığı
ölçülür; duyuyorsa bu ikinci bir Y8 istisnası talebidir.
