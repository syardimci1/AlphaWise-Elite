# Backtest ↔ Canlı Kod-Yolu Parite Denetimi — 9 Eylül 2026

## Neden bu denetim yapıldı

NautilusTrader'ın mühendislik dersi şudur: bir sistemin **backtest'te kullandığı
kod yolu ile canlıda kullandığı kod yolu ayrışırsa**, backtest sonuçları canlı
davranışı temsil etmez — ve bu ayrışma **sessizdir**. Kimse hata almaz; sayılar
üretilmeye devam eder, yalnızca anlamları değişir.

Bu rapor, o ayrışmanın bu depoda nerede olduğunu **ölçerek** tespit eder.

## Yöntem ve dürüstlük notu

Dört bağımsız açıdan (sinyal, veri, maliyet, karar) tarama yapıldı. Ardından
"kesin" olarak işaretlenen her iddia, onu **çürütmekle görevli ayrı bir
incelemeye** verildi.

Sonuç: **8 iddia onaylandı, 2 iddia çürütüldü.** Çürütülenler bu raporda da
yer alıyor — çünkü "ölçtük ve önemsiz çıktı" da bir bulgudur ve tekrar
araştırılmasını önler.

Hiçbir dosya değiştirilmedi, hiçbir konteyner yeniden başlatılmadı, ücretli
veya kotalı hiçbir uç çağrılmadı.

---

## A. TAA /backtest ↔ MAA /decide

### A1. Aynı isimli RSI, iki farklı kütüphane, iki farklı formül — ONAYLANDI

| | |
|---|---|
| Backtest | `taa/src/walkforward.py:71` → `vbt.RSI.run(...)` — vectorbt, `ewm=False`, **basit** hareketli ortalama |
| Canlı | `taa/src/main.py:109` → `talib.RSI(close, 14)` — TA-Lib, **Wilder** yumuşatması |

Gerçek merkezi depo verisiyle ölçüldü:

| Sembol | Ortalama fark | Maksimum fark | Eşik kararının ayrıştığı bar oranı |
|---|---|---|---|
| MSFT (1677 bar) | 6,28 puan | 26,72 puan | %17,9 |
| NVDA (6947 bar) | 6,63 puan | 33,02 puan | %16,7 |
| AAPL | 6,83 puan | 30,14 puan | %21,0 |

Etkisi kozmetik değil. Backtest'in giriş koşulu (`rsi<30 & sma20>sma50`) kaç
gün tetikleniyor:

| Sembol | Backtest RSI'ıyla | Canlı RSI'ıyla |
|---|---|---|
| MSFT | 57 gün | **2 gün** |
| NVDA | 194 gün | **20 gün** |
| AAPL | 81 gün | **8 gün** |

Yani backtest, canlı sistemin fiilen üretemeyeceği bir işlem sıklığını ölçüyor.

### A2. Parametreler: backtest optimize ediyor, canlı sabit — ONAYLANDI

Backtest her 252 günlük pencerede 90 kombinasyonluk ızgaradan en yüksek
Sharpe'li seti seçiyor (`walkforward.py:53-59`, `154-177`). Canlı ise
14/20/50'ye gömülü (`taa/src/main.py:109-111`).

Walk-forward örnek-dışılığı bu farkı **kapatmaz**: örnek-dışı olan parametre
*seçimidir*; canlı ise seçim yapmıyor.

### A3. Karar cebri farklı — ONAYLANDI

Backtest: `giris = (rsi < alt) & (sh > yv)` — iki koşulun **kesişimi**, uzun/nakit.
Canlı `score_taa` (`maa/src/main.py:427-455`): dört bileşenin **toplamı**, −4..+4.

Canlı skorun dört bileşeninden **ikisi backtest'te hiç hesaplanmıyor**:
destek/direnç içindeki konum ve hacim oranı. Bu iki bileşen ±2 puan katkı
sağlıyor — EKLE eşiğinin yarısı — ve hiçbir geçmiş veriyle sınanmamış.

Ölçüldü: backtest girişinin tetiklendiği MSFT'teki 57 günün hiçbirinde canlı
`score_taa` +4'e ulaşmıyor (30 günde +1, 21 günde +2, 6 günde +3). Ters yönde:
canlı `score_taa ≥ 2` olan günlerin yalnızca %30,7'sinde backtest girişi açık.

### A4. Aynı-bar icra: bir bar ileriye bakış — ONAYLANDI

`vbt.Portfolio.from_signals(kapanis, giris, cikis, ...)` — fiyat argümanı
sinyalleri üreten kapanış serisinin kendisi, gecikme yok. Ölçüldü: sinyal
barının kapanışı 13,00 → emir 13,013 (aynı bar + kayma).

