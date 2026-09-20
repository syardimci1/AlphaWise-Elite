# R-15 — İKİ EMİR YÜZEYİNE AYRI PAPER HESABI (Seçenek B)

**Tarih:** 20 Eylül 2026 · **Karar:** kullanıcı **B**'yi seçti
**Yol:** **B2** — defter doğal olarak düzleşince geçilir (zorla kapatma yok)
**Durum:** ⏸ **İKİ ÖN KOŞUL BEKLİYOR** — (1) ikinci hesabın anahtarları,
(2) defterin düzleşmesi. Kod tarafı hazır; iki betik de yazıldı ve sınandı.

---

## Kapatılacak açık

```python
# godmode-paper-trading-service/src/main.py:544, 1259
pv = float(istemci().hesap().get("portfolio_value", 0))        # PAYLASILAN hesap
zarar_durumu = risk.zarar_durumu_belirle(
    pv, defter.kar_zarar({}, "US").get("gerceklesen_kar", 0.0)) # YALNIZCA defter
# risk.py:125 -> abs(gerceklesen_kar) >= pv * 0.20 -> DURDURULMUS
```

Pay bir kitaptan, payda iki kitabı da içeren hesaptan. Ölçülen: eşik
**20.212 $**, defterin bağlı sermayesi **9.876 $**. Yani durdurma güvencesi
bu servis için pratikte tetiklenemiyor.

Seçenek B bunu **kod değiştirmeden** kapatır: paydayı oluşturan hesap
yalnızca o servise ait olursa, oran doğru hâle gelir.

---

## ⚠ GÖÇ YÖNÜ — ölçümle belirlendi, sezgiyle değil

İlk sezgi "emir yüzeyi (execution) taşınsın" yönündeydi. **Ölçüm bunu
çürüttü.** Bugünkü durum:

| | |
|---|---|
| paylaşılan hesap | `PA30SBB6QS52`, öz sermaye **101.060,52 $** |
| paper-trading defterinin iddiası | `MSFT 20.0` — broker'da da **20.0**, mutabık |
| execution'ın açtığı 11 pozisyon | **74.121,31 $** — ASML, CAT, GOOGL, LLY, NVDA, RTX, SCHD, SOXL, TSM, WDC, WMT |

### Neden `execution` taşınmamalı

`godmode/execution`'da **kapatma/satış ucu yok** — yalnızca iki alım ucu
(`/mode-a/execute`, `/mode-b/execute`). Ölçüldü. Yani execution yeni hesaba
geçerse o 11 pozisyon (74.121 $) eski hesapta **sistem içinde kapatılma yolu
olmadan** kalır; üstelik paper-trading'in `pv`'si onları saymaya devam eder
ve **R-15 kapanmaz**.

### Neden `paper-trading` taşınmalı

Yeni hesaba geçtiğinde `pv` yalnızca kendi sermayesini yansıtır → R-15
**kapanır**. 11 pozisyon eski hesapta, onları açan servisle (execution)
birlikte kalır — sahibinin yanında, öksüz değil.

### ⚠ Tek ön koşul: defter DÜZ olmalı

Yeni hesapta pozisyon yoktur. Defter `MSFT 20` iddia ederken geçilirse:

```
fark = defter(20) - broker(0) = 20 > 0
-> emir_engelli = True
-> "DEFTER FAZLA IDDIA EDIYOR (hayalet pozisyon). Emir gonderilmez."
```

Yani servis **emir gönderemez hâle gelir**. Bu bir arıza değil, tam olarak
o kapının işi — ama geçişin bu durumda yapılmaması gerekir.

**KARAR (20.09.2026): B2** — defter doğal olarak düzleşene kadar beklenir,
o pencerede geçilir. Pozisyon **zorla kapatılmaz**; sıfır zorlama, sıfır
zorunlu K/Z. (Reddedilen alternatif B1: MSFT 20 bilinçli kapatılıp hemen
geçilmesiydi — daha hızlı ama kâğıt K/Z realize ederdi.)

### B2 — düzleşme ne zaman gerçekleşir (ölçüldü 20.09.2026)

MSFT'nin **gerçek bir çıkış planı** var:

| | fiyat | pozisyonun kapanan payı | canlı fiyata uzaklık |
|---|---|---|---|
| canlı fiyat | **493,10** | — | — |
| çıkış hedefi 1 | 517,75 | %40 | **+%5,00** |
| çıkış hedefi 2 | 531,90 | %35 | +%7,87 |
| çıkış hedefi 3 | 542,01 | %25 | +%9,92 |
| **stop-loss** | **489,41** | %100 | **−%0,75** |

Trailing stop hedef 1'de devreye giriyor, %3,5 takip.

**Okuma:** hedeflerden yalnızca 1'ine ulaşmak defteri düzleştirmez
(%40 kapanır). **Tam düzleşmenin en yakın yolu stop-loss** — yalnızca
%0,75 uzakta. Yani pencere yakın zamanda açılabilir.

**Pencere ne kadar kalır:** defterde toplam **8 işlem kaydı** var ve
sonuncusu **01.09.2026**. Yani servis yavaş çalışıyor; düzleştikten sonra
hemen yeni pozisyon açması beklenmiyor — pencere dar olmayacak.

**Dikkat:** 44 sembol izleniyor ve hepsi `ACIK` (yeni risk alabilir). Yani
düzleşme kalıcı değildir; yeni bir giriş defteri tekrar doldurabilir.
Bu yüzden ön koşul **her geçişten hemen önce** yeniden ölçülmelidir.

