# KAPANIŞ RAPORU — Çoklu Kullanıcı İzolasyonu

**Tarih:** 17 Eylül 2026 · **Branch:** `feature/coklu-kullanici-izolasyon`

## 1. Ürün Kararı (FAZ 1)

- **Kapsam:** **A — kenar-öncelikli.** Defter tek sistem hesabı olarak kalır.
- **1244 karar / 8 işlem sahipliği:** **A — sistem kullanıcısı** (kural olarak
  kayıtlı; Kapsam A defteri bölmediği için **şu an uygulanmıyor**).
- **Auth yöntemi:** **Hibrit** — kenarda mevcut Supabase auth genişletildi,
  iç çağıranlar statik anahtarla kalıyor.
  **Gerekçe:** ölçüldü ki bugünkü üretim trafiğinin %100'ü JWT'siz (cron
  curl, healthcheck urlopen, hedef-planlayici dar anahtar). Yalnızca-JWT
  modeli otomasyonun tamamını 401'e düşürürdü.

### Görev metninin iki sözleşmesi ölçümle çürütüldü

- **C2 icra edilemez:** proxy `decision_log_id`'yi öğrenemez (üç INSERT de
  `RETURNING`'siz, yanıtta id yok, frontend'de Postgres sürücüsü yok),
  satırların **%98'i** proxy'den hiç geçmiyor, PK `(id, decided_at)` çifti ve
  id'ler `003` ile toplu yeniden numaralandı, iki ayrı VT arasında `fdw` yok.
  → 007 `decision_log`'a **hiç referans vermiyor**.
- **C1'in mekanizması çürük:** `main.py`'nin kendisi ham SQL yazıyor
  (`:906`, `:1015`), yani "defter.py okumaları filtreler" önerisi o sorguları
  filtreleyemezdi. → Kapsam A ile konu dışı kaldı.

## 2. İzolasyon Kanıtı (FAZ 3)

- **Sızıntı matrisi:** **8/8 PASS**, senaryolar elle değil **otomatik üretildi**
  (`src/app/api` ağacı gezilerek). Kapsam: **23 rota** (19 piyasa, 3 kullanıcı,
  1 sistem). Kanıt: `kanit/faz3_sizinti_matrisi.md`
- **Test edilen kullanıcılar:** her test **kendi** kullanıcı çiftini açıyor
  (sıradan bağımsızlık); gerçek oturum çerezleriyle, superuser **değil**.
- **Veri türleri:** kimlik taşıma, hız kovası, rapor erişimi, hata gövdesi,
  007 tablosu (veritabanı tarafında gerçek `anon`/`authenticated` rolleriyle).

## 3. main.py Dokunuldu mu?

| dosya | durum |
|---|---|
| `taa/src/main.py` | **DOKUNULMADI** |
| `maa/src/main.py` | **DOKUNULMADI** |
| `godmode-paper-trading-service/src/main.py` | **DOKUNULMADI** |
| `maa/src/cascade.py`, `llmquant_client.py` | **DOKUNULMADI** |
| `strateji.py`, `risk.py`, `simulasyon.py` | **DOKUNULMADI** (depo manifesti) |

