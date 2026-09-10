# DBnomics ve AkShare — Kaynak Değerlendirmesi

**Madde 44** — *DBnomics + AkShare*
**Tarih:** 10 Eylül 2026

## Kısa sonuç

| kaynak | sonuç |
|---|---|
| **DBnomics** | **kullanılabilir** — bir seri kanıtlanarak benimsendi, kalanı kanıtlanamadı |
| **AkShare** | **kullanılamaz** — ABD makro verisi bir yıl eski, ABD hisse ucu engelli |

## 1. DBnomics

Anahtarsız, HTTP 200. 93 sağlayıcı. `liquidity-signal-service` şu an FRED
kullanıyor ve **FRED_API_KEY olmadan çalışmıyor** — DBnomics bunun için
anahtarsız bir yedek olabilir mi, ölçüldü.

### Bulgu 1: FRED, DBnomics'te sağlayıcı DEĞİL

Yaygın varsayımın aksine DBnomics FRED'i doğrudan aynalamıyor. 93 sağlayıcı
arasında `FRED` yok; `FED`, `BEA`, `BLS`, `ECB`, `IMF`, `OECD`, `WB` var.
Dolayısıyla eşleme **elle** kurulmak zorunda ve denklik **varsayılamaz**.

### Bulgu 2: WALCL birebir eşleşiyor — ve daha taze

`FED/H41/RESPPA_N.WW` (H.4.1, haftalık Çarşamba, toplam varlıklar):

| tarih | DBnomics | FRED (önbellek) | fark |
|---|---:|---:|---:|
| 2026-07-08 | 6.735.609 | 6.735.609 | **0** |
| 2026-07-15 | 6.743.028 | 6.743.028 | **0** |
| 2026-07-22 | 6.747.378 | 6.747.378 | **0** |
| 2026-07-29 | 6.738.190 | 6.738.190 | **0** |
| 2026-08-05 | 6.748.567 | 6.748.567 | **0** |
| 2026-08-12 | 6.759.955 | 6.759.955 | **0** |

Altı ortak tarihin altısında da fark **tam sıfır**. Üstelik DBnomics daha
güncel: en yeni gözlem **2026-09-02**, deponun FRED önbelleği **2026-08-12**'de
bitiyor (1238 gözlem vs 346).

### Bulgu 3: "Aynı seri adı" ≠ "aynı değer" — M2 örneği

`FED/H6_H6_M2/M2.M` (mevsimsellikten arındırılmış M2), FRED `M2SL` ile
**eşleşmiyor**:

| ay | DBnomics | FRED | fark |
|---|---:|---:|---:|
| 2026-02 | 22.598,9 | 22.620,3 | −21,4 |
| 2026-03 | 22.640,4 | 22.676,1 | −35,7 |
| 2026-04 | 22.756,7 | 22.799,9 | −43,2 |

Sürüm (vintage) farkı. Aynı kavram, farklı revizyon. Bu seri tabloya
**alınmadı.**

### Bulgu 4: TGA ve RRP kaynakta yok

`WTREGEN` (Hazine Genel Hesabı) ve `RRPONTSYD` (gecelik ters repo) için
`FED/H41`'in türev olmayan **258 serisi değer üzerinden tarandı**; eşleşen
bulunamadı. İsim araması da sonuç vermedi.

### Uygulama

`liquidity-signal-service/src/dbnomics.py` — tek kuralı var: **bir eşleşme,
değerleri karşılaştırılarak doğrulanmadan tabloya giremez.** Eşleşme kaydı
kanıt alanı taşımak zorunda (ortak gözlem sayısı, azami fark, yöntem) ve test
bunu zorluyor. Doğrulanmamış bir kod istendiğinde modül tahmin etmez, hata
fırlatır.

Tablo şu an **tek seri** taşıyor. Az ama kanıtlı; tahmine dayalı bir eşleşme
sessizce yanlış makro veri beslerdi.

## 2. AkShare

İzole konteynerde kuruldu (B1). 1141 fonksiyon:

| kategori | fonksiyon |
|---|---:|
| ABD makro (`macro_usa_*`) | 49 |
| Çin hissesi (`stock_zh_*`) | 45 |
| opsiyon | 46 |
| ABD hissesi (`stock_us_*`) | 8 |
| kripto | 4 |
| **Türkiye / BIST** | **0** |

49 ABD makro fonksiyonu ilk bakışta umut verici. Ama çalıştırıldığında:

```
macro_usa_cpi_monthly        en yeni dolu gözlem: 2025-08-12
macro_usa_unemployment_rate  en yeni dolu gözlem: 2025-08-01
macro_usa_adp_employment     en yeni dolu gözlem: 2025-09-04
stock_us_spot_em             ConnectionError (uzak uç bağlantıyı kapattı)
```

Veri **bir yıldan fazla eski** (bugün 2026-09-10). Bu bir sıralama yanılgısı
değil: tarih sütunu ayrıştırılıp azami değer alınarak doğrulandı. ABD hisse
ucu ise bağlantıyı reddediyor (kaynak Çin portalı, muhtemelen coğrafi engel).

Ek olarak sütun adları Çince (`商品`, `日期`, `今值`, `预测值`, `前值`).

**Sonuç: AkShare bu sistem için kullanılamaz.** Kurulmadı, bağımlılık
eklenmedi. Bir yıl eski makro veriyi beslemek, hiç beslememekten kötüdür —
çünkü eskilik veri içinde görünmez.

## 3. Şüphecilik turu

| # | mutasyon | sonuç |
|---|---|---|
| M1 | doğrulanmamış M2 eşleşmesini tabloya ekle | YAKALANDI (3 fail) |
| M2 | doğrulanmamış kodu tahminle karşıla | YAKALANDI |
| M3 | eksik gözlemi sıfır yap | YAKALANDI |
| M4 | şema uyuşmazlığını sessizce kırp | YAKALANDI |
| M5 | boş sonuçta boş liste dön | YAKALANDI |

**Hayatta kalan mutasyon yok (0/5).** 14 test.

## 4. Bekleyen karar

`dbnomics.py` yazıldı ve testlendi ama `fred_client.py`'ye **bağlanmadı**.
Bağlamak, canlı makro veri yolunu değiştirmek demektir ve tek doğrulanmış seri
(WALCL) için yedek devreye almanın değeri kullanıcı kararıdır. Modül hazır ve
anahtarsız çalıştığı canlı olarak doğrulandı.

## 5. Üretilen dosyalar

- `liquidity-signal-service/src/dbnomics.py` — anahtarsız yedek, kanıtlı eşleşme tablosu
- `liquidity-signal-service/tests/test_dbnomics.py` — 14 test
