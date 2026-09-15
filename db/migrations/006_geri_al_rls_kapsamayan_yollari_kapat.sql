-- =====================================================================
-- 006 GERİ ALMA — 006'nın kapattığı yetkileri AYNEN geri verir
-- =====================================================================
-- Veritabanı : SUPABASE (`supabase-db`)
-- Amaç       : 006 üretimde beklenmedik bir şeyi kırarsa, tek komutla
--              göç ÖNCESİ duruma dönmek (Y5 — atomik geri alınabilirlik).
--
-- ---------------------------------------------------------------------
-- HEDEF DURUM NEREDEN GELİYOR
-- ---------------------------------------------------------------------
-- Tahminle değil, ÜRETİMDEN OKUNARAK belirlendi (15.09.2026, salt okuma
-- `BEGIN READ ONLY` işleminde):
--
--   profiles               = {postgres=arwdDxtm/postgres, anon=arwdDxtm/postgres,
--                             authenticated=arwdDxtm/postgres, service_role=arwdDxtm/postgres}
--   user_portfolios        = (aynı)
--   user_portfolios_id_seq = {postgres=rwU/postgres, anon=rwU/postgres,
--                             authenticated=rwU/postgres, service_role=rwU/postgres}
--
-- ACL harfleri: a=INSERT r=SELECT w=UPDATE d=DELETE D=TRUNCATE
--               x=REFERENCES t=TRIGGER m=MAINTAIN (PG17+)  |  U=USAGE
--
-- ---------------------------------------------------------------------
-- UYARI — BU GERİ ALMA GÜVENLİK AÇIKLARINI DA GERİ AÇAR
-- ---------------------------------------------------------------------
-- Bu betik çalıştırıldığında şunlar YENİDEN mümkün hale gelir:
--   * `anon` (tarayıcı paketindeki anahtar) TRUNCATE ile tüm profilleri
--     ve portföyleri silebilir,
--   * bir kullanıcı kendi `profiles.role` değerini 'admin' yapabilir,
--   * `anon`, VACUUM FULL/REINDEX ile tabloyu ACCESS EXCLUSIVE kilitle
--     herkese kapatabilir.
-- Yani bu dosya bir ONARIM değil, bir ACİL DURUM ÇIKIŞIDIR. Yalnızca
-- 006 gerçekten bir şeyi kırdıysa ve kök neden bulunana kadar geçici
-- olarak kullanılmalıdır.
--
-- IDEMPOTENT: yalnızca GRANT/REVOKE içerir, defalarca çalıştırılabilir.
-- =====================================================================

BEGIN;

-- 006'nın eklediği KOLON düzeyi yetkileri kaldır. Bu şart: tablo düzeyi
-- UPDATE geri verilse bile kolon girdileri ACL'de ayrı satır olarak kalır
-- ve parmak izi üretimdekiyle AYNI olmaz.
REVOKE UPDATE (email, full_name, company_name, updated_at)
    ON public.profiles FROM authenticated;

-- Tablo yetkilerini üretimdeki hâline döndür (PG17'de ALL, MAINTAIN dahil).
GRANT ALL ON public.profiles        TO anon, authenticated;
GRANT ALL ON public.user_portfolios TO anon, authenticated;

-- Sequence: üretimde rwU = SELECT, UPDATE, USAGE (ALL değil).
GRANT SELECT, UPDATE, USAGE ON SEQUENCE public.user_portfolios_id_seq TO anon;

COMMIT;

-- ---------------------------------------------------------------------
-- DOĞRULAMA — ACL üretimdeki dizgeyle BİREBİR aynı olmalı
-- ---------------------------------------------------------------------
-- DİKKAT: `relacl::text` dizge karşılaştırması YANLIŞTIR. relacl bir dizidir
-- ve eleman sırası yetkilerin veriliş sırasını yansıtır; aynı yetki kümesi
-- farklı sırayla yazılabilir. Karşılaştırma aclexplode() ile KÜME olarak
-- yapılır. (Bu hata ilk sürümde vardı ve sağlam bir geri almayı "FARKLI"
-- gösteriyordu — izole ortamda yakalandı.)
WITH beklenen(nesne, rol, yetki) AS (
    SELECT t.nesne, r.rol, y.yetki
    FROM (VALUES ('profiles'), ('user_portfolios')) t(nesne)
    CROSS JOIN (VALUES ('postgres'),('anon'),('authenticated'),('service_role')) r(rol)
    CROSS JOIN (VALUES ('INSERT'),('SELECT'),('UPDATE'),('DELETE'),
                       ('TRUNCATE'),('REFERENCES'),('TRIGGER'),('MAINTAIN')) y(yetki)
    UNION ALL
    SELECT 'user_portfolios_id_seq', r.rol, y.yetki
    FROM (VALUES ('postgres'),('anon'),('authenticated'),('service_role')) r(rol)
    CROSS JOIN (VALUES ('SELECT'),('UPDATE'),('USAGE')) y(yetki)
), gozlenen AS (
    SELECT c.relname AS nesne, a.grantee::regrole::text AS rol, a.privilege_type AS yetki
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace,
         LATERAL aclexplode(c.relacl) a
    WHERE n.nspname = 'public'
      AND c.relname IN ('profiles','user_portfolios','user_portfolios_id_seq')
)
SELECT 'uretimde_olup_eksik'  AS kontrol, COUNT(*)::text AS deger
FROM (SELECT * FROM beklenen EXCEPT SELECT * FROM gozlenen) e
UNION ALL
SELECT 'fazladan_kalan', COUNT(*)::text
FROM (SELECT * FROM gozlenen EXCEPT SELECT * FROM beklenen) f;

SELECT 'kalan_kolon_yetkisi' AS kontrol, COUNT(*)::text AS deger
FROM information_schema.column_privileges
WHERE table_schema='public' AND table_name='profiles'
  AND grantee='authenticated' AND privilege_type='UPDATE'
  AND column_name IN ('email','full_name','company_name','updated_at')
  AND is_grantable='NO'
  AND NOT EXISTS (SELECT 1 FROM information_schema.role_table_grants g
                  WHERE g.table_schema='public' AND g.table_name='profiles'
                    AND g.grantee='authenticated' AND g.privilege_type='UPDATE');
