# Karar İsabeti Ölçütü — Düzeltme

**Madde 47** — *TradingGoose referansı / isabet ölçütü*
**Tarih:** 10 Eylül 2026

## Kullanıcı kararları

Üç seçim kullanıcıya bırakıldı ve şöyle karara bağlandı:

1. **Korunan `maa/src/main.py`'ye dokunulmadı** — düzeltme yanına kuruldu.
2. **TUT ölçütü piyasaya göreli ±%5** oldu (ilk seçim ±%10'du; taban ölçümüm yanlış çıkınca yeniden soruldu).
3. **BEKLE değerlendirilmiyor** ama nedeni yazılıyor.

## Önce bir düzeltme: daha önce eksik veriye bakmışım

Madde 47'yi ilk raporladığımda "102 karardan yalnızca 12'si değerlendirilmiş"
demiştim. O sayım **yalnızca katman skoru taşıyan satırları** filtreliyordu.
Tam kümede **99 değerlendirilmiş satır** var. Doğru tablo:

| karar | değerlendirilen | eski ölçütle doğru | oran |
|---|---:|---:|---:|
| EKLE | 38 | 27 | %71,0 |
| DİKKAT ET | 30 | 11 | %36,7 |
| TUT | 18 | 17 | %94,4 |
| BEKLE | 12 | — | puanlanmıyordu |
| BELİRSİZ | 1 | — | puanlanmıyordu |

Bu, ilk anlattığımdan **önemli ölçüde farklı** bir tablo ve bir bulguyu
değiştiriyor: **EKLE aslında şansın üstünde.**

## Ölçülen tabanlar — ve ilk ölçümümün yanlış olduğu

**Bu raporun ilk hâlinde yazdığım taban oranları yanlıştı.** Bağımsız bir
düşmanca doğrulama turu bunu yakaladı ve kendim yeniden ölçerek doğruladım.

İki hata birlikte çalışıyordu ve **ikisi de sonucu sistemin lehine bozuyordu**:

1. **Yanlış evren.** Tabanı, kararların gerçekten verildiği semboller yerine
   genel bir büyük-şirket listesiyle (MSFT, AAPL, META, TSLA…) ölçmüştüm.
   Gerçek karar evreni: ASML, CAT, GOOGL, JEPI, LLY, NVDA, O, SCHD, TSM, WDC.
2. **Yanlış pencere.** Seriyi `market-data`'nın `/price` ucundan almıştım ve o
   uç **varsayılan 60 bar** döndürüyor. 30 barlık ufukla bu, sembol başına
   **30 tamamen örtüşen pencere** demek — "630 gözlem" bağımsız değildi.

Doğru ölçüm (gerçek karar evreni, depodaki tam günlük geçmiş 2020–2026,
30 barlık ufuk, **n = 16.367 pencere**, piyasa vekili SPY):

| eşik | mutlak \|r\| | göreli \|r − r_SPY\| |
|---|---:|---:|
| ±%3 | %27,3 | %32,1 |
| **±%5** | %41,7 | **%47,7** ← seçilen |
| ±%6 | %47,9 | %54,4 |
| ±%10 | %65,7 | %73,0 |
| ±%15 | **%79,9** ← eski ölçüt | %87,0 |

**Somut zararı:** yanlış taban (0,584) verildiğinde 13/15 doğru bir TUT sayımı
"tabanın üstünde" yani **beceri** diye yargılanıyordu; doğru tabanla aynı sayım
"şanstan ayırt edilemedi" çıkıyor. Aynı veriden zıt iki yargı — ve yanlış olan,
sistemin lehine olandı.

### Eşik yeniden seçildi

Kullanıcı ilk seçimini "±%10, ölçülen taban %50,4" bilgisiyle yapmıştı. O sayı
yanlış olduğu için seçim yeniden soruldu ve **göreli ±%5** seçildi — gerçek
karar evreninde tabanı **%47,7**, yani asıl anlatılan yazı-tura referansı.

### Bu hata sınıfı artık testle kilitli

`maa/src/test_isabet_taban.py`, tabanı **depo verisinden yeniden hesaplayıp**
`isabet_olcut.py`'de belgelenen değere bağlıyor. Belgeye yazılan bir sayı
sessizce eskiyemez. Test veri yokken **atlanmıyor** — verinin varlığı ayrıca
sınanıyor, çünkü atlanan test hiçbir şey korumaz. Ayrıca örneklem büyüklüğünü
(>10.000) ve kalibrasyon eğrisinin şeklini de kilitliyor.

## Sonuç: eski ve yeni yan yana

```
ESKI OLCUT (main.py, DEGISTIRILMEDI)
  EKLE       27/38  %71,0  GA=[%55,2 , %83,0]  taban %50,6  -> TABANIN USTUNDE
  DIKKAT ET  11/30  %36,7  GA=[%21,9 , %54,5]  taban %49,0  -> sanstan ayirt edilemedi
  TUT        17/18  %94,4  GA=[%74,2 , %99,0]  taban %79,9  -> sanstan ayirt edilemedi

YENI OLCUT (goreli +-%5)
  EKLE       27/38  %71,0  GA=[%55,2 , %83,0]  taban %50,6  -> TABANIN USTUNDE
  DIKKAT ET  11/30  %36,7  GA=[%21,9 , %54,5]  taban %49,0  -> sanstan ayirt edilemedi
  TUT         6/17  %35,3  GA=[%17,3 , %58,7]  taban %47,7  -> sanstan ayirt edilemedi
```

TUT %94,4'ten **%35,3'e** indi. Yine "şanstan ayırt edilemedi" çıkıyor ama
artık dürüst bir nedenle: örnek 17 ve nokta tahmini tabanın **altında**.
Öncekinde sayı zaten anlamsızdı; şimdi anlamlı ama örnek yetersiz.

**En önemli sonuç değişmedi ve olumlu:** EKLE kararları 38 örnekte %71,0 ile
%50,6 tabanının **tamamen üstünde** — güven aralığı tabanı içermiyor. Bu,
sistemin ölçülebilir tek net başarısı.

## Doğrulama turunda bulunan diğer kusurlar

Bağımsız üç mercekle (doğruluk / "ölçülemedi ≠ sıfır" / korunan dosya ve veri)
20 iddia incelendi, 17'si doğrulandı. Kod düzeltmesi gerektirenler:

| kusur | ölçülen etki | düzeltme |
|---|---|---|
| Kontrol sırası ters: pencere önce bakılıyordu | kısa pencereli **BEKLE** `olculemedi` oluyordu, oysa `uygulanamaz` | karar kodu önce bakılıyor |
| `olculemedi` satırına piyasa getirisi 0,0 yazılıyordu | "piyasa düzdü" diye okunur — ölçülemedi'yi sıfıra çevirmek | ölçülmemiş satıra değer yazılmıyor |
| Piyasa hatasının **nedeni** gerekçeden atılıyordu | koşul tersti; neden tam da gerektiği anda siliniyordu | koşul düzeltildi |
| `/price` çağrısı **limit vermiyordu** | seri sessizce 60 bara kırpılıyor; eski kararlar ölçülemez olurdu | `limit=3000` + kapsam uyarısı |
| `ALTER TABLE` ile aynı işlemde 45 sn'lik HTTP çağrısı | hypertable + 8 parça üzerinde `AccessExclusiveLock`; ayrı bir veritabanında ölçüldü: paralel `INSERT` **9,06 sn** bloklandı | seri işlem açılmadan önce çekiliyor |
| `piyasa_getirisi` yalnızca **başlangıç** kapanışını doğruluyordu | bitiş kapanışı 0 iken uydurma **−%100** getiri üretiyordu | `if b <= 0 or s <= 0` |
| İkinci çalıştırma geçerli ölçümü ezebilirdi | veri penceresi kaydıkça ölçülmüş satır `olculemedi` olurdu | geçerli ölçüm ezilmiyor |
| `UPDATE ... WHERE id` | hypertable birincil anahtarı bileşik: `(id, decided_at)` | tam anahtarla yazılıyor |

Bir iddia sağlam kanıtla **çürütüldü**: "tanınmayan karar kodu `uygulanamaz`
sayılıyor" — doğrulayıcı, o satırların `evaluate_decisions`'ın
`price_at_decision IS NOT NULL` süzgecine hiç girmediğini ve koşucuya
ulaşmadığını canlı veriyle gösterdi (31 `risk_on` satırının 0'ı
değerlendirilmiş).

## Korunan dosya ve veri güvenliği

- `maa/src/main.py` **hiç açılmadı**; SHA'sı oturum başıyla birebir aynı.
- `was_correct` alanı **değişmedi**: yazma öncesi 55 doğru / 86 puanlı / 224
  toplam; yazma sonrası **birebir aynı** (yedekle karşılaştırıldı).
- Şema değişikliği **yalnızca ekleme**: dört yeni sütun
  (`goreli_sonuc`, `goreli_gerekce`, `goreli_piyasa_getirisi`, `goreli_zaman`).
  Hiçbir sütun silinmedi ya da türü değişmedi.
- Yazma öncesi tam yedek alındı:
  `yedekler/decision_log_madde47_20260910_215154.csv` (224 kayıt).
  Not: `decision_log` bir **TimescaleDB hypertable**; `pg_dump -t` yalnızca boş
  ana tabloyu veriyor — yedek `COPY (SELECT ...)` ile alındı.

## Şüphecilik turu

| # | mutasyon | sonuç |
|---|---|---|
| M1 | BEKLE'yi de puanla | YAKALANDI (6 fail) |
| M2 | piyasa getirisi yoksa sıfır varsay | YAKALANDI |
| M3 | TUT'u yine mutlak ölç | YAKALANDI |
| M4 | Anayasa dışı kodları da puanla | YAKALANDI (5 fail) |
| M5 | sıfır günlük pencereyi kabul et | YAKALANDI (5 fail) |
| M6 | piyasa fiyatında ileri de bak (geleceğe bakma) | YAKALANDI |
| M7 | EKLE'yi de göreli yap | YAKALANDI |

**Hayatta kalan mutasyon yok (0/15).** Üç tur mutasyon çalıştırıldı: ilk yedi ölçüt mantığını, sonraki dördü doğrulama turunda bulunan kusurları, son dördü kapsam ve kilit düzeltmelerini kilitliyor.

## Üretilen dosyalar

- `maa/src/isabet_olcut.py` — düzeltilmiş ölçütler
- `maa/src/isabet_calistir.py` — veritabanı koşucusu (kuru çalışma + `--yaz`)
- `maa/src/test_isabet_olcut.py` — 45 test
- `maa/src/test_isabet_calistir.py` — 15 test
