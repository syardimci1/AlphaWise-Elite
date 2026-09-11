-- =====================================================================
-- 004 — Supabase: public.profiles + public.user_portfolios SEMASI
-- =====================================================================
-- Uygulandi   : (URETIMDE ZATEN VAR — bu betik onlari GERIYE DONUK
--                surumler; uretimde calistirilirsa NO-OP'tur)
-- Veritabani  : SUPABASE (`supabase-db`, PostgreSQL 17.6) — DIKKAT:
--               001-003 gocceleri `alphawise_db` (TimescaleDB) icindir.
--               Bu ilk SUPABASE goccesidir.
--
-- ---------------------------------------------------------------------
-- NEDEN BU DOSYA VAR: "HAYALET TABLO" BULGUSU
-- ---------------------------------------------------------------------
-- 08.09.2026 denetiminde bulundu, 11.09.2026'da yeniden dogrulandi:
-- `public.profiles` ve `public.user_portfolios` Supabase'de CANLI olarak
-- VAR, RLS acik ve veri tasiyorlar — ama DDL'leri HICBIR git deposunda
-- YOKTU (grep sifir, `git log -S` bos, `supabase_migrations` semasi hic
-- olusturulmamis: 11.09.2026'da olculdu, 0 sema).
--
-- Sonuc: TEMIZ BIR KURULUMDA BU TABLOLAR YENIDEN URETILEMIYORDU. Bu
-- betik o boslugu kapatir — calisan uretimden `pg_dump --schema-only`
-- ile SALT-OKUNUR cikarilmis semanin birebir surumlenmis halidir.
--
-- ---------------------------------------------------------------------
-- IDEMPOTENT — URETIMDE NO-OP
-- ---------------------------------------------------------------------
-- Tum ifadeler IF NOT EXISTS / kosullu yazildi. Uretimde (tablolar zaten
-- varken) calistirilirsa HICBIR SEY DEGISTIRMEZ; degeri temiz bir
-- kurulumu ayaga kaldirabilmektir.
--
-- ON KOSUL: `auth` semasi ve `auth.users` tablosu (GoTrue tarafindan
-- olusturulur) ZATEN VAR OLMALIDIR — yabanci anahtarlar ona bagli.
--
-- ---------------------------------------------------------------------
-- CALISTIRMA
-- ---------------------------------------------------------------------
--   docker exec -i supabase-db psql -U postgres -d postgres \
--     -v ON_ERROR_STOP=1 -f - < 004_...sql
--   (--single-transaction KULLANMAYIN: betik kendi BEGIN/COMMIT'ini tasir,
--    001-003 ile ayni desen)
-- =====================================================================

BEGIN;

-- user_role enum (CREATE TYPE'in IF NOT EXISTS'i yoktur)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = 'public' AND t.typname = 'user_role'
    ) THEN
        CREATE TYPE public.user_role AS ENUM ('user', 'partner', 'admin');
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.profiles (
    id uuid NOT NULL,
    email text,
    role public.user_role DEFAULT 'user'::public.user_role NOT NULL,
    full_name text,
    company_name text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT profiles_pkey PRIMARY KEY (id)
);

-- NOT: `id` uretimde IDENTITY DEGIL, ayri bir SEQUENCE + nextval()
-- varsayilanidir (pg_dump ile olculdu). Birebir ayni kurulmasi sart:
-- IDENTITY'ye cevirmek temiz kurulumu uretimden FARKLI yapardi.
CREATE SEQUENCE IF NOT EXISTS public.user_portfolios_id_seq
    AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

CREATE TABLE IF NOT EXISTS public.user_portfolios (
    id integer NOT NULL DEFAULT nextval('public.user_portfolios_id_seq'::regclass),
    user_id uuid NOT NULL,
    portfolio_name text DEFAULT 'Ana Portfoy'::text,
    tickers text[] NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT user_portfolios_pkey PRIMARY KEY (id)
);

ALTER SEQUENCE public.user_portfolios_id_seq OWNED BY public.user_portfolios.id;

-- Yabanci anahtarlar (ADD CONSTRAINT'in IF NOT EXISTS'i yoktur)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'profiles_id_fkey') THEN
        ALTER TABLE public.profiles
            ADD CONSTRAINT profiles_id_fkey FOREIGN KEY (id)
            REFERENCES auth.users(id) ON DELETE CASCADE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'user_portfolios_user_id_fkey') THEN
        ALTER TABLE public.user_portfolios
            ADD CONSTRAINT user_portfolios_user_id_fkey FOREIGN KEY (user_id)
            REFERENCES auth.users(id) ON DELETE CASCADE;
    END IF;
END $$;

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_portfolios ENABLE ROW LEVEL SECURITY;

-- Uretimde OLCULEN politikalar (DROP+CREATE ile idempotent)
DROP POLICY IF EXISTS "Kullanicilar kendi profilini gorebilir" ON public.profiles;
CREATE POLICY "Kullanicilar kendi profilini gorebilir"
    ON public.profiles FOR SELECT USING ((auth.uid() = id));

DROP POLICY IF EXISTS "Kullanicilar kendi profilini guncelleyebilir" ON public.profiles;
CREATE POLICY "Kullanicilar kendi profilini guncelleyebilir"
    ON public.profiles FOR UPDATE USING ((auth.uid() = id));

DROP POLICY IF EXISTS "Kullanicilar kendi portfoylerini yonetir" ON public.user_portfolios;
CREATE POLICY "Kullanicilar kendi portfoylerini yonetir"
    ON public.user_portfolios USING ((auth.uid() = user_id));

COMMIT;

-- ---------------------------------------------------------------------
-- DOGRULAMA
-- ---------------------------------------------------------------------
SELECT 'tablo_sayisi' AS kontrol, COUNT(*)::text AS deger
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname IN ('profiles','user_portfolios')
UNION ALL
SELECT 'rls_acik_tablo', COUNT(*)::text
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname IN ('profiles','user_portfolios') AND c.relrowsecurity
UNION ALL
SELECT 'politika_sayisi', COUNT(*)::text FROM pg_policy
WHERE polrelid IN ('public.profiles'::regclass, 'public.user_portfolios'::regclass);
