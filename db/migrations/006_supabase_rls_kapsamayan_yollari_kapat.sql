-- =====================================================================
-- 006 — Supabase: RLS'İN KAPSAMADIĞI ERİŞİM YOLLARINI KAPAT
-- =====================================================================
-- Veritabanı : SUPABASE (`supabase-db`) — 004/005 ile aynı hedef.
-- Bulundu    : 15.09.2026, izole ortamda kanıtlanmış sızıntı testiyle.
--
-- ---------------------------------------------------------------------
-- NEDEN BU DOSYA VAR: "RLS AÇIK" YETMİYOR
-- ---------------------------------------------------------------------
-- 004/005 sonrası `profiles` ve `user_portfolios` tablolarında RLS AÇIK
-- ve politikalar doğru. İzole ortamda 21 satır-düzeyi sızıntı testinin
-- 21'i de GEÇTİ (A, B'nin verisini SELECT/UPDATE/DELETE edemiyor;
-- B adına INSERT edemiyor; anon hiçbir şey göremiyor).
--
-- ANCAK RLS, PostgreSQL'de TRUNCATE'İ KAPSAMAZ. Satır düzeyi güvenlik
-- SELECT/INSERT/UPDATE/DELETE için çalışır; TRUNCATE tablo düzeyinde bir
-- işlemdir ve yalnızca TRUNCATE yetkisine bakar.
--
-- ÖLÇÜLDÜ (izole ortam, üretim yetkilerinin birebir kopyası):
--     authenticated  TRUNCATE public.profiles         -> BAŞARILI
--     authenticated  TRUNCATE public.user_portfolios  -> BAŞARILI
--     anon           TRUNCATE public.profiles         -> BAŞARILI
--     anon           TRUNCATE public.user_portfolios  -> BAŞARILI
--
-- `anon` anahtarı tarayıcı paketine gömülüdür (NEXT_PUBLIC_SUPABASE_ANON_KEY).
-- Yani siteyi açan HERKES, tek bir çağrıyla TÜM kullanıcıların profillerini
-- ve portföylerini silebilirdi. RLS bunu engellemez; yalnızca yetkinin
-- geri alınması engeller.
--
-- İKİNCİ BULGU — GİZİL AYRICALIK YÜKSELTME:
-- `profiles.role` kolonu (enum: user|partner|admin) kullanıcının KENDİ
-- güncelleyebildiği bir kolondu. Ölçüldü: A, kendi satırında
-- `role='admin'` yapabiliyor. Bugün `role` hiçbir yetkilendirmede
-- KULLANILMIYOR (frontend taraması boş) — yani açık şu an sömürülemez.
-- Ama biri `if (profile.role === 'admin')` yazdığı ANDA sömürülebilir
-- hale gelir. Bu, kapatılması ucuz, sonradan bulunması pahalı bir mayındır.
--
-- ---------------------------------------------------------------------
-- NE YAPILMIYOR (bilinçli)
-- ---------------------------------------------------------------------
-- * RLS politikalarına DOKUNULMUYOR — 21/21 test geçiyor, çalışan bir
--   şeyi değiştirmek karşılaştırılabilirliği bozardı.
-- * `service_role` ve `postgres` yetkileri KORUNUYOR — ikisi de zaten
--   BYPASSRLS taşıyor; onlardan TRUNCATE almak Supabase Studio/yönetim
--   araçlarını bozabilirdi, güvenlik kazancı ise sıfırdır.
-- * `profiles` DELETE politikası EKLENMİYOR — şu an politika yok, yani
--   DELETE zaten reddediliyor (fail-closed, C5 ile uyumlu ve doğru).
--   Kullanıcı silme, auth.users üzerinden ON DELETE CASCADE ile olur.
--
-- ---------------------------------------------------------------------
-- IDEMPOTENT
-- ---------------------------------------------------------------------
-- REVOKE, olmayan bir yetki için hata vermez; betik defalarca
-- çalıştırılabilir. Doğrulama sorgusu sonda.
--
-- ÇALIŞTIRMA:
--   docker exec -i supabase-db psql -U postgres -d postgres \
--     -v ON_ERROR_STOP=1 -f - < 006_...sql
-- =====================================================================

BEGIN;

-- --- 1) TRUNCATE yetkisini istemci rollerinden AL ---------------------
-- RLS bunu engellemiyor; tek koruma yetkinin kendisidir.
REVOKE TRUNCATE ON public.profiles        FROM anon, authenticated;
REVOKE TRUNCATE ON public.user_portfolios FROM anon, authenticated;

-- --- 2) Gereksiz şema yetkilerini AL ---------------------------------
-- REFERENCES ve TRIGGER, istemci rollerinin işine yaramaz; saldırı
-- yüzeyini büyütür (ör. TRIGGER ile tabloya kod iliştirme).
REVOKE REFERENCES, TRIGGER ON public.profiles        FROM anon, authenticated;
REVOKE REFERENCES, TRIGGER ON public.user_portfolios FROM anon, authenticated;

