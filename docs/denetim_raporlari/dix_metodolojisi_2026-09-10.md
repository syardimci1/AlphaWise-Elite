# DIX Metodolojisi — Denetim ve Uygulama

**Madde 41** — *DIX metodolojisi*
**Tarih:** 10 Eylül 2026

## Kısa sonuç

Sistemdeki mevcut DPKE göstergesi, DIX'in **hesaplanamaz** olduğunu belgeleyen
açık bir uyarı taşıyor. Bu uyarı yazıldığı gün doğruydu — ama dayandığı veri
kısıtı, o metin yazıldıktan **sonra** eklenen bir veri kümesiyle ortadan
kalkmış. DIX'in yayımlanmış mekanizması artık uygulanabilir durumda ve
uygulandı. DPKE kaldırılmadı; farklı bir şey ölçüyor ve yerinde duruyor.

## 1. Eskimiş imkansızlık iddiası

`gamma-exposure-service/main.py` içindeki `METODOLOJI` sabiti şunu diyor:

> "FINRA'nın haftalık ATS Transparency verisi işlem YÖNÜ İÇERMEZ — yalnızca
> toplam hisse adedi ve işlem sayısı verir. Bu nedenle gerçek DIX bu veriden
> HESAPLANAMAZ."

Bu ifade **haftalık ATS veri kümesi için doğrudur.** Ancak:

| veri kümesi | eklenme | işlem yönü |
|---|---|---|
| `finra.py` — haftalık ATS Transparency | 18.08.2026 | yok |
| `regsho.py` — **günlük Reg SHO kısa hacim** | **23.08.2026** | **kısa hacim oranı var** |

Günlük Reg SHO veri kümesi, DPKE'nin metodoloji metni yazıldıktan sonra
eklendi. İmkansızlık iddiası bu ikinci kaynağı kapsamıyor.

## 2. DIX'in yayımlanmış mekanizması

SqueezeMetrics'in açıkladığı sezgi: bir yatırımcı karanlık havuzda **alırken**,
karşı tarafta duran piyasa yapıcı pozisyonu **açığa satar**. Dolayısıyla borsa
dışı baskılarda "short" işaretli hacmin payı, alış baskısının vekilidir. Yön
bilgisi işlem bazında işaretlemeden değil, **kısa hacim oranından** gelir.

Reg SHO günlük dosyası tam olarak bunu verir:

```
ShortVolume / TotalVolume   (FINRA'ya bildirilen = borsa dışı hacim için)
```

## 3. Ölçüm

CDN'den doğrudan indirilerek, 10.09.2026:

| tarih | sembol | eşit ağırlıklı | medyan | **hacim ağırlıklı** | 7 mega-cap |
|---|---:|---:|---:|---:|---:|
| 2026-09-03 | 12.266 | %48,76 | %49,71 | **%50,89** | **%38,68** |
| 2026-09-09 | 12.275 | %49,60 | %50,20 | **%52,11** | **%44,77** |

Gerçek DIX tarihsel olarak **%38–48** bandında hareket eder ve %45 üzeri
"alıcılı" sayılır. Mega-cap ağırlıklı değerlerimiz (%38,68 → %44,77) bu bantla
örtüşüyor — mekanizmanın doğru olduğunun bağımsız göstergesi.

Canlı uçtan ölçüm aynı sonucu veriyor: `/dix?semboller=AAPL,MSFT,NVDA,TSLA,AMZN,GOOGL,META`
→ **%44,77**, 2026-09-09, kapsam %100.

## 4. Bu yine de resmî DIX değildir — farklar

| # | fark | neden önemli |
|---|---|---|
| 1 | **Kapsam** | Reg SHO, FINRA'ya bildirilen *tüm* borsa dışı hacmi kapsar: ATS (karanlık havuz) **ve** broker iç eşleştirmesi. DIX yalnızca karanlık havuz baskılarını kullanır. Paydamız daha geniştir. |
| 2 | **Sepet** | DIX S&P 500 bileşenleri üzerinden hesaplanır. Bu depoda doğrulanmış bir S&P 500 listesi **yok**. Liste uydurulmadı; sepet dışarıdan verilir ve kapsam raporlanır. |
| 3 | **Ağırlık** | DIX dolar hacmiyle ağırlıklandırır. Fiyat verisi yoksa dolar ağırlığı hesaplanamaz; hisse hacmi ağırlığına düşülür ama bu **sessizce yapılmaz** — hangi ağırlığın kullanıldığı her yanıtta bildirilir. |
| 4 | **Normalizasyon** | DIX'in iç ölçekleme/düzleştirme ayrıntıları açık değildir. Burada ham oran verilir; uydurma bir ölçekleme yapılmaz. |

## 5. İki tasarım kararı

**Kapsam dışı sembol sıfır sayılmaz.** Sepette olup günlük dosyada bulunmayan
bir sembolü 0 oranla katmak, "o sembolde hiç kısa hacim yoktu" demek olur ve
endeksi yapay olarak aşağı çeker. Bunun yerine kapsam dışı sayılır ve
`kapsam_yuzde` ile birlikte raporlanır. Canlı doğrulama: 4 sembollük sepette 2
sahte sembolle kapsam %50 bildirildi, oran bozulmadı.

**Ağırlık karışımı yapılmaz.** Sepetin bir kısmını dolar, kalanını hisse
hacmiyle tartmak tanımsız bir karışım üretir. Bir sembolün bile fiyatı eksikse
dolar ağırlığı **tamamen** bırakılır ve bu bildirilir. Kapsam dışı bir sembolün
fiyatının bulunmaması ise dolar ağırlığını düşürmez — o sembol zaten hesaba
girmiyor.

## 6. Şüphecilik turu

| # | mutasyon | sonuç |
|---|---|---|
| M1 | kapsam dışı sembolü sıfır oranla sepete kat | YAKALANDI (4 fail) |
| M2 | kapsam dışı sembolün fiyatsızlığı da dolar ağırlığını düşürsün | YAKALANDI |
| M3 | eksik fiyat varken yine dolar ağırlığı iddia et | YAKALANDI (4 fail) |
| M4 | dolar ağırlığını hiç uygulama | YAKALANDI |
| M5 | resmî DIX olduğunu iddia et | YAKALANDI |
| M6 | oranı ağırlıklandırmadan topla | YAKALANDI |

**Hayatta kalan mutasyon yok (0/6).**

## 7. DPKE'ye ne oldu

Hiçbir şey. `gamma-exposure-service`'teki DPKE ucu **kaldırılmadı ve
değiştirilmedi**. Farklı bir şey ölçüyor (hacmin nerede gerçekleştiği — venue
karması), yeni DIX ucu ise yön baskısının vekilini ölçüyor. İkisi birbirinin
yerine geçmez.

**Öneri (uygulanmadı):** DPKE'nin `METODOLOJI` metnindeki imkansızlık cümlesi,
günlük Reg SHO veri kümesini kapsamadığını belirtecek şekilde güncellenebilir.
Bu değişiklik yapılmadı çünkü o dosya bu maddenin konusu değil ve çalışma
ağacında başka bir bekleyen değişiklik taşıyor.

## 8. Üretilen dosyalar

- `finra-darkpool-service/src/dix.py` — sepet ağırlıklı borsa dışı kısa hacim oranı
- `finra-darkpool-service/src/main.py` — `/dix` ucu
- `finra-darkpool-service/tests/test_dix.py` — 17 test
