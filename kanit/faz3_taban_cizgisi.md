# FAZ 3 — DEĞİŞİKLİKTEN ÖNCEKİ TABAN ÇİZGİSİ

**Tarih:** 16 Eylül 2026, Faz 2 uygulanmadan **önce** ölçüldü.
Bu dosya, Faz 3'ün "sonra" ölçümüyle karşılaştırılacak referanstır.

## Ölçüm 1 — Kaç API rotası kullanıcı kimliği okuyor?

```
TOPLAM rota          : 23
KIMLIK okuyan rota   :  0
kimlik OKUMAYAN rota : 23
```

İlk tarama 4 rotayı "kimlik okuyor" gösterdi; dördü de **yanlış eşleşme**
çıktı — üçü yorum satırındaki "kullanıcıya" kelimesi
(`finnhub-signal`, `institution-filter`, `skor-sentezi`), biri
`maa/[...yol]/route.ts`'teki `kullaniciZamanAsimi` adlı bir zaman aşımı
değişkeni. Hiçbiri gerçek kimlik okuması değil.

**Sonuç: sistemin "kim çağırıyor" kavramı rota katmanında SIFIR.**

## Ölçüm 2 — Kimlik nerede üretilip nerede kayboluyor

| aşama | dosya:satır | durum |
|---|---|---|
| JWT doğrulanıyor | `src/lib/oturum.ts:115` `sb.auth.getUser()` | ✅ çalışıyor |
| `kullaniciId` üretiliyor | `src/lib/oturum.ts:116` `return { gecerli: true, sebep: 'ok', kullaniciId: data.user.id }` | ✅ üretiliyor |
| middleware sonucu alıyor | `src/middleware.ts:255` `const oturum = await oturumDogrula(req, yanit)` | ✅ elinde |
| middleware **kullanıyor mu** | `src/middleware.ts:256` yalnızca `if (!oturum.gecerli)` | ❌ **`kullaniciId` ATILIYOR** |
| aşağı akışa taşınıyor mu | `src/lib/servis-proxy.ts:58-60` `fetch(url, { signal })` | ❌ **hiçbir başlık yok** |

## Ölçüm 3 — Hız sınırlama kovası

`src/middleware.ts:203` `const anahtar = \`${istemciKimligi(req)}|${sinif}\``
ve `istemciKimligi()` (satır 135-147) güvenilir vekil yokken sabit **`'ortak'`**
döndürüyor. Yani **tüm kullanıcılar tek kova paylaşıyor** — A, B'yi 429'a
düşürebilir. Kodun kendi yorumu (satır 142-147) bunu açıkça "tek kullanıcı
varsayımı" ile gerekçelendiriyor.

## Ölçüm 4 — Kimlik doğrulama SIRASI (değiştirilmemesi gereken tasarım)

Satır 212-256'daki sıra **bilinçli ve belgeli**:

1. `oturumCereziVarMi(req)` — bedava, ağa çıkmaz, jeton yakmaz (satır 218)
2. Hız sınırlama jetonu düşülür (satır 220)
3. `oturumDogrula()` — Supabase'e **ağ çağrısı** (satır 255)

Gerekçe kodda yazılı: kimliksiz bir sel, ortak kovayı boşaltıp meşru
kullanıcıyı kilitleyen bir hizmet engellemeye dönüşmesin diye jeton
harcatmadan reddediliyor. **İ-3 (kullanıcı bazlı kova) bu sırayı bozmadan
tasarlanmalı** — aksi halde her istek Supabase'e bir ağ çağrısı yapar.

## Ölçüm 5 — Sahte başlık (spoofing) yüzeyi

`src/middleware.ts:199` `if (!sinif) return NextResponse.next()` — sınıfı
olmayan yol tüm kontrolleri atlar. `sinifBelirle()` yalnızca
`!yol.startsWith('/api/')` durumunda `null` dönüyor; matcher `/api/:path*`
olduğu için pratikte tek istisna tam olarak `/api` yoludur.

Yine de: İ-1 uygulanırken gelen `x-kullanici-id` başlığı **koşulsuz ve en
başta** silinmelidir; aksi halde istemci kendi kimliğini uydurabilir.
Bu, Faz 3'te ayrı bir test senaryosudur.

## Ölçüm 6 — Test altyapısı hazır

`frontend/package.json`: `"test": "node --import tsx --test tests/koyfin/*.test.ts"`.
Mevcut 23 test **23/23 geçiyor**. Desen: rota fonksiyonunu doğrudan içe
aktar, `NextRequest` kur, çağır, yanıtı doğrula. Faz 4 testleri bu deseni
izleyecek; glob `tests/koyfin/*` ile sınırlı olduğu için genişletilmesi gerekecek.
