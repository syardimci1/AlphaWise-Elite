-- =====================================================================
-- 005 — Supabase: profiles INSERT politikasi + auth.users profil tetigi
-- =====================================================================
-- Uygulandi   : 2026-09-11 (URETIME UYGULANDI, kullanici onayiyla)
-- Veritabani  : SUPABASE (`supabase-db`, PostgreSQL 17.6)
-- On kosul    : 004
--
-- ---------------------------------------------------------------------
-- OLCULEN ARIZA
-- ---------------------------------------------------------------------
-- `public.profiles` RLS ACIK ama yalnizca SELECT ve UPDATE politikasi
-- vardi. PostgreSQL'de RLS acikken POLITIKASI OLMAYAN komut REDDEDILIR:
--   * yeni kullanici kaydinda profil satiri OLUSMUYORDU (auth.users
--     uzerinde 0 tetik vardi),
--   * kullanici KENDI profilini bile olusturamiyordu.
-- Ayrica tum depoda `profiles`'a INSERT yapan HICBIR uygulama kodu ve
-- hicbir service_role kullanimi YOKTU — yani bosluğu kapatan bir yol
-- hic yoktu. Mevcut 2 profil, artik VAR OLMAYAN bir mekanizmadan kalmisti.
--
-- IZOLE ORTAMDA YENIDEN URETILDI (postgres:17-alpine, ayri ag, uretim
-- semasinin birebir kopyasi — sutun semasi MD5'i ozdes):
--   1) auth.users'a yeni kayit -> profil sayisi 0
--   2) kullanici KENDI profilini ekliyor (auth.uid() dogru):
--      ERROR: new row violates row-level security policy for table "profiles"
--
-- ---------------------------------------------------------------------
-- TASARIM NOTLARI
-- ---------------------------------------------------------------------
-- * SECURITY DEFINER: kayit aninda JWT baglami YOKTUR (auth.uid() NULL),
--   bu yuzden tetik RLS'i atlayarak yazabilmelidir.
-- * SET search_path = '': SECURITY DEFINER fonksiyonlarda search_path
--   ele gecirmeye karsi ZORUNLU; bu yuzden tum nesneler tam nitelenmis.
-- * ON CONFLICT DO NOTHING: yeniden calistirma / geri doldurma / yarisan
--   yol kaydi BOZMAZ.
-- * WITH CHECK (auth.uid() = id): kullanici YALNIZCA KENDI profilini
--   ekleyebilir, baskasininkini EKLEYEMEZ (izole ortamda ve uretimde
--   ayri ayri kanitlandi).
--
-- BILINEN ODUNLESME (olculdu): tetik AFTER INSERT ve ayni islemdedir —
-- profil olusturma HATA FIRLATIRSA kayit TAMAMEN GERI ALINIR, yani
-- kullanici hic kaydolamaz (izole testte dogrulandi: auth.users'ta 0
-- satir). Bu BILINCLI bir fail-closed tercihtir: profilsiz kullanici
-- ASLA olusmasin diye. Fail-open isteniyorsa fonksiyona
-- `EXCEPTION WHEN OTHERS THEN RETURN NEW` eklenir — karsiliginda profil
-- eksikligi SESSIZ kalir.
--
-- ---------------------------------------------------------------------
-- CALISTIRMA / GERI ALMA
-- ---------------------------------------------------------------------
--   docker exec -i supabase-db psql -U postgres -d postgres \
--     -v ON_ERROR_STOP=1 -f - < 005_...sql
--   (--single-transaction KULLANMAYIN: betik kendi BEGIN/COMMIT'ini tasir)
--   Geri alma: /opt/alphawise/supabase_hayalet_tablo_geri_al.sql
--   (veri degismedigi icin geri alma veri KAYBETTIRMEZ)
-- =====================================================================

BEGIN;

DROP POLICY IF EXISTS "Kullanicilar kendi profilini olusturabilir" ON public.profiles;
CREATE POLICY "Kullanicilar kendi profilini olusturabilir"
  ON public.profiles FOR INSERT TO authenticated
  WITH CHECK (auth.uid() = id);

CREATE OR REPLACE FUNCTION public.yeni_kullanici_profili_olustur()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  INSERT INTO public.profiles (id, email, full_name, company_name)
  VALUES (
    NEW.id,
    NEW.email,
    NULLIF(NEW.raw_user_meta_data ->> 'full_name', ''),
    NULLIF(NEW.raw_user_meta_data ->> 'company_name', '')
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS auth_users_profil_olustur ON auth.users;
CREATE TRIGGER auth_users_profil_olustur
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.yeni_kullanici_profili_olustur();

-- GERI DOLDURMA (idempotent): profili olmayan mevcut kullanicilar.
-- 11.09.2026'da uretimde 0 SATIR etkiledi (2/2 kullanicinin profili vardi).
INSERT INTO public.profiles (id, email, full_name, company_name)
SELECT u.id, u.email,
       NULLIF(u.raw_user_meta_data ->> 'full_name', ''),
       NULLIF(u.raw_user_meta_data ->> 'company_name', '')
FROM auth.users u
WHERE NOT EXISTS (SELECT 1 FROM public.profiles p WHERE p.id = u.id)
ON CONFLICT (id) DO NOTHING;

COMMIT;

-- ---------------------------------------------------------------------
-- DOGRULAMA
-- ---------------------------------------------------------------------
SELECT 'profiles_insert_politikasi' AS kontrol, COUNT(*)::text AS deger
FROM pg_policy WHERE polrelid = 'public.profiles'::regclass AND polcmd = 'a'
UNION ALL
SELECT 'auth_users_tetigi', COUNT(*)::text
FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'auth' AND c.relname = 'users'
  AND t.tgname = 'auth_users_profil_olustur' AND NOT t.tgisinternal
UNION ALL
SELECT 'tetik_security_definer', p.prosecdef::text
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public' AND p.proname = 'yeni_kullanici_profili_olustur'
UNION ALL
SELECT 'profilsiz_kullanici', COUNT(*)::text
FROM auth.users u WHERE NOT EXISTS (SELECT 1 FROM public.profiles p WHERE p.id = u.id);
