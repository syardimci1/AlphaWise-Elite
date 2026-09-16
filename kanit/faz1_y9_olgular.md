# FAZ 1.2 — Y9 Ürün Kararı İçin Ölçülen Olgular

**Tarih:** 16 Eylül 2026 · **Kaynak:** canlı `defter.sqlite` (salt-okunur) + Supabase

## Mevcut veri — ve görev metnindeki sayı artık eskimiş

Görev "1244 karar / 8 işlem" diyor. Bugün ölçülen:

| tablo | görev metni | **bugün** | fark |
|---|---|---|---|
| `karar` | 1244 | **1332** | +88 |
| `islem` | 8 | **8** | – |
| `sinyal_gozlem` | 748 | **836** | +88 |

**Defter canlı ve büyüyor.** En yeni karar bugün 16:02'de yazılmış. Bu, göç
stratejisini doğrudan etkiler: hareketli bir hedefe göç yazılıyor.

### Büyüme hızı (ölçüldü)

```
2026-09-16     88   (gün henüz bitmedi)
2026-09-15    176
2026-09-14    176
2026-09-11    176
2026-09-10    163
2026-09-09    180
2026-09-08    176
```

Cron: `0 16,18,20,21 * * 1-5` — hafta içi günde **4 çalışma**, ~176 karar/gün.
Yani göç sırasında tablo büyümeye devam eder; `ALTER TABLE` + varsayılan
değer stratejisi, "önce dondur" stratejisinden daha güvenli olabilir.

## Kararların niteliği

| eylem | adet |
|---|---|
| BEKLE | 1319 |
| AL | 13 |

Tamamı `broker='alpaca_paper'`. En sık semboller: MSFT (53), CAT (31),
WDC/V/TSLA/STX/SNDK/PLTR (30'ar).

## 8 işlemin tamamı

| id | zaman | sembol | yön | adet | fiyat |
|---|---|---|---|---|---|
| 8 | 2026-08-25 20:19 | MSFT | buy | 1 | 492,19 |
| 9 | 2026-08-25 20:23 | MSFT | buy | 1 | 492,12 |
| 10 | 2026-08-25 20:46 | MSFT | buy | 1 | 490,67 |
| 11 | 2026-09-01 16:53 | MSFT | buy | 4 | 500,23 |
| 12 | 2026-09-01 18:07 | MSFT | buy | 3 | 500,94 |
| 13 | 2026-09-01 19:00 | MSFT | buy | 3 | 500,94 |
| 14 | 2026-09-01 19:11 | MSFT | buy | 3 | 501,10 |
| 15 | 2026-09-02 14:00 | MSFT | buy | 4 | 498,22 |

**Hepsi MSFT alımı, toplam 20 adet, tek yön.** Yani "kimin portföyü"
sorusunun cevabı tek bir pozisyonu etkiliyor.

## En sert kısıt: **TEK Alpaca hesabı**

`/opt/alphawise/godmode-paper-trading-service/.env` içinde:

```
ALPACA_PAPER_API_KEY
ALPACA_PAPER_SECRET_KEY
```

Tekil. Yani defterdeki 20 MSFT adedi, **gerçek bir Alpaca kâğıt hesabında
duran tek bir pozisyona** karşılık geliyor. Çoklu kullanıcıda bu bir şema
sorunu değil, bir **muhasebe çelişkisi**: iki kullanıcı ayrı portföy görüyorsa
ama tek broker hesabı varsa, defter ile broker arasındaki mutabakat
(`/mutabakat` ucu) hangi kullanıcıya göre yapılacak?

## Supabase'deki iki kullanıcı

| id | e-posta | rol | kayıt |
|---|---|---|---|
| `c59c7853-…9798b50` | selcuk@alphawise.test | **admin** | 2026-08-03 16:26:41 |
| `d7e28a7c-…3d869d60` | partner@alphawise.test | partner | 2026-08-03 16:32:37 |

**Önemli sadeleşme:** İlk kayıt olan kullanıcı ZATEN admin. Yani Y9'un
A seçeneği ("sistem/admin kullanıcısına ata") ile C seçeneği ("ilk kayıt
olan kullanıcıya ata") **aynı kişiye çıkıyor** — `selcuk@alphawise.test`.
İkisi arasındaki tek gerçek fark, kuralın gelecekte nasıl davranacağı:
A sabit bir sistem kimliği, C ise "ilk gelen" kuralıdır.

Not: `profiles.role` alanı anlamlı şekilde kullanılıyor (admin/partner)
ama hiçbir kod onu yetkilendirmede okumuyor — 006 göçü bu kolonu
kullanıcının kendi değiştirmesine karşı kilitledi.