**Y8 istisnası KULLANILMADI.** AST hash karşılaştırma: `kanit/benim_dosyalarim.sh`
(SHA-256 + docstring'siz AST, 8/8 PASS). Araç 4 mutasyonla doğrulandı **ve**
deponun kendi manifestiyle çapraz doğrulandı (ikisi de `dbd47e6f4946`).

## 4. Regresyon (FAZ 4)

- **Toplam: 28/28** (frontend 19 + konteyner 9). 15 maddenin **hepsi** ele alındı.
- Frontend testleri **206/206**; izole db ağı **83/83 + 0 bulgu**.
- **Defter korundu** — iddia "kaybolmadı" değil, **"hiç dokunulmadı"**:
  şemada `user_id` yok, `godmode-paper-trading` altında hiçbir dosya değişmedi.
- **Admin akışı çalışıyor** — beyaz liste dışı MAA yolu hâlâ jeton harcamadan 403.
- **`karar_uret` etkilenmedi** — değişen 2 Python dosyasının ikisi de
  `db/testler/` altında.
- Ölçülen: kimlik katmanı **12,73 ms**; 100 eşzamanlı kullanıcıda **sıfır karışma**.

## 5. Üretim Uygulaması (FAZ 5 — ✅ UYGULANDI, 17.09.2026)

- **Göç:** `007_*.sql` + `007_geri_al_*.sql` (yalnızca ekleme, veri riski sıfır)
- **Rollback:** tek komut, test edildi, idempotent
- **Kullanıcı kararı: A — ikisi de uygulandı.** Rapor izinli rolleri:
  `admin,partner` (varsayılan, sıfır regresyon).

### Uygulama sonucu — ölçüldü

**Parça 1 — 007 göçü (`supabase-db`)**
- Göçün kendi doğrulaması: **8/8** hedefte
- Mevcut veri **değişmedi**: `profiles=2, user_portfolios=1, auth.users=2`,
  profil özeti `583d6743a512781cf63281925aa3f09a`, politika sayısı 4.
  Tek fark beklenendi: `public` tablo sayısı 2 → 3.
- **Saldırılar üretim üzerinde fiilen denendi, 6/6 engellendi:**

| deneme | sonuç |
|---|---|
| `anon` SELECT | `permission denied for table` |
| `anon` TRUNCATE | `permission denied for table` |
| `anon` fonksiyon çağrısı | `permission denied for function` |
| `authenticated` doğrudan SELECT | `permission denied for table` |
| `authenticated` doğrudan INSERT | `permission denied for table` |
| `authenticated` sequence `nextval` | `permission denied for sequence` |

- **Meşru yol çalışıyor:** gerçek bir üretim kullanıcısının oturumunda
  `goruntuleme_kaydi_yaz(...)` → `id=1` (işlem geri alındı).

**Parça 2 — Frontend dağıtımı**
- `docker compose up -d --no-deps --build frontend` → yeni imaj, **15 sn**'de `healthy`
- **Komşu servisler etkilenmedi** (ölçüldü): `supabase-db` 4 hafta,
  `alphawise-maa` 13 gün, `alphawise-portfoy` 8 gün, `alphawise-gamma-exposure`
  7 gün, `godmode-paper-trading` 5 gün — hiçbirinin uptime'ı sıfırlanmadı.
  `--no-deps` işe yaradı.
- **Konteynerde yeni kod doğrulandı:** `kiraci.ts`, `rol.ts`, `raporlar.ts`
  mevcut; middleware `@/lib/kiraci` ithal ediyor; **16 rota** kimlik taşıyor.
- **Canlı davranış:** `/api/raporlar` çerezsiz → **401** + `x-oturum: cerez_yok`;
  beyaz liste dışı `/api/maa/decide/MSFT` → **403** (jeton harcamadan);
  ana sayfa → **200**.
- **Riskler:** `kanit/faz5_uretim_plani.md` — kapanmayan 7 risk açıkça listeli
  (en önemlisi R-4 kota adaleti ve paylaşılan ön kova)

## 6. Tek Cümle

> "Hiçbir kullanıcı bir başkasının verisini göremez çünkü **kimlik artık
> kenarda doğrulanıp aşağı akışa taşınıyor, hız kovası ve rapor erişimi
> doğrulanmış kimliğe bağlı, hata gövdeleri kiracıya göre süzülüyor ve yeni
> veritabanı nesnesi — güvensiz doğduğu ölçülmüş olduğu için — açıkça
> sertleştirildi.**"

**Dürüst kayıt:** Bu cümle **Kapsam A sınırları içinde** doğrudur. Defter,
`decision_log` ve kâğıt hesap hâlâ **tek sistem hesabıdır**; bunlar kullanıcı
verisi değil sistem verisidir ve paylaşılmaları tasarımdır. "Her kullanıcı
kendi portföyünü görür" cümlesi **hâlâ doğru değildir** ve bu görev onu doğru
hâle getirmedi — Kapsam B/C bilinçli olarak seçilmedi.
