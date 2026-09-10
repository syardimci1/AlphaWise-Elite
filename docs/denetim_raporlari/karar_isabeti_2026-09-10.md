# Karar İsabeti — Şansla Karşılaştırmalı Ölçüm

**Madde 47** — *TradingGoose referansı*
**Tarih:** 10 Eylül 2026

## Alınan fikir

TradingGoose gibi çok ajanlı sistemlerin ayırt edici fikri **yansıma**dır:
geçmiş kararların sonucu ölçülür ve yeni kararlara geri beslenir. Kod
alınmadı, kurulmadı; alınan yalnızca bu fikir.

AlphaWise'da ölçüm **zaten var**: `decision_log.was_correct`,
`/evaluate-decisions`, `/performance-report`. Halka kurulmuş ama
**kapanmamış** — ve kapatmadan önce oranın kendisinin anlamlı olması
gerektiği ortaya çıktı.

## Bulgu 1: `/performance-report` ucunu hiçbir tüketici çağırmıyor

Depo genelinde arandı: uç `maa/src/main.py:943`'te tanımlı, ama frontend'de,
hiçbir serviste ya da betikte çağrılmıyor. Ölçüm üretiliyor, kimse okumuyor.

## Bulgu 2: 102 kararın yalnızca 12'si değerlendirilmiş

| durum | adet | ortalama yaş |
|---|---:|---:|
| değerlendirilmiş | 12 | 48,1 gün |
| değerlendirilmemiş | 90 | 18,6 gün |

`/evaluate-decisions` varsayılan olarak 30 günden eski kararlara bakıyor;
değerlendirilmemişlerin çoğu henüz o yaşta değil. Ama en eskisi 2026-07-21
tarihli, yani 51 günlük — eşiğin üstünde olduğu hâlde değerlendirilmemiş
kayıtlar var.

## Bulgu 3 (asıl bulgu): TUT ölçütü neredeyse her zaman sağlanıyor

Karar kuralı (`maa/src/main.py`, korunmuş — okundu, değiştirilmedi):

```
EKLE      doğru sayılır eğer  getiri > 0
DİKKAT ET doğru sayılır eğer  getiri < 0
TUT       doğru sayılır eğer  |getiri| < %15
BEKLE     hiç değerlendirilmez (was_correct = None)
```

TUT'un ölçütü ±%15'lik bir bant. Bunun ne kadar müsamahakâr olduğu gerçek
fiyatlarla ölçüldü — 12 sembol, 30 iş günlük 360 pencere:

| ölçüt | taban oranı |
|---|---:|
| TUT: \|getiri\| < %15 | **%71,9** |
| EKLE: getiri > 0 | **%41,1** |

Sembol bazında TUT tabanı %16,7 (MSFT) ile %100 (GOOGL, BAC) arasında
değişiyor. Ortalama %71,9.

> Bu taban ölçülen döneme özgüdür (60 barlık pencere, ~3 ay); genel bir
> piyasa sabiti değildir. Modül bunu her çıktıda bildirir.

## Sonuç: mevcut isabet rakamları şanstan ayırt edilemiyor

Gerçek verilerle:

```
EKLE   gözlem 4/7    oran %57,1   GA=[%25,1, %84,2]   taban %41,1
       -> ŞANSTAN AYIRT EDİLEMEDİ

TUT    gözlem 5/5    oran %100,0  GA=[%56,5, %100,0]  taban %71,9
       -> ŞANSTAN AYIRT EDİLEMEDİ

BEKLE  gözlem 0/0    -> ÖLÇÜLEMEDİ (ölçüt tanımlı değil)
```

**"TUT kararlarının %100'ü doğru" cümlesi tek başına hiçbir şey söylemez.**
Hiçbir bilgisi olmayan bir sistem de ~%72 alırdı ve n=5'te %100 ile %72
arasındaki fark istatistiksel olarak ayırt edilemez.

## Modülün kuralı

`maa/src/isabet.py`: gözlenen oranın güven aralığı taban oranını
**içeriyorsa**, sonuç "şanstan ayırt edilemedi" olarak raporlanır. Bu bir
başarısızlık değil, ölçümün durumudur — gizlenmesi, sistemin kendini
olduğundan iyi göstermesi demek olurdu.

Güven aralığı **Wilson** yöntemiyle hesaplanır. Normal yaklaşım (p ± z·se)
küçük örneklerde ve uç oranlarda (0/5, 5/5) **sıfır genişlikte** aralık
üretir ve yanıltır — mutasyon M3 bunu doğruluyor.

Örnek sayısı 5'in altındaysa oran hiç hesaplanmaz.

## Şüphecilik turu

| # | mutasyon | sonuç |
|---|---|---|
| M1 | taban kontrolünü kaldır (her oran başarılı görünür) | YAKALANDI |
| M2 | küçük örnekte de oran üret | YAKALANDI |
| M3 | Wilson yerine normal yaklaşım | YAKALANDI (3 fail) |
| M4 | yetersiz barlı sembolü taban 0 say | YAKALANDI |
| M5 | hiç örnek yokken taban 0 raporla | YAKALANDI |
| M6 | asgari örneği 1'e düşür | YAKALANDI |

**Hayatta kalan mutasyon yok (0/6).** 23 test.

## Bekleyen kararlar

1. **TUT ölçütü.** ±%15 bandı bilgi taşımıyor. Daha dar bir bant ya da
   piyasaya göreli bir ölçüt (örn. endeksten sapma) anlamlı olurdu. Ancak
   ölçüt korunmuş `maa/src/main.py` içinde ve Anayasa v4.4 kapsamında —
   **değiştirilmedi.**
2. **BEKLE hiç değerlendirilmiyor.** `was_correct` None bırakılıyor. Bir
   "beklemek doğru muydu" ölçütü tanımlamak da karar kuralına dokunmayı
   gerektirir.
3. **Halkanın kapanması.** `isabet.py` yazıldı ve testlendi ama canlı bir
   tüketiciye bağlanmadı — bağlamak `maa/src/main.py`'ye uç eklemeyi
   gerektirir ve o dosya korunmuş.

## Üretilen dosyalar

- `maa/src/isabet.py` — Wilson aralığı, taban karşılaştırması, taban ölçümü
- `maa/src/test_isabet.py` — 23 test
