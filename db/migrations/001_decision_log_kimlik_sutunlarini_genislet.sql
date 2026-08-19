-- =====================================================================
-- 001 — decision_log kimlik sutunlarini varchar(20) -> varchar(64)
-- =====================================================================
-- Uygulandi   : 2026-08-20
-- Veritabani  : alphawise_db (TimescaleDB 2.28.2 / PostgreSQL 16.14)
-- Tablo       : public.decision_log (hypertable, 4 chunk)
--
-- ---------------------------------------------------------------------
-- SORUN: SESSIZ VERI KAYBI
-- ---------------------------------------------------------------------
-- MAA'nin /portfolio-signal/{strategy} uc noktasi (maa/src/main.py:1006-1013)
-- decision_log.ticker sutununa su degeri yaziyordu:
--
--     f"PORTFOLIO_{strategy}"
--
-- strategy="adaptive_rotation" ile bu deger 27 KARAKTER olur; sutun
-- sinirlari 20 idi. INSERT basarisiz oluyordu, ANCAK cagri kodu hatayi
-- try/except icinde yutup yalnizca logluyordu:
--
--     [portfolio_signal log] kayit hatasi: value too long for
--     type character varying(20)
--
-- Sonuc: uc nokta HTTP 200 donuyordu ama satir veritabanina HIC
-- yazilmiyordu. Cagrilar sessizce kayit disi kaliyordu. Tablodaki en
-- uzun ticker degerinin 5 karakter olmasi bunun kanitiydi — tasan
-- kayitlarin hicbiri diske ulasmamisti.
--
-- ---------------------------------------------------------------------
-- NEDEN GENISLETME, NEDEN KIRPMA DEGIL
-- ---------------------------------------------------------------------
-- Alternatif, cagri kodunda degeri 20 karaktere kirpmakti. Reddedildi:
--
--   1) BILGI KAYBI VE CAKISMA: "PORTFOLIO_adaptive_rotation" 20 karaktere
--      kirpilinca "PORTFOLIO_adaptive_r" olur. "PORTFOLIO_adaptive_rebalance"
--      gibi bir strateji de AYNI dizeye kirpilir ve iki farkli portfoy
--      ayni kimlikle kaydedilir. Kimlik sutununda bu kabul edilemez.
--
--   2) KORUNAN DOSYA: kirpma maa/src/main.py'yi degistirmeyi gerektirir;
--      bu dosya CLAUDE.md'de KORUNAN DOSYALAR listesindedir.
--
--   3) DEGERLER MESRU SEKILDE UZUN: depodaki mevcut strateji adlariyla
--      uretilecek en uzun deger
--      "PORTFOLIO_AdaptiveRotationConf_BIST_v1.0.yaml" = 45 karakter.
--      Sinir bu degerleri kesmemeli.
--
-- Genislik 64 secildi: bilinen en uzun deger 45 karakter, %42 pay birakir.
--
-- ---------------------------------------------------------------------
-- UC SUTUN DA NEDEN GENISLETILDI
-- ---------------------------------------------------------------------
--   ticker   : AKTIF ARIZALI (45 karaktere kadar deger, sinir 20)
--   decision : market_regime degerlerini de tasiyor; finrl-x'te tanimli
--              en uzun rejim "fast_risk_off" (13). Sinira 7 karakter
--              kalmisti; dis servisten gelen bir deger tasarsa AYNI
--              sessiz kayip yasanirdi.
--   source   : yalnizca kodda sabit degerler ("llm_cascade" = 11).
--              Su an tasma riski yok, ama ayni kirilma bicimini paylasan
--              bir sutunu dar birakmak ileride tuzak olur. Genisletme
--              maliyeti sifir oldugu icin tutarlilik tercih edildi.
--
-- ---------------------------------------------------------------------
-- ETKI: TABLO YENIDEN YAZILMAZ
-- ---------------------------------------------------------------------
-- PostgreSQL'de varchar(n) uzunlugunu ARTIRMAK yalnizca katalog
-- guncellemesidir; tablo yeniden yazilmaz. Uygulama sonrasi
-- relfilenode degerleri (parent + 4 chunk + 4 indeks) DEGISMEDI:
-- dogrulandi. 114 satirlik veri parmak izi (md5) de ayni kaldi.
--
-- TimescaleDB, hypertable uzerindeki ALTER TABLE'i chunk'lara OTOMATIK
-- yayar; 4 chunk'in tamami varchar(64) oldu (dogrulandi).
--
-- ---------------------------------------------------------------------
-- CALISTIRMA
-- ---------------------------------------------------------------------
--   docker exec -i alphawise-timescaledb \
--     psql -U alphawise -d alphawise_db -f - < 001_...sql
--
-- NOT: "docker exec" komutunda -i BAYRAGI ZORUNLUDUR. Onsuz stdin
-- baglanmaz, psql hicbir girdi almaz ve komut sessizce hicbir sey
-- yapmadan basariyla doner.
--
-- Betik idempotenttir: zaten uygulanmissa hicbir sey yapmaz.
-- =====================================================================

BEGIN;

DO $$
DECLARE
    v_sutun   text;
    v_mevcut  integer;
    v_hedef   integer := 64;
BEGIN
    FOREACH v_sutun IN ARRAY ARRAY['ticker', 'decision', 'source']
    LOOP
        SELECT a.atttypmod - 4
          INTO v_mevcut
          FROM pg_attribute a
          JOIN pg_class c ON c.oid = a.attrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'public'
           AND c.relname = 'decision_log'
           AND a.attname = v_sutun
           AND a.attnum > 0
           AND NOT a.attisdropped;

        IF v_mevcut IS NULL THEN
            RAISE EXCEPTION 'decision_log.% sutunu bulunamadi', v_sutun;
        ELSIF v_mevcut >= v_hedef THEN
            RAISE NOTICE 'decision_log.% zaten varchar(%) — atlandi', v_sutun, v_mevcut;
        ELSE
            EXECUTE format(
                'ALTER TABLE public.decision_log ALTER COLUMN %I TYPE varchar(%s)',
                v_sutun, v_hedef);
            RAISE NOTICE 'decision_log.% : varchar(%) -> varchar(%)',
                v_sutun, v_mevcut, v_hedef;
        END IF;
    END LOOP;
END $$;

COMMIT;

-- ---------------------------------------------------------------------
-- DOGRULAMA: parent + TUM chunk'lar varchar(64) olmali (15 satir)
-- ---------------------------------------------------------------------
SELECT c.relname AS tablo,
       a.attname AS sutun,
       format_type(a.atttypid, a.atttypmod) AS tip
  FROM pg_attribute a
  JOIN pg_class c ON c.oid = a.attrelid
 WHERE a.attname IN ('ticker', 'decision', 'source')
   AND (c.relname = 'decision_log' OR c.relname LIKE '_hyper_2_%_chunk')
   AND a.attnum > 0
   AND NOT a.attisdropped
 ORDER BY c.relname, a.attnum;
