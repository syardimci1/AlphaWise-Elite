# Karar İsabeti Ölçütü — Düzeltme

**Madde 47** — *TradingGoose referansı / isabet ölçütü*
**Tarih:** 10 Eylül 2026

## Kullanıcı kararları

Üç seçim kullanıcıya bırakıldı ve şöyle karara bağlandı:

1. **Korunan `maa/src/main.py`'ye dokunulmadı** — düzeltme yanına kuruldu.
2. **TUT ölçütü piyasaya göreli ±%10** oldu.
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

## Ölçülen tabanlar

21 sembol (karar evrenindekiler dahil), 30 iş günlük **630 pencere**, piyasa
vekili **SPY**:

| ölçüt | taban oranı |
|---|---:|
| EKLE: getiri > 0 | %50,6 |
| DİKKAT ET: getiri < 0 | %49,0 |
| **TUT (eski): \|getiri\| < %15** | **%75,9** |
| **TUT (yeni): \|getiri − piyasa\| < %10** | **%58,4** |

Eski TUT ölçütü kendiliğinden %75,9 oranında sağlanıyordu. EKLE ve DİKKAT ET
ölçütleri ise yazı-tura civarında, yani **ayırt edici** — bu yüzden bilerek
değiştirilmedi. Değiştirmek, eski değerlendirmeyle karşılaştırılabilirliği de
bozardı.

## Neden mutlak değil, piyasaya göreli

Mutlak bant TUT'u **düz bir piyasada kendiliğinden ödüllendirir** ve tersi de
doğrudur: tüm piyasa %20 düşerken TUT kararı makul olabilir ama mutlak ölçüt
onu "yanlış" sayar. Göreli bant bu iki hatayı da yapmaz.

Bedeli: değerlendirme anında bir piyasa vekili getirisi gerekiyor. Vekil o
pencerede okunamazsa sonuç **`olculemedi`** olur — **sıfır varsayılmaz**, çünkü
sıfır varsaymak düz bir piyasa varsaymaktır.

## BEKLE neden puanlanmıyor

BEKLE, geçerli katman sayısı 3'ün altına düştüğünde üretilir; yani
**"ölçemedik"** demektir. Fiyat hareketine bakıp doğru/yanlış demek,
ölçülemedi'yi bir piyasa çağrısına çevirir — bu depoda `232d1a0` ile kapatılan
hatanın ta kendisi.

Eski durumda `was_correct = None` yazılıyordu ve bu **"henüz
değerlendirilmedi"** ile ayırt edilemiyordu. Yeni alan ikisini ayırıyor:
`uygulanamaz` (bir daha denemenin anlamı yok) ile boş (henüz sırası gelmedi).

Aynı kural Anayasa dışı kodlara da uygulanıyor: `BELIRSIZ` ve `risk_on` bir
piyasa çağrısı değil, puanlanmıyor.

## Yan bulgu: sıfır günlük değerlendirme penceresi

`decision_log` id=2 kaydının kararı ve değerlendirmesi **aynı gün**
(2026-07-21 → 2026-07-21). Getirisi %0,12 ve eski ölçütte **"doğru"**
işaretlenmiş. Sıfır günlük bir pencerenin getirisi karar hakkında hiçbir şey
söylemez. Yeni ölçüt en az 20 günlük pencere şart koşuyor; bu kayıt artık
`olculemedi`.

## Sonuç: eski ve yeni yan yana

```
ESKI OLCUT (main.py, DEGISTIRILMEDI)
  EKLE       27/38  %71,0  GA=[%55,2 , %83,0]  taban %50,6  -> TABANIN USTUNDE
  DIKKAT ET  11/30  %36,7  GA=[%21,9 , %54,5]  taban %49,0  -> sanstan ayirt edilemedi
  TUT        17/18  %94,4  GA=[%74,2 , %99,0]  taban %75,9  -> sanstan ayirt edilemedi

YENI OLCUT (goreli_sonuc)
  EKLE       27/38  %71,0  GA=[%55,2 , %83,0]  taban %50,6  -> TABANIN USTUNDE
  DIKKAT ET  11/30  %36,7  GA=[%21,9 , %54,5]  taban %49,0  -> sanstan ayirt edilemedi
  TUT        11/17  %64,7  GA=[%41,3 , %82,7]  taban %58,4  -> sanstan ayirt edilemedi
```

TUT %94,4'ten %64,7'ye indi. **Yine "şanstan ayırt edilemedi" çıkıyor — ama
artık dürüst bir nedenle:** örnek 17 ve %64,7 ile %58,4 arasındaki fark bu
büyüklükte ayrılamıyor. Önceki hâlde sayı zaten anlamsızdı; şimdi anlamlı ama
**örnek yetersiz**. İkisi çok farklı durumlar.

**En önemli sonuç değişmedi ve olumlu:** EKLE kararları 38 örnekte %71,0 ile
%50,6 tabanının **tamamen üstünde** — güven aralığı tabanı içermiyor. Bu,
sistemin ölçülebilir tek net başarısı.

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

**Hayatta kalan mutasyon yok (0/7).** 60 yeni test; tam regresyon **932** geçti.

## Üretilen dosyalar

- `maa/src/isabet_olcut.py` — düzeltilmiş ölçütler
- `maa/src/isabet_calistir.py` — veritabanı koşucusu (kuru çalışma + `--yaz`)
- `maa/src/test_isabet_olcut.py` — 45 test
- `maa/src/test_isabet_calistir.py` — 15 test
