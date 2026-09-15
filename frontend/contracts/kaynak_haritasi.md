# Kaynak Haritası — 4 Veri Kaynağı → Olay Şeması (C1) Eşlemesi

FAZ 1 kanıtı. Tüm örnekler 14-15.09.2026 tarihinde NVDA için canlı üretim
konteynerlerinden (host ağı, 127.0.0.1) çekildi. Yeni API/uç YOK (Y2) —
yalnızca zaten var olan 4 servisin zaten var olan uçları kullanıldı.

## 1) CONGRESS — congress-trading-service (127.0.0.1:8210)

**İstek:** `GET /trades/NVDA?limit=2`

**Örnek yanıt satırı:**
```json
{
  "member": "Gilbert Cisneros", "chamber": "House", "district": "CA31",
  "ticker": "NVDA", "asset_description": "NVIDIA Corporation",
  "transaction_type": "Sale", "transaction_date": "2026-08-18",
  "disclosure_date": "2026-09-11", "amount_range": "$1,001 - $15,000",
  "amount_min_usd": 1001, "amount_max_usd": 15000, "amount_mid_usd": 8000.5,
  "owner": ""
}
```

**C1 eşlemesi:**
| C1 alanı | Kaynak | Not |
|---|---|---|
| `id` | `hash(ticker, transaction_date, member, transaction_type, amount_range)` | Servis kalıcı id vermiyor — deterministik türetilmeli |
| `tip` | sabit `"CONGRESS"` | |
| `symbol` | `ticker` | |
| `ts_utc` | `transaction_date` (00:00 UTC) | **gerçek işlem tarihi** |
| `kaynak_zamani_utc` | `disclosure_date` (00:00 UTC) | STOCK Act'e göre işlemden **45 güne kadar geç** açıklanabilir — ts_utc≠kaynak_zamani_utc'nin C1'de neden iki ayrı alan olarak var olması gerektiğinin CANLI kanıtı |
| `kaynak` | `"congress_trading:" + source` (fmp/quiver/equibles) | üç katmanlı kaskad — hangi alt-kaynaktan geldiği izlenebilir kalmalı |
| `ozet` | `f"{member} ({chamber}) {transaction_type} {amount_range}"` | |
| `detay_url` | `null` | servis genel bir kamu linki döndürmüyor — GAP, VARSAYIM_DEFTERI'nde işaretli |
| `ham_veri_ref` | tüm satır (JSON) | |
| `confidence` | `1.0` | resmi STOCK Act beyanı; tutar bir ARALIK olsa da beyanın kendisi kesin |

## 2) INSIDER — insider-trading-service (127.0.0.1:8250)

**İstek:** `GET /insider/NVDA`

**Örnek yanıt satırı:**
```json
{
  "islem_tarihi": "2026-09-03", "dosyalama_tarihi": "2026-09-08",
  "kisi": "STEVENS MARK A",
  "islem_turu_ham": "Open market or private sale of non-derivative or derivative security",
  "acik_piyasa": true, "acik_piyasa_yonu": "satis",
  "adet": 198707.0, "islem_fiyati": 227.6954
}
```

**C1 eşlemesi:**
| C1 alanı | Kaynak | Not |
|---|---|---|
| `id` | `hash(ticker, kisi, islem_tarihi, adet, islem_fiyati)` | |
| `tip` | sabit `"INSIDER"` | |
| `symbol` | istek parametresi | yanıt satırında yok, çağıran taraf ekler |
| `ts_utc` | `islem_tarihi` | gerçek işlem günü |
| `kaynak_zamani_utc` | `dosyalama_tarihi` | Form 4 gecikmesi (ölçülen medyan 2 iş günü, bkz. dashboard) — congress ile AYNI iki-zaman deseni |
| `kaynak` | sabit `"sec_form4_direct"` | doğrudan SEC, aracı yok |
| `ozet` | `f"{kisi}: {acik_piyasa_yonu or islem_turu_ham} {adet} adet" + (f" @ ${islem_fiyati}" if acik_piyasa else "")` | |
| `detay_url` | `null` | servis Form 4 accession/URL döndürmüyor — GAP |
| `ham_veri_ref` | tüm satır | |
| `confidence` | `1.0` eğer `acik_piyasa=true`, `0.6` eğer `false` | `acik_piyasa=false` kayıtlarda `islem_fiyati=0.0` (hibe/ödül — gerçek piyasa sinyali değil); bu ayrımı KORUMAK gerekir, aksi halde 0 fiyatlı bir "satış" gibi yanlış okunur |

## 3) DARK POOL — finra-darkpool-service (127.0.0.1:8200)