-- --- 3) `anon` YAZAMAZ ------------------------------------------------
-- Oturumsuz bir ziyaretçinin yazma işi yoktur. RLS zaten engelliyordu
-- (auth.uid() NULL), ama derinlemesine savunma: yetkiyi de al.
-- Kayıt akışı etkilenmez: profil, 005'teki SECURITY DEFINER tetiği
-- tarafından auth.users üzerinden oluşturulur, anon INSERT'i ile değil.
REVOKE INSERT, UPDATE, DELETE ON public.profiles        FROM anon;
REVOKE INSERT, UPDATE, DELETE ON public.user_portfolios FROM anon;

-- --- 4) AYRICALIK YÜKSELTMEYİ KAPAT ----------------------------------
-- Kolon düzeyi yetki: kullanıcı profilini güncelleyebilir ama `role`
-- kolonuna DOKUNAMAZ. Politika yerine kolon yetkisi seçildi çünkü RLS
-- WITH CHECK yalnızca YENİ satırı görür; "role değişmedi" kıyası için
-- OLD gerekir ve bu ancak tetikle yapılabilirdi — kolon yetkisi hem
-- daha basit hem de veritabanı tarafından doğrudan zorlanıyor.
--
-- DİKKAT — ÖLÇÜLEN TUZAK (ilk sürümde bu yanlış yazılmıştı):
-- Yalnızca `REVOKE UPDATE (role)` yazmak HİÇBİR ŞEY YAPMAZ. PostgreSQL'de
-- TABLO düzeyi UPDATE yetkisi TÜM kolonları kapsar ve kolon düzeyi bir
-- REVOKE ondan eksiltme yapamaz. İzole ortamda ölçüldü: kolon REVOKE'undan
-- SONRA da A, kendi `role`'unu 'admin' yapabiliyordu.
-- Doğru yol: önce TABLO düzeyi UPDATE'i tamamen al, sonra YALNIZCA izinli
-- kolonlar için kolon düzeyi UPDATE ver. `id` de bilerek dışarıda:
-- kullanıcı kendi satırının kimliğini değiştirememeli.
REVOKE UPDATE ON public.profiles FROM anon, authenticated;
GRANT UPDATE (email, full_name, company_name, updated_at)
    ON public.profiles TO authenticated;

-- --- 5) SEQUENCE: `anon` id tüketemesin --------------------------------
-- ÖLÇÜLDÜ: `anon` ve `authenticated`, user_portfolios_id_seq üzerinde
-- nextval() çağırabiliyordu (izole ortamda anon 8'e kadar ilerletti).
-- `anon`'un artık HİÇ INSERT yetkisi yok (bölüm 3), dolayısıyla bu
-- yetkiye ihtiyacı da yok. Kalması, oturumsuz bir ziyaretçinin `serial`
-- (int4, üst sınır 2.147.483.647) sayacını tüketip meşru INSERT'leri
-- kalıcı olarak bozabilmesi demekti.
-- `authenticated`'ın USAGE'ı KORUNUYOR: `serial` varsayılanı INSERT
-- sırasında çağıran rolün yetkisiyle değerlendirilir; alınırsa kullanıcı
-- kendi portföyünü oluşturamaz hale gelirdi (Y6 ihlali).
REVOKE ALL ON SEQUENCE public.user_portfolios_id_seq FROM anon;

-- --- 6) FAIL-CLOSED (C5): okuma da yetki düzeyinde kapansın -----------
-- RLS zaten `anon`'a sıfır satır döndürüyor (auth.uid() NULL — 21/21
-- testte ölçüldü). Bu iki REVOKE ikinci katmandır: RLS bir gün yanlışlıkla
-- kapatılsa ya da bir politika gevşetilse bile oturumsuz okuma YETKİ
-- katmanında reddedilir. "Politika hatası = herkese açık" senaryosu kapanır.
--
-- Y6 GÜVENCESİ — ölçüldü, varsayılmadı: bu iki tabloya depoda HİÇBİR kod
-- dokunmuyor. `from('profiles')` / `from('user_portfolios')` araması tüm
-- frontend ve backend'de BOŞ; üç `createClient()` çağrısının üçü de yalnızca
-- kimlik işlemi yapıyor (signInWithPassword, getUser, signOut). `service_role`
-- da hiçbir yerde kullanılmıyor. Yani bu daraltmanın kıracağı bir çağrı yok.
-- İleride oturumsuz bir genel okuma gerekirse, yetki AÇIKÇA geri verilmelidir.
REVOKE SELECT ON public.profiles        FROM anon;
REVOKE SELECT ON public.user_portfolios FROM anon;

-- `profiles` üzerinde DELETE politikası YOK, yani RLS zaten reddediyor.
-- Yetkiyi de almak bunu tek katmanlı olmaktan çıkarır: politika listesine
-- ileride bir DELETE politikası eklenirse bile yetki engeli ayakta kalır.
REVOKE DELETE ON public.profiles FROM authenticated;

