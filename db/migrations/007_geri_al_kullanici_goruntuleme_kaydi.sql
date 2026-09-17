-- =====================================================================
-- 007 GERİ ALMA — kullanıcı görüntüleme kaydını kaldırır
-- =====================================================================
-- Veritabanı : SUPABASE (`supabase-db`)
-- Amaç       : Y5 (atomik geri alınabilirlik).
--
-- ---------------------------------------------------------------------
-- ⚠ 006'NIN GERİ ALMASINDAN FARKI: BU BETİK VERİ KAYBETTİRİR
-- ---------------------------------------------------------------------
-- 006'nın geri alması yalnızca yetkileri değiştiriyordu, hiçbir satır
-- silmiyordu. Bu betik TABLOYU DÜŞÜRÜR; içindeki her görüntüleme kaydı
-- kalıcı olarak gider.
--
-- Çalıştırmadan ÖNCE dışa aktarmak isterseniz:
--   docker exec supabase-db psql -U postgres -d postgres -c \
--     "\copy public.kullanici_goruntuleme_kaydi TO '/tmp/kgk_yedek.csv' CSV HEADER"
--   docker cp supabase-db:/tmp/kgk_yedek.csv ./kgk_yedek_$(date +%Y%m%d).csv
--
-- ---------------------------------------------------------------------
-- ÖNCE UYGULAMA TARAFI DURDURULMALI
-- ---------------------------------------------------------------------
-- Frontend proxy hâlâ `goruntuleme_kaydi_yaz` çağırıyorsa, fonksiyon
-- düştükten sonra her çağrı `42883 undefined_function` döndürür.
-- Kayıt yazımı tasarım gereği ATEŞLE-UNUT + try/catch olduğu sürece
-- kullanıcı etkilenmez; yine de önce uygulama tarafındaki çağrının
-- kaldırılması ya da bayrakla kapatılması önerilir.
--
-- SIRA BİLİNÇLİ: önce fonksiyon, sonra tablo. Tersi olsaydı, düşme
-- anında araya giren bir yazma çağrısı yarım kalmış bir duruma düşerdi.
-- CASCADE BİLEREK KULLANILMIYOR: ileride bu tabloya bağlanmış bir nesne
-- varsa sessizce silinmesin, göç HATA versin ve insan baksın.
-- =====================================================================

BEGIN;

DROP FUNCTION IF EXISTS public.goruntuleme_kaydi_yaz(
    text, text, boolean, smallint, char(64), integer);

DROP TABLE IF EXISTS public.kullanici_goruntuleme_kaydi;

COMMIT;

-- ---------------------------------------------------------------------
-- DOĞRULAMA — üçü de SIFIR olmalı
-- ---------------------------------------------------------------------
SELECT 'kalan_tablo' AS kontrol, COUNT(*)::text AS deger
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname='public' AND c.relname='kullanici_goruntuleme_kaydi'
UNION ALL
SELECT 'kalan_fonksiyon', COUNT(*)::text
FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
WHERE n.nspname='public' AND p.proname='goruntuleme_kaydi_yaz'
UNION ALL
SELECT 'kalan_sequence', COUNT(*)::text
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND c.relkind='S'
  AND c.relname='kullanici_goruntuleme_kaydi_id_seq';
