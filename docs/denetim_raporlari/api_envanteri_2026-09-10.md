# Dış API Envanteri

**Madde 53** — *Nihai API envanteri*
**Tarih:** 10 Eylül 2026

## Nasıl üretildi

Elle yazılmadı. `araclar/api_envanteri.py` her çalıştırıldığında uç
noktalara **gerçekten dokunur**; bir kaynak kapandığında ya da taşındığında
liste kendini ele verir. Madde 35'te tam olarak bu oldu: USPTO, PatentsView
ve Senate LDA uçlarının üçü de belgelerde "ücretsiz" görünüyordu ama
ölçüldüğünde 401/403/emekli çıktılar.

Betik **anahtarsız** istek atar — amaç verinin kendisi değil, "bu uç nokta
hâlâ orada mı ve anahtar mı istiyor" sorusu. Bu yüzden **401 beklenen ve
sağlıklı bir sonuçtur**; incelenmesi gereken kod **404**'tür (yol değişmiş
ya da uç kaldırılmış).

Betik hiçbir ücretli çağrı yapmaz: ücretli kaynaklarda bile anahtar
gönderilmediği için istek faturalanabilir kullanım üretmez.

## Ölçüm çıktısı

```
kaynak                  HTTP  anahtar  ucret                 kota                                      tuketen
------------------------------------------------------------------------------------------------------------------------------------------------------
SEC EDGAR                200  HAYIR    ucretsiz              adil kullanim (UA sart)                   sec-edgar-13f, insider-trading
FINRA CDN (Reg SHO)      200  HAYIR    ucretsiz              belirtilmemis                             finra-darkpool
DBnomics                 200  HAYIR    ucretsiz              belirtilmemis                             liquidity-signal (yedek, madde 44)
FRED                     400  evet     ucretsiz (anahtarli)  120 istek/dk                              liquidity-signal
Tiingo                   200  evet     ucretsiz katman       6 anahtar tanimli                         market-data
Finnhub                  401  evet     ucretsiz katman       4 anahtar tanimli                         finnhub-signal
FlashAlpha               401  evet     ucretsiz katman       5 anahtar x 5/gun = 25/gun, ~250 sembol   gamma-exposure
OpenRouter (LLM)         200  HAYIR    UCRETLI (kredi)       kredi bazli                               maa (cascade)
LLMQuant                 404  evet     UCRETLI (kredi)       2 anahtar tanimli                         institution-filter
FMP                      401  evet     UCRETLI               plan bazli                                faa (kismi)
Alpha Vantage            200  evet     ucretsiz katman       25 istek/gun                              yedek
Quiver Quant             401  evet     UCRETLI               plan bazli                                congress-trading
Alpaca PAPER             401  evet     ucretsiz (paper)      200 istek/dk                              godmode-paper-trading
Google Patents           503  HAYIR    belgelenmemis         ~10 istekte 503, >16 dk blok (madde 35)   patent-sinyal (BAGLANMADI)
Equibles                 401  evet     ucretsiz katman       100 istek/gun (madde 52)                  YOK - anahtar bekliyor
Databento                401  evet     UCRETLI               kullanim bazli                            YOK (madde 49)
Schwab                   401  evet     dogrulanamadi         dogrulanamadi                             YOK (madde 50)
```

## Okuma notları

- **FRED 400** — uç ayakta,  parametresi eksik olduğu için biçim
  hatası veriyor. 401 ile aynı anlamda: erişilebilir, anahtar şart.
- **LLMQuant 404** — kök yolda uç yok; servis anahtarla farklı bir yol
  kullanıyor. Ücretli olduğu için derin sorgu yapılmadı.
- **Google Patents 503** — madde 35'te ölçülen blok hâlâ sürüyor. Bu kaynak
  bilinçli olarak **canlı bağımlılık yapılmadı**.
- **Equibles / Databento / Schwab 401** — hiçbiri sisteme bağlı değil; üçü de
  BEKLEYEN_KARAR (madde 49, 50, 52).

## Ücret dağılımı

| kategori | kaynak |
|---|---|
| **anahtarsız ücretsiz** | SEC EDGAR, FINRA CDN, DBnomics |
| **ücretsiz, anahtarlı** | FRED, Tiingo, Finnhub, FlashAlpha, Alpha Vantage, Alpaca PAPER |
| **ÜCRETLİ** | OpenRouter (LLM kredisi), LLMQuant, FMP, Quiver Quant |
| **belgelenmemiş** | Google Patents (bağlanmadı) |
| **bağlı değil** | Equibles, Databento, Schwab |

## En dar kotalar

| kaynak | kota | risk |
|---|---|---|
| **FlashAlpha** | 25 istek/gün **toplam**, ~250 sembol | madde 36'da üç sızıntı kapatıldı |
| **Alpha Vantage** | 25 istek/gün | yalnızca yedek |
| Equibles (bağlanırsa) | 100 istek/gün | sembol başına sorguya yetmez |

## Anahtar sayısı (canlı konteynerlerden okundu, değerler gizli)

Tiingo 6, FlashAlpha 5, Finnhub 4, LLMQuant 2; ayrıca FMP, FRED, Quiver,
Alpha Vantage, Alpaca, OpenRouter birer anahtar.

Çok anahtarlı rotasyon üç serviste var (FlashAlpha, Finnhub, LLMQuant) ve
FlashAlpha'da kota muhasebesi Redis'te atomik olarak tutuluyor.

## Yeniden çalıştırmak için

```bash
python3 araclar/api_envanteri.py
```