Canlıda T kapanışı bilindiğinde o kapanıştan artık işlem yapılamaz; en erken
T+1'dir. `walkforward.py`'deki look-ahead notları yalnızca **parametre
seçimini** kapsıyor; **icra gecikmesi hiçbir yerde ele alınmamış**.

### A5. /backtest yetim bir uç — ONAYLANDI

Depoda `/backtest` ucunu çağıran **hiçbir kod yok** (tanımının kendisi hariç
tek eşleşme yok). Sonuç canlı karara geri beslenmiyor ve **iki yolun uyuştuğunu
denetleyen bir test de yok**.

### A6. Farkın bildirimi eksik ve yanıltıcı — ONAYLANDI

`taa/src/main.py:226` kapsam notu "FAA/RAA/SAA dahil değil" diyor. İki kusuru
var: (a) **Chronos'u saymıyor** — canlıda beşinci katman var; (b) "TAA'nın
teknik mantığı" ifadesi yanlış — test edilen kural `score_taa`'nın kuralı
değil. MAA `/decide` yanıtında backtest'e dair tek kelime yok.

> Bu dosya **korunmuş** olduğu için düzeltilmedi; yalnızca raporlanıyor.

---

## B. Veri konvansiyonu

### B1. Merkezi CSV deposunda iki farklı temettü-düzeltme konvansiyonu — ONAYLANDI

Aynı dosyanın içinde eski satırlar Tiingo'nun temettü-düzeltilmiş fiyatları
(`factor<1`), yeni satırlar defeatbeta'nın ham fiyatları (`factor=1.0`).

400 dosyalık örnekte **98 dosyada bu dikiş var; 70'inde dikiş canlı yolun
okuduğu son 130 barın içinde.** Medyan tek-günlük yapay getiri %0,65, p90 %1,84.

Backtest test pencereleri neredeyse tamamen düzeltilmiş bölümde; canlı karar
penceresi ham bölümde **ve dikişin üzerinde**.

### B2. `factor` sütunu yazılıyor ama hiç okunmuyor — ONAYLANDI

Dikiş tespit edilebilir olmasına rağmen (`factor 0,99783 → 1,0`) hiçbir kod
bunu kullanıp seriyi tek konvansiyona getirmiyor. Yani ayrışma yalnızca sessiz
değil, **mevcut kodla geri alınamaz** da.

### B3. Çürütülen iddia: "canlı 130 bar, backtest 1300 bar" — ÖNEMSİZ

Olgu doğru, **etkisi ölçülünce sıfır çıktı**: Wilder RSI(14) için 252 hissede
medyan fark 0,0015 puan, maksimum 0,046 puan ve 30/70 eşiği **0/252 hissede**
değişiyor (130 barda 116 özyineleme, (13/14)^116 ≈ 1,9e-4). SMA50 farkı tam sıfır.

### B4. Çürütülen iddia: "pencere sonunda zorunlu pozisyon kapama"

Olgular doğru ama çıkarım yanlış: bu bir backtest↔canlı ayrışması değil,
walk-forward muhasebe kuralı.

---

## C. İşlem maliyeti

Üç ayrı standart ölçüldü:

| Yol | Emir başına | Gidiş-dönüş |
|---|---|---|
| TAA walk-forward | 20,00 bps | 39,92 bps |
| Kâğıt işlem backtest'i | 11,60 bps | 23,20 bps |
| Canlı defter (gerçek dolumlar) | 10 bps komisyon + **ölçülen kayma 0,60–2,26 bps** | — |

İki sonuç:

1. TAA backtest'i kâğıt/canlı yola göre sistematik olarak **kötümser**; iki
   motorun sonuçları karşılaştırılamaz.
2. Kâğıt işlem servisi **kendi beyan ettiği §8.6 maliyetini uygulamıyor**:
   dışarıya `%0,20` raporluyor, gerçekte `%0,116` uyguluyor (~1,7 kat fark).

Ayrıca stop-loss'ta deftere yazılan "kayma", icra kayması değil **gece
boşluğudur** — referans olarak önceki günün kapanışı kullanılıyor. Bu, TCA
ölçümünü kirletiyor.

---

## D. En ciddi bulgu: paylaşılan çekirdek iddiası bugün geçersiz

`godmode-paper-trading-service/src/simulasyon.py:1-27` açıkça NautilusTrader
ilkesini iddia ediyor: *"karar mantığı tek bir yerde durur"*. Ve `karar_dongusu()`
gerçekten paylaşılıyor.