---

## Gereken tek şey: ikinci Alpaca paper hesabı

**BEKLEYEN_KARAR — kullanıcıdan:** ikinci bir Alpaca **paper** hesabının
anahtar çifti. (Alpaca panelinden yeni bir paper hesabı açılır; mevcut
hesabı sıfırlamak GEREKMEZ ve önerilmez — 11 pozisyon orada kalmalı.)

Anahtarlar şu dosyada, **2 satır**:

```
/opt/alphawise/godmode-paper-trading-service/.env
  satir 1: ALPACA_PAPER_API_KEY=...
  satir 2: ALPACA_PAPER_SECRET_KEY=...
```

`godmode/execution/.env` (satır 24-25) **değişmez** — eski hesapta kalır,
11 pozisyonun sahibi odur.

---

## Uygulama adımları (kimlik bilgisi gelince)

```bash
# 0) ON KOSUL: defter duz mu?  (B2 dedektoru — cikis 0 beklenir)
bash /opt/alphawise/commercial/AlphaWise-Elite/kanit/r15_gecis_hazir_mi.sh

# 1) YEDEK
cp /opt/alphawise/godmode-paper-trading-service/.env{,.r15_yedek}

# 2) IKI SATIR degisir (yalnizca paper-trading)
#    ALPACA_PAPER_API_KEY / ALPACA_PAPER_SECRET_KEY -> YENI hesap

# 3) YALNIZCA o konteyner yeniden kurulur
cd /opt/alphawise/godmode-paper-trading-service
docker compose -f docker-compose.paper.yml up -d --no-deps godmode-paper-trading

# 4) KABUL TESTI
bash /opt/alphawise/commercial/AlphaWise-Elite/kanit/r15_ayri_hesap_dogrula.sh
#    cikis 0 beklenir
```

**Geri alma:** `.env.r15_yedek` geri kopyalanır, aynı `up -d --no-deps`
komutu çalıştırılır. Kod değişmediği için `git revert` gerekmez.

---

## Kabul testi

İki betik var ve ikisi de bugünkü durumda **doğru biçimde olumsuz** dönüyor:

| betik | ne ölçer | bugünkü çıkış |
|---|---|---|
| `r15_gecis_hazir_mi.sh` | B2 ön koşulu: defter düz mü | **1** — `{"MSFT": 20.0}` var |
| `r15_ayri_hesap_dogrula.sh` | sonuç: hesaplar ayrıldı mı | **1** — ikisi de `PA30SBB6QS52` |

`r15_gecis_hazir_mi.sh` arıza-güvenlidir: broker okunamazsa `2` döner ve
okunamayan bir defter **düz sayılmaz**. Karar mantığı dört senaryoda
doğrulandı (pozisyon var / düz+açık / düz ama kapı engelli / okunamadı).

`kanit/r15_ayri_hesap_dogrula.sh` — **bugün bilerek kırmızı**:

```
execution ALPACA_API_KEY           eb8885988aadb469
paper ALPACA_PAPER_API_KEY         eb8885988aadb469
execution hesap|oz sermaye         PA30SBB6QS52|101060.52
paper     hesap|oz sermaye         PA30SBB6QS52|101060.52
defterin bildigi sembol : ['MSFT']
brokerdaki YABANCI      : 11 [ASML, CAT, GOOGL, LLY, NVDA, RTX, SCHD, SOXL, TSM, WDC, WMT]
SONUC: AYNI ANAHTAR -> iki yuzey AYNI hesapta. R-15 ACIK.      (cikis 1)
```

Betik **sır yazdırmaz**: anahtarlar yalnızca `sha256[:16]` ile
karşılaştırılır. Hesap numarası Alpaca'nın açık kimliğidir.

**İki katmanlı kontrol** bilinçlidir — karar mantığı üç senaryoda
doğrulandı:

| senaryo | çıkış |
|---|---|
| aynı anahtar | 1 (açık) |
| farklı anahtar **ama aynı hesap** | 1 (açık) — aynı hesaba ikinci anahtar çifti üretmek ayrım sayılmaz |
| farklı anahtar, farklı hesap | 0 (kapalı) |

---

## Geçiş sonrası beklenen durum

| ölçüm | önce | sonra (beklenen) |
|---|---|---|
| iki servisin hesabı | aynı (`PA30SBB6QS52`) | **farklı** |
| paper-trading `pv` | 101.060 $ (%73,3'ü yabancı) | yeni hesabın kendi sermayesi |
| zarar eşiği (`%20 × pv`) | 20.212 $ | yeni sermayenin %20'si — **kendi kitabına oranlı** |
| broker'daki yabancı sembol | 11 | **0** |
| kabul testi çıkışı | 1 | **0** |

**Not:** `gerceklesen_kar` defterden gelmeye devam eder ve geçmişi taşır.
Bugün **0,00 $** olduğu için geçiş anında eşik sorunu yoktur; B1 yolu
seçilir ve MSFT zararla kapanırsa o zarar orana girer (yeni sermayeye göre
hâlâ eşiğin çok altında kalır).

---

## Kapsam dışı kalan (bilerek)

Anahtar yeniden kullanımı ayrı bir konudur ve bu planda ele alınmadı:
`paper-trading GODMODE_ADMIN_KEY` ile `godmode-execution ADMIN_KEY` aynı
sırdır (`sha256[:16] = 7e02b48a6b016f45`). Broker hesabı ayrılsa bile bu
paylaşım sürer. Ayrı bir karar konusudur.
