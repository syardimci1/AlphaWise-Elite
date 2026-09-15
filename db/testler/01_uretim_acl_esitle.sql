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
