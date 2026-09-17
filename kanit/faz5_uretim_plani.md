# FAZ 5 — ÜRETİM UYGULAMA PLANI (Y7: ONAY BEKLİYOR)

**Tarih:** 17 Eylül 2026 · **Durum:** ✅ **UYGULANDI** (17.09.2026, kullanıcı onayıyla — seçenek A)
Sonuçlar `kanit/KAPANIS_cokluk.md` §5'te.

---

## Uygulanacak iki BAĞIMSIZ parça

Bunlar birbirinden ayrı uygulanabilir; birini yapıp diğerini ertelemek
tutarsızlık yaratmaz.

### Parça 1 — Veritabanı göçü (`007`)

| | |
|---|---|
| **ileri** | `db/migrations/007_supabase_kullanici_goruntuleme_kaydi.sql` |
| **geri** | `db/migrations/007_geri_al_kullanici_goruntuleme_kaydi.sql` |
| **hedef** | `supabase-db` |
| **doğası** | **Yalnızca EKLEME**: yeni bir tablo + yeni bir fonksiyon. Mevcut hiçbir tabloya, politikaya veya yetkiye dokunmaz |
| **veri riski** | **Yok** — hiçbir satır okunmaz, yazılmaz, silinmez |
| **geri alma** | Tek komut; test edildi ve idempotent |
| **kesinti** | Yok — tablo kimse tarafından kullanılmıyor |

```bash
# uygula
docker exec -i supabase-db psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
  -f - < db/migrations/007_supabase_kullanici_goruntuleme_kaydi.sql
# geri al
docker exec -i supabase-db psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
  -f - < db/migrations/007_geri_al_kullanici_goruntuleme_kaydi.sql
```

### Parça 2 — Frontend dağıtımı (kimlik katmanı)

| | |
|---|---|
| **etkilenen** | `alphawise-frontend` konteyneri (yalnızca o) |
| **komut** | `docker compose up -d --no-deps --build frontend` |
| **kuru prova** | ✅ yapıldı — `depends_on` zinciri yok, tek konteyner etkileniyor |
| **kesinti** | Konteyner yeniden kurulurken kısa (önceki ölçümde benzer bir servis için **2,12 sn**) |
| **geri alma** | `git revert` + aynı komut; ya da önceki imaja dönmek |

> `--no-deps` **zorunlu**. Gerekçe ölçülmüş bir olaydır (H-003): daha önce
> `--no-deps` olmadan yapılan bir yeniden kurulum, `depends_on` üzerinden
> komşu bir servisi de yeniden başlatmıştı.

---

## Üretimde ne DEĞİŞİR, ne DEĞİŞMEZ

### Değişir

| değişiklik | görünen etki |
|---|---|
| Kimlik aşağı akışa taşınır (`x-kullanici-id`) | Servis günlüklerinde artık "kim çağırdı" görünür |
| Hız sınırlaması kullanıcı başına | Bir kullanıcının aşırı kullanımı diğerini **kendi kovası** düzeyinde kilitlemez |
| Hata gövdesi süzgeci | Kullanıcı artık `FLASHALPHA_API_KEY_2` gibi sır adlarını ve `172.18.0.7:8000` gibi iç adresleri **görmez** |
| Rapor uçlarına rol kapısı | `role='user'` olan bir hesap raporları indiremez |

### Değişmez

- **Defter** (`karar`/`islem`/`sinyal_gozlem`) — şema da veri de aynı
- **`decision_log`**, `signal_ledger` — hiç dokunulmadı
- **Karar yolu** (`karar_uret`) — tek satır Python değişmedi
- **Cron otomasyonu** — frontend'e hiç uğramıyor, etkilenmez
- **Mevcut iki kullanıcı** — ikisi de `admin`/`partner`, rapor erişimleri **aynen** sürer

---

## Üretim öncesi son kontrol listesi