**Ama ölçüldü:** izlenen 44 sembolün **44'ünün de strateji planı var**. Bu yüzden
canlı yol `main.py:657-658`'de `strateji.strateji_karar_dongusu`'ne sapıyor ve
backtest'in koştuğu bant-tabanlı çekirdek **canlıda hiç çalışmıyor**.

Otomasyon logları bunu doğruluyor: 01–03.09'da `konum=giris_bolgesinde/AL`
(bant yolu), 04.09'dan itibaren **176/176 kayıt** `konum=strateji_beklemede/BEKLE`
(plan yolu).

Yani paylaşılan çekirdek iddiası **bugünkü sembol kümesinin %100'ü için
geçersiz**. Canlıda emri üreten stop-loss / trailing-stop / kademeli giriş
mantığı backtest'te hiç koşmuyor.

Ek olarak: backtest bantları kapanış-only **ATR vekiliyle** üretiyor, canlı
gerçek `talib.ATR(high, low, close, 14)` kullanıyor. Ölçüldü — vekil/gerçek
oranı 10 sembolde **0,50–0,69** (medyan ~%45 dar bant).

---

## Gerçekten paylaşılan kod yolları (iyi haber)

- `taa/src/main.py:13` `get_price_data()` — canlı `/analyze` ve `/backtest`
  **aynı** fonksiyonu ve aynı merkezi depoyu kullanıyor.
- `market-data-service/src/main.py:70` `read_central_csv()` + imkânsız-bar
  süzgeci — canlı ve backtest okumalarında ortak.
- `godmode-paper-trading-service/src/karar.py:132-210` `karar_uret()` — saf
  fonksiyon, bant yolunda gerçekten ortak.
- `godmode-paper-trading-service/src/risk.py:106-215` `emir_kontrol()` — bant
  yolu, plan yolu ve backtest aynı ön-işlem risk kontrollerini çağırıyor.

---

## Bu rapor ne YAPMADI

Hiçbir ayrışma **düzeltilmedi**. Gerekçe:

- `taa/src/main.py` ve `maa/src/main.py` **korunmuş dosyalardır**.
- RSI kütüphanesini birleştirmek (vectorbt→TA-Lib veya tersi), yayımlanmış
  backtest sonuçlarının tamamını değiştirir; bu, ölçülmeden ve onaylanmadan
  yapılacak bir değişiklik değildir.
- Veri konvansiyonu dikişini onarmak, merkezi deponun yeniden üretilmesini
  gerektirir.
- Kâğıt işlem servisi ayrı bir depodur ve canlı emir gönderir.

Bunların her biri **ayrı bir karar** gerektirir. Bu raporun işi, kararı
verecek kişinin elinde **ölçülmüş sayılar** olmasını sağlamaktır.

---

## Denetim tek seferlik bırakılmadı: parite ölçeri

`taa/src/parite.py` — ayrışmayı **sayıya çeviren** çalıştırılabilir araç.
İşi düzeltmek değil, **ölçmek**: fark görünür olur, zamanla büyüyüp büyümediği
izlenebilir ve "iki yol aynı" varsayımı testle engellenir.

Modül TA-Lib veya vectorbt'ye bağımlı değil; iki formülü de açıkça uyguluyor.
Aynı sonucu ürettikleri **testle kilitlendi** (konteynerde, atlamasız):

- `rsi_wilder` ↔ `talib.RSI` — maksimum fark **< 1e-6**
- `rsi_basit` ↔ `vbt.RSI.run` — maksimum fark **< 1e-6**

Aracın gerçek merkezi depo verisiyle bağımsız ölçümü (5 yıl, 1286 bar):

| Sembol | Ort. RSI farkı | Maks. fark | Eşik kararının ayrıştığı bar | Giriş koşulu: backtest | Giriş koşulu: canlı |
|---|---|---|---|---|---|
| MSFT | 6,39 | 26,72 | %18,9 | 48 gün | **2 gün** |
| NVDA | 6,38 | 27,56 | %14,9 | 27 gün | **3 gün** |
| AAPL | 7,06 | 30,14 | %21,6 | 71 gün | **7 gün** |
| KO   | 6,71 | 28,92 | %18,4 | 37 gün | **4 gün** |

Bir test, ayrışmanın **hâlâ var olduğunu** kilitliyor. İki yol ileride
birleştirilirse o test düşer ve bu raporun güncellenmesi gerektiği anlaşılır —
"aynı olduğunu varsayma" hatası bir daha sessizce oluşamaz.