**ÖNEMLİ DÜZELTME (bu fazda kendi kendine bulundu — bkz. HATA_HAFIZASI_koyfin.md H-001):**
Bir önceki fizibilite incelemesi (madde 59) yalnızca `/darkpool/{ticker}`'ı
(TEK haftalık anlık görüntü) görmüştü ve "dark pool haftalık özet, günlük
olay değil" sonucuna varmıştı. Bu doğruydu AMA eksikti — aynı serviste
**`/regsho/{ticker}`** adında GÜNLÜK granülerlikte, resmi FINRA Reg SHO
konsolide verisi ZATEN var. Yeni API gerekmiyor (Y2 sağlam).

**İstek:** `GET /regsho/NVDA`

**Örnek yanıt satırı:**
```json
{
  "tarih": "2026-09-14", "kisa_hacim": 23260788.456128,
  "kisa_muaf_hacim": 157180.0, "toplam_hacim": 52819239.034298,
  "kisa_hacim_orani_yuzde": 44.04
}
```
(bağlam: `ortalama_kisa_hacim_orani_yuzde: 39.37`, son 10 gün)

**C1 eşlemesi:**
| C1 alanı | Kaynak | Not |
|---|---|---|
| `id` | `hash(ticker, tarih)` | |
| `tip` | sabit `"DARK_POOL"` | |
| `symbol` | istek parametresi | |
| `ts_utc` | `tarih` | |
| `kaynak_zamani_utc` | `tarih` (ayrı yayın-gecikme alanı YOK) | VARSAYIM — servis yayın tarihini ayrıca döndürmüyor, GAP olarak işaretli |
| `kaynak` | sabit `"finra_regsho"` | resmi, anahtarsız |
| `ozet` | `f"Kisa hacim orani %{kisa_hacim_orani_yuzde} (10 gunluk ort. %{ortalama_kisa_hacim_orani_yuzde})"` | |
| `detay_url` | `null` | |
| `ham_veri_ref` | tüm satır | |
| `confidence` | `1.0` | |
| **filtre kuralı** | yalnızca `kisa_hacim_orani_yuzde` trailing-10-gün ortalamanın **+X puan** üzerindeyse OLAY üretilir | HER GÜN marker basmak grafiği anlamsız kalabalıklaştırır (bkz. FAZ 3 görsel gürültü testi) — eşik değeri VARSAYIM_DEFTERI'nde açık varsayım olarak kayıtlı, sabit kod DEĞİL |

## 4) 13F — sec-edgar-13f-service (127.0.0.1:8240)

**İstek:** `GET /holders/NVDA?top=2`

**Örnek yanıt satırı:**
```json
{
  "kurum": "BlackRock, Inc.", "kurum_cik": "2012383",
  "donem": "2026-06-30", "dosyalama_tarihi": "2026-08-07",
  "accession": "0002012383-26-003238",
  "cusip_dogrulandi": true,
  "hisse_pozisyonu": { "deger_usd": 226560080545, "adet": 607367113 }
}
```

**C1 eşlemesi:**
| C1 alanı | Kaynak | Not |
|---|---|---|
| `id` | `hash(kurum_cik, accession)` | |
| `tip` | sabit `"13F"` | |
| `symbol` | istek parametresi | |
| `ts_utc` | `donem` (rapor dönemi sonu — pozisyonun GERÇEKTEN ait olduğu tarih) | |
| `kaynak_zamani_utc` | `dosyalama_tarihi` (SEC'e sunulduğu tarih) | 13F'in kendi doğası gereği ~45 gün gecikmeli — congress/insider ile AYNI iki-zaman deseni ÜÇÜNCÜ kez doğrulandı |
| `kaynak` | sabit `"sec_edgar_13f_direct"` | |
| `ozet` | `f"{kurum} {donem} donemi icin ${deger_usd:,} pozisyon bildirdi"` | |
| `detay_url` | `f"https://www.sec.gov/Archives/edgar/data/{kurum_cik}/{accession.replace('-','')}/"` | **YENİ API GEREKMEDEN** kurulabiliyor — CIK+accession zaten yanıtta var (Y2 sağlam) |
| `ham_veri_ref` | tüm satır | |
| `confidence` | `1.0` eğer `cusip_dogrulandi=true`, `0.7` eğer `false` (isim eşleşmesiyle bulunmuş, doğrulanmamış) | |

## Genel Gözlem (FAZ 3'e taşınacak şüphecilik notu)

Dört kaynağın ÜÇÜ (congress, insider, 13F) doğal olarak İKİ ayrı zaman
taşıyor: gerçek olay tarihi (`ts_utc`) ve resmi açıklama tarihi
(`kaynak_zamani_utc`), aradaki gecikme haftalar sürebilir (13F/congress
~45 gün, insider ~2 iş günü medyan). C1'in bu ikisini ayrı alanlar olarak
tutması isteğe bağlı bir zarafet değil, üç kaynaktan üçünde de CANLI
gözlemlenen zorunlu bir gerçek. Grafik üzerinde HANGİ tarihte
gösterileceği (ts_utc mi kaynak_zamani_utc mi) FAZ 2'de açık bir
UI kararı olarak belgelenecek (bkz. VARSAYIM_DEFTERI V-002).