| # | kontrol | durum |
|---|---|---|
| 1 | Frontend testleri yeşil | ✅ 206/206 |
| 2 | İzole db ağı yeşil | ✅ 83/83 + 0 bulgu |
| 3 | Sızıntı matrisi yeşil | ✅ 8/8 (23/23 rota) |
| 4 | Faz 4 regresyon yeşil | ✅ 28/28 |
| 5 | 8 korunan dosya değişmemiş | ✅ SHA-256 + AST |
| 6 | Başkasının işi bozulmamış | ✅ 5 dosya hash'i + 54 girdi varlığı |
| 7 | `next build` yeşil | ✅ |
| 8 | Geri alma test edildi | ✅ gidiş-dönüş + idempotent |
| 9 | Kuru prova yapıldı | ✅ tek konteyner |
| 10 | Üretim henüz dokunulmadı | ✅ `0/2/1` |

---

## ⚠ Uygulansa bile KAPANMAYAN riskler

Bunlar bu görevin kapsamı dışında kaldı ve **açıkça açık** bırakılıyor:

| # | risk | neden kapanmadı |
|---|---|---|
| **R-4** ✅ | Kota adaleti ve muhasebesi | **KAPATILDI** — İ-7 yapıldı (`efb013d`): kullanıcı başına sayaç + yumuşak pay. Kod commit'li; servis dağıtımı code 4'ün `pandas`/`oipd` bağımlılığı çözüldüğünde yapılmalı |
| **Ön kova** | Adalet mutlak değil — bir kullanıcı ~3-4× eşikte diğerini 429'a düşürebilir | Bilinçli ödünleşme; kalıcı çözüm güvenilir ters vekil |
| **R-1** | Defter/broker kiracılığı | Kapsam A kararı: defter tek sistem hesabı kalıyor |
| **R-7** | `/oz-iyilestirme/*` küresel strateji parametreleri | Korunan dosyada; kapsam dışı |
| **R-9** | Bildirim alıcı kavramı yok | Kapsam dışı |
| **R-13** | `godmode/execution` ikinci emir yüzeyi | Faz 1'de sonradan bulundu; kapsam dışı |
| **—** | `pg_default_acl` — her yeni tablo hâlâ güvensiz doğuyor | Sistemik karar; Supabase'in kendi araçlarını da etkiler |

---

## SEÇENEKLER

### A — İkisini de şimdi uygula (önerilen)

Önce 007 (veri riski sıfır), sonra frontend dağıtımı. Her adımdan sonra
doğrulama koşulur.

- **Fayda:** Ölçülen üç sızıntı (sır adı, iç adres, ortak sayaç) **bugün**
  kapanır; "kim çağırdı" sorusu cevaplanabilir hâle gelir.
- **Risk:** Frontend konteyneri kısa süre yeniden kurulur. Rapor rol kapısı
  devreye girer — bugünkü iki hesap etkilenmez (ikisi de yetkili).
- **Geri dönüş:** İkisi de tek komutla geri alınabilir.

### B — Kademeli: önce 007, frontend sonra

007'yi uygula (tamamen additive, kimse kullanmıyor), frontend'i bir sonraki
bakım penceresine bırak.

- **Fayda:** Sıfır kesinti; göç üretimde "dinlenir".
- **Risk:** Sızıntılar frontend dağıtılana kadar **açık kalır** — yani
  asıl güvenlik kazancı ertelenir.

### C — Bekle, ek test iste

Hiçbir şey uygulanmaz.

- **Fayda:** Sıfır değişiklik riski.
- **Risk:** Ölçülen sızıntılar açık kalır. Ayrıca `role='user'` ile kaydolacak
  ilk gerçek müşteri, kapatılmamış güvenlik açıklarını ve 33 servisin port
  envanterini içeren raporları indirebilir.

---

## ÖNERİM: **A**

Gerekçe: 007'nin veri riski **sıfır** (yalnızca ekleme, mevcut hiçbir nesneye
dokunmuyor) ve frontend değişikliği geriye uyumlu tasarlandı — kimlik
verilmediğinde her yol bugünkü davranışı aynen sürdürüyor. Buna karşılık
kapanacak şeyler ölçülmüş ve somut: API anahtarı adı, iç ağ adresleri ve
tüm kiracıların ortak tüketim sayacı bugün kullanıcının ekranına gidiyor.

Eğer `partner@alphawise.test` **dış** bir iş ortağıysa, dağıtımdan önce
`RAPOR_IZINLI_ROLLER=admin` ortam değişkenini eklemenizi öneririm — raporlar
kapatılmamış bir TLS açığını adıyla listeliyor.
