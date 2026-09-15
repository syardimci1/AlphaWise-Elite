# Çoklu Kullanıcı İzolasyonu — Kapanış Raporu

**Tarih:** 15 Eylül 2026
**Kapsam:** Veri erişim/izolasyon katmanı (Supabase `profiles`, `user_portfolios`)
**Üretime uygulandı mı:** **EVET** — 15.09.2026, kullanıcının açık onayıyla (Y7).

> Bu rapordaki her sayı, üretim yetkilerinin **birebir kopyalandığı** izole bir
> PostgreSQL 17 ortamında, **superuser olmayan** gerçek `anon`/`authenticated`
> rolleriyle ölçülmüştür. Hiçbiri varsayım değildir.

---

## 1. Tek cümlelik sonuç

RLS zaten doğruydu ve satır düzeyinde sızıntı yoktu; **açık, RLS'in hiç
görmediği yollardaydı** — TRUNCATE, kolon yetkisi ve MAINTAIN. Üçü de
kapatıldı ve kapandığı kanıtlandı, ama **üretime uygulanmadı**.

## 2. Bulunan açıklar (üçü de üretimde GERÇEKTEN vardı)

Üretimden okunan ACL (15.09.2026, `BEGIN READ ONLY`):

```
profiles        = {postgres=arwdDxtm, anon=arwdDxtm, authenticated=arwdDxtm, service_role=arwdDxtm}
user_portfolios = {postgres=arwdDxtm, anon=arwdDxtm, authenticated=arwdDxtm, service_role=arwdDxtm}
```

`anon` anahtarı (`NEXT_PUBLIC_SUPABASE_ANON_KEY`) tarayıcı paketine gömülüdür.
Yani aşağıdaki üç yetki, **siteyi açan herkesin** elindeydi.

### A-1 — TRUNCATE: tüm kullanıcıların verisi silinebiliyordu (KRİTİK)

RLS, PostgreSQL'de TRUNCATE'i **kapsamaz**; TRUNCATE tablo düzeyi bir işlemdir
ve yalnızca TRUNCATE yetkisine bakar.

| rol | işlem | 006 ÖNCESİ | 006 SONRASI |
|---|---|---|---|
| `authenticated` | `TRUNCATE profiles` | **BAŞARILI** | `permission denied` |
| `authenticated` | `TRUNCATE user_portfolios` | **BAŞARILI** | `permission denied` |
| `anon` | `TRUNCATE profiles` | **BAŞARILI** | `permission denied` |
| `anon` | `TRUNCATE user_portfolios` | **BAŞARILI** | `permission denied` |

### A-2 — Ayrıcalık yükseltme: kullanıcı kendini `admin` yapabiliyordu

`profiles.role` (`user|partner|admin`) kullanıcının kendi güncelleyebildiği bir
kolondu. Ölçüldü: A, kendi satırında `role='admin'` yapabiliyordu.

**Bugün sömürülebilir değil** — `role` hiçbir yetkilendirmede kullanılmıyor
(tüm depoda arama boş). Ama biri `if (profile.role === 'admin')` yazdığı anda
sömürülebilir hale gelirdi. Kapatılması ucuz, sonradan bulunması pahalı bir mayın.

006 sonrası: `permission denied for table profiles`.

### A-3 — MAINTAIN: `anon` tabloyu herkese kapatabiliyordu (erişim engelleme)

PostgreSQL 17 ile gelen MAINTAIN yetkisi (ACL harfi `m`) `VACUUM`, `REINDEX`,
`CLUSTER` hakkı verir. Üçü de **ACCESS EXCLUSIVE** kilit alır: kilit süresince
tabloya hiçbir okuma veya yazma geçemez.

```
006 ÖNCESİ (anon):  VACUUM FULL profiles  -> VACUUM     (çalıştı)
                    REINDEX TABLE profiles -> REINDEX   (çalıştı)
                    CLUSTER profiles ...   -> CLUSTER   (çalıştı)
006 SONRASI (anon): VACUUM FULL -> WARNING: permission denied to vacuum, skipping
                    REINDEX     -> ERROR:   permission denied for table
```

Veri sızdırmaz, **erişimi engeller**. RLS bu yolu hiç görmez.

## 3. Zaten doğru olan: satır düzeyi izolasyon

006 ÖNCESİNDE de geçiyordu; 006 bunları **bozmadı**:

- A, B'nin profilini/portföyünü göremiyor, güncelleyemiyor, silemiyor
- A, B adına satır yazamıyor (`new row violates row-level security policy`)
- Sahipsiz (yetim) satır kimseye görünmüyor — fail-closed (C5)
- JOIN, alt sorgu, LEFT JOIN, `EXISTS`, `MAX()` ile dolaylı sızıntı yok
- `auth.users` ve `pg_authid` istemci rollerine kapalı
- İstemci rolleri `public` şemada tablo/fonksiyon **yaratamıyor**
- Tek SECURITY DEFINER fonksiyonun (`yeni_kullanici_profili_olustur`)
  `search_path`'i sabitlenmiş (`search_path=""`) ve doğrudan çağrılamıyor

## 4. Ölçüm özeti

Test ağının tamamı depoda: **`db/testler/`**. Tek komutla, sıfırdan kurulan
izole bir PostgreSQL 17 ortamında yeniden üretilebilir:

```
$ db/testler/calistir.sh
sizinti_testi.py       SONUC: 30/30 PASS
yollar_testi.py        SONUC: 13/13 PASS
goc_testi.py           SONUC: 17/17 PASS
geri_alma_testi.py     SONUC: 8/8 PASS
bypass_testi.py        bulgu sayısı: 0
TÜM TESTLER GEÇTİ
```

| test ağı | kapsam | sonuç |
|---|---|---|
| `sizinti_testi.py` | satır düzeyi sızıntı matrisi + olumlu denetimler | **30/30** |
| `yollar_testi.py` | JOIN/toplam/SECURITY DEFINER/sequence/şema/katalog | **13/13** |
| `goc_testi.py` | idempotentlik, veri korunumu, canlı yol dokunulmazlığı | **17/17** |
| `geri_alma_testi.py` | geri alma gidiş-dönüş, ACL parmak izi | **8/8** |
| `bypass_testi.py` | TRUNCATE / rol yükseltme / SECURITY DEFINER | **0 bulgu** |

Toplam **68 ölçüm**, tamamı geçti.

Testler `postgres` ile DEĞİL, **superuser olmayan** gerçek `anon` ve
`authenticated` rolleriyle çalışır; `postgres` BYPASSRLS taşıdığı için onunla
yapılan hiçbir ölçüm izolasyonu kanıtlamaz (C4).

## 5. Yasalara uygunluk

| yasa | durum | kanıt |
|---|---|---|
| **Y1** kutsal dosyalar | uyuldu | `git status` üçünde de temiz; hiçbiri okunmadı |
| **Y2** sıfır harcama | uyuldu | yalnızca mevcut Postgres; hiçbir dış çağrı yok |
| **Y3** şüphecilik turu | uyuldu | 3 açık, 2'si kendi testimin/göçümün hatasıydı (bkz. HATA_HAFIZASI) |
| **Y4** canlı karar yolu | uyuldu | görevin depoya kattığı tek şey iki `.sql` dosyası; `karar_uret` taşıyan dosya değişmedi |
| **Y5** atomik geri alınabilirlik | uyuldu | tek `BEGIN/COMMIT`; geri alma göçü ACL'i üretime **birebir** döndürüyor |
| **Y6** geri uyumluluk | uyuldu | göçte hiç DML yok; satır sayıları ve içerik özeti değişmedi; olumlu denetimler geçiyor |
| **Y7** üretim onayı | uyuldu | durup soruldu; **onay alındıktan sonra** uygulandı (bkz. bölüm 7) |
| **Y8** izolasyon kanıtı | uyuldu | her engel için "denendi → reddedildi" çıktısı yukarıda |

## 6. Kapsam DIŞI kalan — ürünün asıl çoklu kullanıcı açığı

Bu görev **veri erişim katmanını** kapattı. Ama ürünün gerçek çoklu kullanıcı
sorunu burada değil:

- `profiles` ve `user_portfolios` tablolarına **depoda hiçbir kod dokunmuyor**
  (`from('profiles')` / `from('user_portfolios')` araması tüm frontend ve
  backend'de boş). Bu tablolar bugün fiilen kullanılmıyor.
- Kullanıcının gerçekten gördüğü veri — portföy, kararlar, kâğıt defter,
  izlenen semboller — **kullanıcı sütunu olmayan** servislerden geliyor.
  `frontend/src/app/api/portfoy/route.ts` bunu açıkça söylüyor:
  *"Ticker almaz; defterin tamamıdır."*
- Yani bugün iki kullanıcı giriş yapsa **aynı portföyü ve aynı kararları**
  görür. Bu, `docs/denetim_raporlari/cok_kullanicili_olcekleme_2026-09-10.md`
  (Madde 54) belgesinde zaten ölçülmüş ve orada "bir şema, fiyatlandırma ve
  kota politikası kararıdır" denerek kullanıcıya bırakılmıştı.
- O katmanın kalbi **Y1 ile korunan dosyaların** içinde
  (`taa/src/main.py`, `maa/src/main.py`, `godmode-paper-trading-service/main.py`),
  dolayısıyla bu görevin kapsamına giremezdi.

**Dürüst ifade:** kapalı beta öncesi veri erişim katmanındaki üç somut açık
kapatıldı ve kanıtlandı; ancak "her kullanıcı yalnızca kendi verisini görür"
cümlesi **henüz doğru değildir** ve bu görevle doğru hale gelmemiştir.


## 7. Üretime uygulama (15.09.2026, onaylı)

Kullanıcı onayından sonra uygulandı. Öncesinde `pg_dump` ile iki tablonun
şema+veri yedeği alındı ve göçün ihtiyaç duyduğu dört kolonun üretimde
gerçekten var olduğu doğrulandı.

**Göçün kendi doğrulaması (üretim):** 9/9 hedefte — kapanması gereken yedi
ölçüt `0`, meşru kullanımı ölçen iki ölçüt `4`.

**Saldırılar üretim üzerinde fiilen denendi** (hepsi `ROLLBACK` içinde):

| rol | deneme | sonuç |
|---|---|---|
| `anon` | `TRUNCATE profiles` | `permission denied for table profiles` |
| `anon` | `TRUNCATE user_portfolios` | `permission denied for table user_portfolios` |
| `authenticated` | `TRUNCATE profiles` | `permission denied for table profiles` |
| `anon` | oturumsuz `SELECT` | `permission denied for table profiles` |
| `anon` | `nextval()` | `permission denied for sequence user_portfolios_id_seq` |
| `authenticated` (gerçek kullanıcı) | kendi `role`'unu `admin` yapma | `permission denied for table profiles` |
| `anon` | `VACUUM` / `REINDEX` | `permission denied to vacuum, skipping` / `permission denied` |

**Meşru kullanım bozulmadı** (gerçek üretim kullanıcısıyla): kendi profilini
görüyor (1), başkasınınkini görmüyor (0), kendi portföyünü görüyor (1), kendi
adını güncelleyebiliyor (1), yeni portföy ekleyebiliyor (1).

**Y6 sayısal kanıt:** göç öncesi ve sonrası birebir aynı —
`profiles=2, user_portfolios=1, auth.users=2`, profil içerik özeti
`583d6743a512781cf63281925aa3f09a`, politika sayısı `4`. Supabase yığınındaki
11 konteynerin hepsi `healthy` kaldı; PostgREST şema önbelleği tazelendi.

### 7.1 Tesadüfi bulgu — önceden var olan bir üretim hatası

Meşru kullanımı ölçen olumlu denetim, **006 ile ilgisi olmayan** gerçek bir
hatayı ortaya çıkardı: `user_portfolios_id_seq`, tabloda `id=1` satırı
dururken `is_called=f` durumundaydı. Yani sayacın üreteceği ilk değer `1`'di
ve **portföy oluşturmaya çalışan ilk gerçek kullanıcı**
`duplicate key value violates unique constraint "user_portfolios_pkey"`
hatası alacaktı.

Neden 006 kaynaklı değil: göç sequence'e yalnızca `REVOKE` uyguluyor, ki bu
yetki alır, **değer değiştirmez**. Aynı çakışma, 006'dan bağımsız olarak
izole ortamda da yeniden üretildi (sayaç geride bırakılıp INSERT denenerek).

Neden kendiliğinden kapandı: PostgreSQL'de `nextval` **işlem dışıdır**.
Başarısız olup geri alınan test INSERT'i bile sayacı ilerletti. Sonuç
doğrulandı — sayaç artık `max(id)`'nin önünde ve meşru INSERT `id=2` alarak
çalışıyor. Üretimdeki diğer dört sequence hiç kullanılmamış (`last_value`
boş), yani aynı hata başka yerde yok.
