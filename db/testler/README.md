# İzole RLS / Yetki Doğrulama Ortamı

Bu dizin, `db/migrations/006_supabase_rls_kapsamayan_yollari_kapat.sql`
göçünün **gerçekten çalıştığını** kanıtlayan test ağını içerir.

```bash
./calistir.sh          # ortamı sıfırdan kurar ve tüm testleri çalıştırır
./calistir.sh --sadece-test
```

## Neden ayrı bir ortam

Bir RLS politikasını yazmak, onun çalıştığını kanıtlamaz. Bu testler
**superuser olmayan** gerçek `anon` / `authenticated` rolleriyle, tıpkı
tarayıcıdaki bir istemci gibi bağlanır ve saldırıyı **fiilen dener**.
`postgres` rolü BYPASSRLS taşıdığı için onunla yapılan hiçbir test
izolasyonu kanıtlamaz.

Kimlik, Supabase'in kendi yolundan taklit edilir:

```sql
BEGIN;
  SET LOCAL role authenticated;
  SET LOCAL request.jwt.claims = '{"sub":"<uuid>","role":"authenticated"}';
  -- saldırı burada denenir
ROLLBACK;   -- testler ortamı bozmaz, tekrarlanabilir
```

## Üretime dokunulmaz

Testler `izole-rls-test` adlı geçici bir konteynerde çalışır. Üretim
(`supabase-db`) yalnızca ACL karşılaştırması için **salt okuma** sorgusuyla
okunur; hiçbir yazma yapılmaz.

## Dosyalar

| dosya | işi |
|---|---|
| `calistir.sh` | ortamı kurar, göçleri uygular, tüm testleri çalıştırır |
| `00_izole_kurulum.sql` | roller, `auth` şeması, `auth.uid()`/`auth.role()` (üretimden birebir) |
| `01_uretim_acl_esitle.sql` | **ortamı üretimin yetki yüzeyine eşitler** (aşağıya bakın) |
| `02_test_verisi.sql` | iki sahte kullanıcı (A, B) + bir "yetim" kullanıcı (C) |
| `sizinti_testi.py` | satır düzeyi sızıntı matrisi + olumlu denetimler |
| `bypass_testi.py` | RLS'in kapsamadığı yollar (TRUNCATE, rol yükseltme, SECURITY DEFINER) |
| `yollar_testi.py` | JOIN / toplam / sequence / şema yazma / sistem kataloğu |
| `goc_testi.py` | idempotentlik, veri korunumu, canlı karar yolunun dokunulmazlığı |
| `geri_alma_testi.py` | geri alma göçünün gidiş-dönüş testi (ACL parmak izi) |

## `01_uretim_acl_esitle.sql` neden var

Bu çalışmadaki en ciddi hata buydu (`docs/denetim_raporlari/HATA_HAFIZASI_coklukullanici.md`,
H-1): izole ortamın üretimi temsil ettiği **varsayılmıştı**. Üretimde
`anon=arwdDxtm` iken izole ortamda `m` (MAINTAIN) yoktu; testler var olmayan
bir yetkiyi "kapalı" sanıyordu. O dosya bu hatayı yapısal olarak imkânsız kılar.

**Üretimin ACL'i değişirse** o dosyadaki GRANT'lar güncellenmelidir; içinde
yeniden okumak için gereken sorgu yazılıdır.

## Beklenen çıktı

```
sizinti_testi.py       SONUC: 30/30 PASS
yollar_testi.py        SONUC: 13/13 PASS
goc_testi.py           SONUC: 17/17 PASS
geri_alma_testi.py     SONUC: 8/8 PASS
bypass_testi.py        bulgu sayısı: 0
```

Bir testin **kırmızıya dönmesi** göçün bir şeyi kaçırdığı anlamına gelir.
Test ağında hem "saldırı engellendi mi" hem de **"meşru kullanım hâlâ
çalışıyor mu"** denetimleri vardır; ikincisi olmadan "her şeyi reddet"
sahte bir başarı olurdu.
