# R-15 — İKİ EMİR YÜZEYİNE AYRI PAPER HESABI (Seçenek B)

**Tarih:** 20 Eylül 2026 · **Karar:** kullanıcı **B**'yi seçti
**Durum:** ⏸ **KİMLİK BİLGİSİ BEKLİYOR** — kod tarafı hazır, kabul testi yazıldı

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

**İki temiz yol var:**

| yol | ne gerektirir | maliyeti |
|---|---|---|
| **B1** — MSFT 20 bilinçli kapatılır, sonra geçilir | paper-trading'in kendi satış yolu (`emir_gonder(..., "SAT")`), kendi pozisyonu | K/Z **realize edilir** (kâğıt para) |
| **B2** — defter doğal olarak düzleşene kadar beklenir, o pencerede geçilir | strateji pozisyonu kendi kapattığında geçmek | **sıfır zorlama**, ama zamanlama beklemeye bağlı |

B2 daha temiz; B1 daha hızlı. Karar kullanıcınındır — ikisi de bir **emir
işlemi** içerdiği ve işleyen bir defteri etkilediği için otonom yapılmadı.

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
# 0) ON KOSUL: defter duz mu?
docker exec godmode-paper-trading python3 -c "..."   # defter_pozisyonlari bos olmali

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
