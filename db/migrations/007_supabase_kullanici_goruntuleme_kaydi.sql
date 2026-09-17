-- =====================================================================
-- 007 — Supabase: KULLANICI GÖRÜNTÜLEME KAYDI
-- =====================================================================
-- Veritabanı : SUPABASE (`supabase-db`) — 004/005/006 ile aynı hedef.
-- Tarih      : 17.09.2026
--
-- ---------------------------------------------------------------------
-- NE İŞE YARAR
-- ---------------------------------------------------------------------
-- "Kim, neyi, ne zaman gördü" sorusunu cevaplar. Bugün sistemin hiçbir
-- yerinde bu bilgi yok: 23 API rotasının 23'ü de kullanıcı kimliği
-- okumuyordu (Faz 3 taban çizgisinde ölçüldü).
--
-- ---------------------------------------------------------------------
-- NEDEN `decision_log`'A REFERANS VERMİYOR
-- ---------------------------------------------------------------------
-- Görev metnindeki ilk tasarım `kullanici_karar_iliskisi(user_id,
-- decision_log_id)` idi. Faz 1'de bu tasarımın **icra edilemez** olduğu
-- beş bağımsız kanıt zinciriyle gösterildi:
--
--   1. Proxy `decision_log_id`'yi ÖĞRENEMEZ: üç INSERT de `RETURNING`'siz
--      (`maa/src/main.py:611-614, :1016-1019, :1047-1055`) ve `/decide` ile
--      `/narrative-verified` yanıtlarında `id` alanı yok.
--   2. Frontend'de Postgres sürücüsü YOK (`package.json`: yalnızca
--      @supabase/*, next, react) ve konteynerde `DB_*` değişkeni verilmiyor.
--   3. Satırların **%98'i** proxy'den hiç geçmiyor: canlı döküm
--      `god_mode`=79, `bilinmiyor`=147, `llm_cascade`=4 (toplam 230).
--   4. `decision_log`'un birincil anahtarı **(id, decided_at) ÇİFTİ**
--      (`002:166`); tek başına `id` UNIQUE indeks bile kabul etmiyor
--      (`002:53`) ve id'ler `003:85-105` ile TOPLU yeniden numaralandı.
--   5. İki AYRI veritabanı (TimescaleDB pg16 ↔ Supabase pg17), aralarında
--      `postgres_fdw`/`dblink` YOK (`\dx`: yalnızca plpgsql + timescaledb).
--
-- Bu yüzden `decision_log` yetkili kaynak olarak **dokunulmadan** kalır;
-- burada tutulan şey kullanıcının KENDİ görüntüleme olayıdır.
--
-- ---------------------------------------------------------------------
-- ⚠ EN ÖNEMLİ TASARIM GEREKÇESİ — YENİ TABLO GÜVENSİZ DOĞAR
-- ---------------------------------------------------------------------
-- ÖLÇÜLDÜ (17.09.2026, canlı `supabase-db` üzerinde GERİ ALINAN bir
-- işlemde gerçek `CREATE TABLE` ile):
--
--   CREATE TABLE public._olcum_007 (...)
--     → relacl = {postgres=arwdDxtm, anon=arwdDxtm,
--                 authenticated=arwdDxtm, service_role=arwdDxtm}
--     → relrowsecurity = FALSE
--   _olcum_007_id_seq → {anon=rwU, authenticated=rwU, ...}
--   CREATE FUNCTION public._olcum_007_fn()
--     → proacl = {=X/postgres, anon=X, authenticated=X, ...}   ← PUBLIC EXECUTE
--
-- Kaynağı `pg_default_acl`'deki 6 satır (`postgres` ve `supabase_admin`
-- sahipliğinde, r/S/f tipleri için).
--
-- SONUÇ: **"GRANT yazmazsam kimse erişemez" bu veritabanında YANLIŞTIR.**
-- 006'nın `profiles`/`user_portfolios` üzerinde tek tek kapattığı
-- TRUNCATE + MAINTAIN + anon-yazma açığı, hiçbir REVOKE yazılmazsa bu
-- tabloda **ilk günden** yeniden açılırdı. Bu göç yetkileri AÇIKÇA geri alır.
--
-- Not: `pg_default_acl`'in KENDİSİ değiştirilmiyor (ALTER DEFAULT
-- PRIVILEGES). O, bu depodaki her gelecekteki tabloyu etkileyen sistemik
-- bir karardır ve Supabase'in kendi araçlarını da etkiler — ayrı bir
-- karar olarak Faz 5'e bırakıldı.
--
-- ---------------------------------------------------------------------
-- GİZLİLİK KARARI — YANIT GÖVDESİ SAKLANMIYOR
-- ---------------------------------------------------------------------
-- Gövdenin kendisi yerine `govde_saglamasi` (sha256) + `govde_bayt`
-- tutulur. Bu, çapraz-kullanıcı önbellek paylaşımını **kanıtlama** gücünü
-- korur (A ve B aynı baytları aldıysa sağlamaları eşittir) ama Supabase'de
-- kullanıcıya bağlı içerik biriktirmez.
--
-- `karar_kodu` (EKLE/TUT/BEKLE/DİKKAT ET) BİLEREK yok: kodu çıkaran regex
-- KORUNAN dosyadadır (`maa/src/main.py:1004-1008`); kenarda kopyalamak MAA
-- değiştiğinde sessiz sürüklenme üretir ve kod zaten `decision_log`'da
-- yetkili kaynağında durur.
--
-- ---------------------------------------------------------------------
-- IDEMPOTENT
-- ---------------------------------------------------------------------
-- CREATE ... IF NOT EXISTS, DROP POLICY IF EXISTS, CREATE OR REPLACE,
-- REVOKE (doğası gereği idempotent). Defalarca çalıştırılabilir.
--
-- ÇALIŞTIRMA:
--   docker exec -i supabase-db psql -U postgres -d postgres \
--     -v ON_ERROR_STOP=1 -f - < 007_supabase_kullanici_goruntuleme_kaydi.sql
-- =====================================================================

BEGIN;

-- --- 1) TABLO ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.kullanici_goruntuleme_kaydi (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- Kullanıcı silinince kayıtları da gider (KVKK "verimi sil" talebi).
    user_id          uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    -- Hangi ticker sorgulandı. NULL olabilir: ticker taşımayan uçlar var
    -- (ör. /api/maa/portfolio-signal/adaptive_rotation).
    ticker           text,
    -- Hangi yol istendi. Dar tutulur; sorgu dizesi SAKLANMAZ.
    istenen_yol      text        NOT NULL,
    -- Yanıt proxy önbelleğinden mi geldi? Çapraz-kullanıcı önbellek
    -- paylaşımını ölçmenin tek yolu bu alandır.
    onbellekten_mi   boolean     NOT NULL DEFAULT false,
    http_durum       smallint,
    -- Gövdenin KENDİSİ değil, sha256'sı (64 hex). Bkz. GİZLİLİK KARARI.
    govde_saglamasi  char(64),
    govde_bayt       integer,
    olusturulma_zamani timestamptz NOT NULL DEFAULT now()
);

-- Beklenen sorgu: "bu kullanıcının son N kaydı" → (user_id, zaman DESC).
CREATE INDEX IF NOT EXISTS ix_kgk_kullanici_zaman
    ON public.kullanici_goruntuleme_kaydi (user_id, olusturulma_zamani DESC);
-- Önbellek paylaşımı analizi: aynı sağlamayı kaç farklı kullanıcı aldı.
CREATE INDEX IF NOT EXISTS ix_kgk_saglama
    ON public.kullanici_goruntuleme_kaydi (govde_saglamasi)
    WHERE govde_saglamasi IS NOT NULL;

-- --- 2) RLS ----------------------------------------------------------
ALTER TABLE public.kullanici_goruntuleme_kaydi ENABLE ROW LEVEL SECURITY;

-- BUGÜN HİÇBİR SELECT POLİTİKASI YOK — bilinçli, fail-closed.
-- 006'nın disiplini: kullanılmayan yetki verilmez. "Geçmişim" ekranı bir
-- ürün gereksinimi hâline gelirse eklenecek olan tam metin:
--
--   GRANT SELECT ON public.kullanici_goruntuleme_kaydi TO authenticated;
--   CREATE POLICY kgk_kendi_kaydi ON public.kullanici_goruntuleme_kaydi
--       FOR SELECT USING (auth.uid() = user_id);
--
-- RLS yine de AÇIK: ileride biri `GRANT ALL ON ALL TABLES IN SCHEMA public
-- TO authenticated` gibi yaygın bir Supabase parçacığı çalıştırırsa ikinci
-- katman ayakta kalsın.

-- --- 3) SERTLEŞTİRME — yeni tablo GÜVENSİZ doğar, açıkça kapatılır ----
-- Bkz. yukarıdaki ölçüm. Bu bloklar OLMAZSA 006 ile kapatılan açık burada
-- ilk günden yeniden açılır.
REVOKE ALL ON public.kullanici_goruntuleme_kaydi FROM anon, authenticated;
REVOKE ALL ON SEQUENCE public.kullanici_goruntuleme_kaydi_id_seq
    FROM anon, authenticated;

-- --- 4) TEK YAZMA YOLU: SECURITY DEFINER fonksiyonu -------------------
-- Kullanıcı tabloya DOĞRUDAN yazamaz (yukarıda REVOKE edildi). Tek yol bu
-- fonksiyondur ve `user_id` PARAMETRE ALMAZ — zorla `auth.uid()` kullanır.
-- Böylece kullanıcı ne başkası adına satır üretebilir ne de user_id uydurabilir.
--
-- service_role anahtarı GEREKMEZ: ölçüldü ki frontend konteynerinde böyle bir
-- değişken YOK. Proxy, zaten elindeki kullanıcı çerezleriyle çağırır.
--
-- search_path = '' — 005'teki tetikle aynı sertleştirme: SECURITY DEFINER bir
-- fonksiyonda değiştirilebilir search_path bilinen bir ayrıcalık yükseltme
-- yoludur.
CREATE OR REPLACE FUNCTION public.goruntuleme_kaydi_yaz(
    p_istenen_yol     text,
    p_ticker          text        DEFAULT NULL,
    p_onbellekten_mi  boolean     DEFAULT false,
    p_http_durum      smallint    DEFAULT NULL,
    p_govde_saglamasi char(64)    DEFAULT NULL,
    p_govde_bayt      integer     DEFAULT NULL
) RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_kullanici uuid := auth.uid();
    v_id bigint;
BEGIN
    -- FAIL-CLOSED: oturumsuz çağrı kayıt üretemez. Bu bir GÖRÜNTÜLEME
    -- kaydıdır; izleyicisi olmayan cron/healthcheck trafiğinin burada işi yok.
    IF v_kullanici IS NULL THEN
        RAISE EXCEPTION 'goruntuleme_kaydi_yaz: oturum gerekli'
            USING ERRCODE = '42501';
    END IF;
    -- Yol dar tutulur: sorgu dizesi ve uzun metin saklanmaz.
    INSERT INTO public.kullanici_goruntuleme_kaydi
        (user_id, ticker, istenen_yol, onbellekten_mi,
         http_durum, govde_saglamasi, govde_bayt)
    VALUES
        (v_kullanici,
         left(p_ticker, 16),
         left(p_istenen_yol, 200),
         COALESCE(p_onbellekten_mi, false),
         p_http_durum,
         p_govde_saglamasi,
         p_govde_bayt)
    RETURNING id INTO v_id;
    RETURN v_id;
END;
$$;

-- Fonksiyon da GÜVENSİZ doğar: yeni fonksiyonda PUBLIC'in yerleşik EXECUTE
-- hakkı vardır (ölçüldü: proacl `=X/postgres` içeriyor). Önce TAMAMEN alınır,
-- sonra YALNIZCA `authenticated`'a verilir — `anon` çağıramaz.
REVOKE ALL ON FUNCTION public.goruntuleme_kaydi_yaz(
    text, text, boolean, smallint, char(64), integer) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.goruntuleme_kaydi_yaz(
    text, text, boolean, smallint, char(64), integer) TO authenticated;

COMMIT;

-- ---------------------------------------------------------------------
-- DOĞRULAMA
-- ---------------------------------------------------------------------
SELECT 'tablo_var' AS kontrol, COUNT(*)::text AS deger
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname = 'kullanici_goruntuleme_kaydi'
UNION ALL
SELECT 'rls_acik', (SELECT relrowsecurity::text FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname='public' AND c.relname='kullanici_goruntuleme_kaydi')
UNION ALL
-- Bu üçü SIFIR olmalı: yeni tablo güvensiz doğduğu için açıkça kapatıldı.
SELECT 'istemci_tablo_yetkisi_kalan', COUNT(*)::text
FROM information_schema.role_table_grants
WHERE table_schema='public' AND table_name='kullanici_goruntuleme_kaydi'
  AND grantee IN ('anon','authenticated')
UNION ALL
SELECT 'istemci_sequence_yetkisi_kalan', COUNT(*)::text
FROM information_schema.role_usage_grants
WHERE object_schema='public'
  AND object_name='kullanici_goruntuleme_kaydi_id_seq'
  AND grantee IN ('anon','authenticated')
UNION ALL
SELECT 'anon_fonksiyon_execute', COUNT(*)::text
FROM information_schema.role_routine_grants
WHERE routine_schema='public' AND routine_name='goruntuleme_kaydi_yaz'
  AND grantee IN ('anon','PUBLIC')
UNION ALL
-- Bu ikisi 1 OLMALI: meşru yol çalışıyor olmalı.
SELECT 'auth_fonksiyon_execute_OLMALI_1', COUNT(*)::text
FROM information_schema.role_routine_grants
WHERE routine_schema='public' AND routine_name='goruntuleme_kaydi_yaz'
  AND grantee='authenticated'
UNION ALL
-- DIKKAT: proconfig'de deger TIRNAKLI saklanir (`search_path=""`), bu yuzden
-- `@> ARRAY['search_path=']` esitligi TUTMAZ. Ilk surumde tam bu hata vardi ve
-- dogrulama, search_path GERCEKTEN sabitlenmis oldugu halde 0 donduruyordu.
-- Onek eslesmesi kullanilir.
SELECT 'fonksiyon_search_path_sabit_OLMALI_1', COUNT(*)::text
FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
WHERE n.nspname='public' AND p.proname='goruntuleme_kaydi_yaz'
  AND p.prosecdef
  AND EXISTS (SELECT 1 FROM unnest(p.proconfig) AS k WHERE k LIKE 'search_path=%')
UNION ALL
SELECT 'indeks_sayisi_OLMALI_3', COUNT(*)::text
FROM pg_indexes WHERE schemaname='public'
  AND tablename='kullanici_goruntuleme_kaydi';