-- --- 7) MAINTAIN: ERISIM ENGELLEME (DoS) VEKTÖRÜNÜ KAPAT ---------------
-- PostgreSQL 17 ile gelen MAINTAIN yetkisi (ACL harfi `m`) VACUUM, ANALYZE,
-- CLUSTER, REINDEX ve REFRESH MATERIALIZED VIEW çalıştırma hakkı verir.
-- Üretimde ölçüldü: her iki tabloda da `anon=arwdDxtm` — yani `m` VAR.
--
-- ÖLÇÜLEN SÖMÜRÜ (izole ortam, üretim ACL'i birebir kopyalanarak):
--     SET ROLE anon; VACUUM FULL public.profiles;   -> VACUUM   (çalıştı)
--                    REINDEX TABLE public.profiles; -> REINDEX  (çalıştı)
--                    CLUSTER public.profiles ...;   -> CLUSTER  (çalıştı)
-- KARŞI ÖLÇÜM (MAINTAIN alındıktan sonra, aynı oturumda):
--     VACUUM FULL -> WARNING: permission denied to vacuum "profiles", skipping
--     REINDEX     -> ERROR:   permission denied for table profiles
--
-- Bunların üçü de ACCESS EXCLUSIVE kilit alır: kilit süresince tabloya HİÇBİR
-- okuma ya da yazma geçemez. `anon` anahtarı tarayıcı paketinde olduğundan,
-- siteyi açan herkes bu çağrıyı döngüye alıp tabloyu kapatabilirdi. Veri
-- SIZDIRMAZ ama ERİŞİMİ ENGELLER; RLS bu yolu hiç görmez.
--
-- Uygulama tarafında MAINTAIN'e ihtiyaç YOK: hiçbir kod VACUUM/REINDEX
-- çalıştırmıyor, bakım işleri `postgres` rolüyle ve autovacuum ile yapılır.
-- `service_role` ve `postgres` dokunulmadan bırakılıyor.
--
-- SÜRÜM NOTU: MAINTAIN yalnızca PostgreSQL 17+ vardır. Üretim 17.6 olarak
-- ölçüldü, izole doğrulama ortamı 17.11 — aynı ana sürüm, aynı ACL anlamı.
-- 17 öncesi bir sunucuda bu satır sözdizimi hatası verir; o durumda satır
-- kaldırılmalıdır (diğer bölümler sürümden bağımsızdır).
REVOKE MAINTAIN ON public.profiles        FROM anon, authenticated;
REVOKE MAINTAIN ON public.user_portfolios FROM anon, authenticated;

COMMIT;

-- ---------------------------------------------------------------------
-- DOĞRULAMA
-- ---------------------------------------------------------------------
SELECT 'truncate_yetkisi_kalan' AS kontrol, COUNT(*)::text AS deger
FROM information_schema.role_table_grants
WHERE table_schema='public' AND privilege_type='TRUNCATE'
  AND grantee IN ('anon','authenticated')
UNION ALL
SELECT 'anon_yazma_yetkisi_kalan', COUNT(*)::text
FROM information_schema.role_table_grants
WHERE table_schema='public' AND privilege_type IN ('INSERT','UPDATE','DELETE')
  AND grantee = 'anon'
UNION ALL
SELECT 'role_kolonu_update_yetkisi', COUNT(*)::text
FROM information_schema.column_privileges
WHERE table_schema='public' AND table_name='profiles' AND column_name='role'
  AND privilege_type='UPDATE' AND grantee IN ('anon','authenticated')
UNION ALL
SELECT 'anon_okuma_yetkisi_kalan', COUNT(*)::text
FROM information_schema.role_table_grants
WHERE table_schema='public' AND privilege_type='SELECT' AND grantee='anon'
UNION ALL
SELECT 'anon_sequence_yetkisi', COUNT(*)::text
FROM information_schema.role_usage_grants
WHERE object_schema='public' AND grantee='anon'
UNION ALL
SELECT 'auth_profiles_delete_yetkisi', COUNT(*)::text
FROM information_schema.role_table_grants
WHERE table_schema='public' AND table_name='profiles'
  AND privilege_type='DELETE' AND grantee='authenticated'
UNION ALL
SELECT 'maintain_yetkisi_kalan', COUNT(*)::text
FROM information_schema.role_table_grants
WHERE table_schema='public' AND privilege_type='MAINTAIN'
  AND grantee IN ('anon','authenticated')
UNION ALL
-- OLUMLU DENETIM: daraltma FAZLA genis olmamali (Y6).
-- Bu ikisi 1 DONMEZSE goc kullaniciyi kendi verisinden etmis demektir.
SELECT 'auth_profil_duzenleyebilir_OLMALI_4', COUNT(*)::text
FROM information_schema.column_privileges
WHERE table_schema='public' AND table_name='profiles' AND grantee='authenticated'
  AND privilege_type='UPDATE'
UNION ALL
SELECT 'auth_portfoy_yazabilir_OLMALI_4', COUNT(*)::text
FROM information_schema.role_table_grants
WHERE table_schema='public' AND table_name='user_portfolios' AND grantee='authenticated'
  AND privilege_type IN ('SELECT','INSERT','UPDATE','DELETE');
