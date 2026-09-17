-- =====================================================================
-- İZOLE ORTAMI ÜRETİMİN ACL'İNE BİREBİR EŞİTLE
-- =====================================================================
-- 004/005 ÇALIŞTIRILDIKTAN SONRA uygulanır (tablolar var olmalı).
--
-- NEDEN AYRI BİR ADIM: bu çalışmadaki en ciddi hata (HATA_HAFIZASI H-1),
-- izole ortamın üretimi temsil ETTİĞİNİN varsayılmasıydı. Üretimde
-- `anon=arwdDxtm` iken izole ortamda `m` (MAINTAIN) hiç yoktu; sonuç
-- olarak testler var olmayan bir yetkiyi "kapalı" sanıyordu. Bu dosya,
-- o hatayı yapısal olarak imkânsız kılar: ortam, ölçüm yapılmadan ÖNCE
-- üretimin yetki yüzeyine eşitlenir.
--
-- Hedef durum ÜRETİMDEN OKUNDU (15.09.2026, BEGIN READ ONLY):
--   profiles = user_portfolios = {postgres=arwdDxtm, anon=arwdDxtm,
--                                 authenticated=arwdDxtm, service_role=arwdDxtm}
--   user_portfolios_id_seq     = {postgres=rwU, anon=rwU, authenticated=rwU, service_role=rwU}
--
-- ÜRETİM DEĞİŞTİYSE: aşağıdaki GRANT'lar yerine üretimden yeniden okunmalıdır:
--   SELECT relname, relacl FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
--    WHERE n.nspname='public' AND relname IN ('profiles','user_portfolios');
-- =====================================================================
BEGIN;
REVOKE ALL ON public.profiles        FROM anon, authenticated, service_role;
REVOKE ALL ON public.user_portfolios FROM anon, authenticated, service_role;
REVOKE ALL (email, full_name, company_name, updated_at) ON public.profiles FROM anon, authenticated;
REVOKE ALL ON SEQUENCE public.user_portfolios_id_seq FROM anon, authenticated, service_role;

GRANT ALL ON public.profiles        TO anon, authenticated, service_role;
GRANT ALL ON public.user_portfolios TO anon, authenticated, service_role;
GRANT SELECT, UPDATE, USAGE ON SEQUENCE public.user_portfolios_id_seq TO anon, authenticated, service_role;

-- ---------------------------------------------------------------------
-- VARSAYILAN YETKİLER (pg_default_acl) — 17.09.2026 eklendi
-- ---------------------------------------------------------------------
-- NEDEN: Üretimde `public` şemasında açılan HER YENİ nesne, istemci
-- rollerine AÇIK doğuyor. Canlı ölçüldü (geri alınan işlemde gerçek
-- CREATE TABLE ile):
--   yeni tablo    → {postgres=arwdDxtm, anon=arwdDxtm, authenticated=arwdDxtm, ...}
--                   ve relrowsecurity = FALSE
--   yeni sequence → {anon=rwU, authenticated=rwU, ...}
--   yeni fonksiyon→ proacl `=X/postgres` (PUBLIC EXECUTE)
-- Kaynağı `pg_default_acl`'deki 6 satır (postgres + supabase_admin sahipliğinde).
--
-- Bu blok olmadan izole ortam üretimi TEMSİL ETMEZ: 007 gibi yeni nesne
-- kuran göçlerin sertleştirme bloklarını test etmek imkânsız olurdu, çünkü
-- çıplak bir PostgreSQL'de yeni tablo zaten kapalı doğar ve REVOKE'lar
-- "zaten kapalıydı" diye sessizce geçerdi. Bu, HATA_HAFIZASI H-1'in
-- (izole ortam üretimi temsil etmiyordu) aynı sınıf tekrarı olurdu.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON TABLES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, UPDATE, USAGE ON SEQUENCES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO anon, authenticated, service_role;
COMMIT;

-- DOĞRULAMA: 3 nesnenin de ACL'i üretimdekiyle aynı KÜME olmalı.
WITH beklenen(nesne, rol, yetki) AS (
    SELECT t.nesne, r.rol, y.yetki
    FROM (VALUES ('profiles'),('user_portfolios')) t(nesne)
    CROSS JOIN (VALUES ('postgres'),('anon'),('authenticated'),('service_role')) r(rol)
    CROSS JOIN (VALUES ('INSERT'),('SELECT'),('UPDATE'),('DELETE'),
                       ('TRUNCATE'),('REFERENCES'),('TRIGGER'),('MAINTAIN')) y(yetki)
    UNION ALL
    SELECT 'user_portfolios_id_seq', r.rol, y.yetki
    FROM (VALUES ('postgres'),('anon'),('authenticated'),('service_role')) r(rol)
    CROSS JOIN (VALUES ('SELECT'),('UPDATE'),('USAGE')) y(yetki)
), gozlenen AS (
    SELECT c.relname AS nesne, a.grantee::regrole::text AS rol, a.privilege_type AS yetki
    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace, LATERAL aclexplode(c.relacl) a
    WHERE n.nspname='public' AND c.relname IN ('profiles','user_portfolios','user_portfolios_id_seq')
)
SELECT 'uretimde_olup_eksik' AS kontrol, COUNT(*)::text AS deger
FROM (SELECT * FROM beklenen EXCEPT SELECT * FROM gozlenen) e
UNION ALL
SELECT 'fazladan_kalan', COUNT(*)::text
FROM (SELECT * FROM gozlenen EXCEPT SELECT * FROM beklenen) f;
