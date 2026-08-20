-- =====================================================================
-- 002 — decision_log: tekrarlanan id'lerin temizlenmesi + PRIMARY KEY
-- =====================================================================
-- Uygulandi   : 2026-08-20
-- Veritabani  : alphawise_db (TimescaleDB 2.28.2 / PostgreSQL 16.14)
-- Tablo       : public.decision_log (hypertable, partition sutunu decided_at)
--
-- ---------------------------------------------------------------------
-- SORUN: id BENZERSIZLIGI HIC ZORLANMIYORDU
-- ---------------------------------------------------------------------
-- decision_log.id bir sequence'ten (nextval) besleniyordu ama uzerinde
-- HICBIR PRIMARY KEY / UNIQUE kisit yoktu. Sequence bir noktada geriye
-- sifirlanmis (sebebi tespit edilemedi — muhtemelen erken bir manuel
-- sifirlama), bu yuzden yeni INSERT'ler eski, halihazirda kullanilmis
-- id degerleriyle carpisti.
--
-- Tespit edilen kapsam (2026-08-20, ilk tarama):
--   53 farkli id, HER BIRI tam olarak 2 satirda gecen — toplam 106 satir
--   etkilendi (159 satirlik tablonun %67'si).
--
-- Sequence durumu bozulmayi kanitliyordu: decision_log_id_seq.last_value=54
-- iken MAX(id)=106 idi — sequence ZATEN gerideydi, bir sonraki INSERT
-- (id=55) mevcut bir satirla ANINDA carpisacakti. Bu aktif, devam eden
-- bir arizaydi, gecmiste kalmis degil.
--
-- ---------------------------------------------------------------------
-- 53 CIFTIN HICBIRI TAM KOPYA DEGIL — HICBIR SATIR SILINMEDI
-- ---------------------------------------------------------------------
-- Dogrulama (push oncesi calistirildi):
--   SELECT ticker, decision, decided_at, source, price_at_decision, COUNT(*)
--   FROM decision_log GROUP BY 1,2,3,4,5 HAVING COUNT(*)>1;
--   -> 0 SATIR. Ayni id'yi paylasan her cift GERCEKTEN FARKLI karardir
--   (farkli ticker, farkli decided_at, farkli source). Bu yuzden silme
--   DEGIL, yeniden numaralandirma stratejisi uygulandi.
--
-- ---------------------------------------------------------------------
-- STRATEJI: MINIMAL MUDAHALE
-- ---------------------------------------------------------------------
-- 159 satirin TAMAMINI yeniden numaralandirmak yerine, her 53'lu
-- carpisan ciftte:
--   - KRONOLOJIK OLARAK DAHA ESKI olan satir ORIJINAL id'sinde KALIR
--   - DAHA YENI olan satira, MAX(id)+1'den baslayan YENI bir id verilir
-- Boylece 53 satir yeniden numaralandirilir, digerlerine dokunulmaz.
-- decided_at hypertable'in partition sutunu oldugu icin sirayi belirlemek
-- dogal ve gecerlidir.
--
-- ---------------------------------------------------------------------
-- NEDEN "PRIMARY KEY (id)" TEK BASINA DEGIL — TimescaleDB KISITI
-- ---------------------------------------------------------------------
-- Canli test edildi (BEGIN/ROLLBACK ile, kalici degisiklik yapilmadan):
--
--   ALTER TABLE decision_log ADD PRIMARY KEY (id);
--   ERROR: cannot create a unique index without the column "decided_at"
--          (used in partitioning)
--   HINT: If you're creating a hypertable on a table with a primary key,
--         ensure the partitioning column is part of the primary or
--         composite key.
--
-- TimescaleDB, hypertable'larda partition sutununu ICERMEYEN hicbir
-- UNIQUE/PRIMARY KEY indeksine izin vermez — bu PostgreSQL/TimescaleDB'nin
-- yapisal bir kuralidir, atlatilamaz (tabloyu normal PostgreSQL tablosuna
-- cevirmek disinda, ki bu zaman-serisi chunk'lama avantajini kaybettirir
-- ve bu gorevin kapsami disindadir).
--
-- Bu yuzden kisit PRIMARY KEY (id, decided_at) olarak eklendi. Bu,
-- TimescaleDB'nin izin verdigi EN GUCLU kisittir. Pratikte id benzersizligi
-- SU IKI SEYE dayanir:
--   1) Bu migration sonrasi TUM id degerleri gercekten benzersiz (yukarida
--      dogrulandi — asagida da tekrar dogrulanir)
--   2) Sequence dogru degere ayarlaniyor (asagida) ve BIR DAHA elle
--      sifirlanmadigi surece yeni carpisma olmaz
--
-- DURUST SINIRLAMA: (id, decided_at) kisiti, ayni id'nin FARKLI bir
-- decided_at ile tekrar EKLENMESINI veritabani seviyesinde ENGELLEMEZ —
-- yalnizca ayni (id, decided_at) ciftinin tekrarini engeller. Gercek
-- koruma, sequence'in dogru tutulmasina baglidir. Bu, TimescaleDB
-- hypertable'lari icin standart, kabul edilen bir modeldir.
--
-- AYRI ONERI (bu migration'in kapsami disinda, KOD DEGISIKLIGI gerektirir):
-- maa/src/main.py:915 (evaluate_decisions) "UPDATE decision_log SET ...
-- WHERE id = %s" kullaniyor — decided_at'i de WHERE kosuluna eklemek
-- ek bir savunma katmani olurdu. main.py CLAUDE.md'de KORUNAN DOSYA
-- oldugu icin bu migration'da DEGISTIRILMEDI; ayri bir gorev/onay
-- gerektirir.
--
-- ---------------------------------------------------------------------
-- CALISTIRMA
-- ---------------------------------------------------------------------
--   docker exec -i alphawise-timescaledb \
--     psql -U alphawise -d alphawise_db -f - < 002_...sql
--
-- NOT: "docker exec" komutunda -i BAYRAGI ZORUNLUDUR (onsuz stdin
-- baglanmaz, komut sessizce hicbir sey yapmadan biter).
--
-- Betik idempotenttir: PK zaten varsa ve tekrar eden id yoksa atlar.
-- =====================================================================

BEGIN;

-- --------------------------------------------------------------
-- ADIM 1: tekrarlanan id'leri yeniden numaralandir (yalnizca gerekliyse)
-- --------------------------------------------------------------
DO $$
DECLARE
    v_max_id      integer;
    v_yeni_id     integer;
    v_kayit       RECORD;
    v_pk_var_mi   boolean;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        WHERE t.relname = 'decision_log' AND c.contype = 'p'
    ) INTO v_pk_var_mi;

    IF v_pk_var_mi THEN
        RAISE NOTICE 'decision_log zaten PRIMARY KEY icin — yeniden numaralandirma atlandi';
        RETURN;
    END IF;

    SELECT COALESCE(MAX(id), 0) INTO v_max_id FROM decision_log;
    v_yeni_id := v_max_id;

    -- Her tekrarlanan id grubunda: en eski satir (decided_at'e gore)
    -- ORIJINAL id'sinde kalir; digerleri MAX(id)+1'den baslayan yeni
    -- id'ler alir. ctid kullanilir (bu asamada id+decided_at henuz
    -- PK olmadigi icin, tekil fiziksel satiri hedeflemenin en guvenli yolu).
    FOR v_kayit IN
        SELECT ctid, id, decided_at,
               ROW_NUMBER() OVER (PARTITION BY id ORDER BY decided_at ASC) AS sira
        FROM decision_log
        WHERE id IN (SELECT id FROM decision_log GROUP BY id HAVING COUNT(*) > 1)
        ORDER BY id, decided_at
    LOOP
        IF v_kayit.sira > 1 THEN
            v_yeni_id := v_yeni_id + 1;
            UPDATE decision_log SET id = v_yeni_id WHERE ctid = v_kayit.ctid;
            RAISE NOTICE 'id % (decided_at %) -> yeni id %',
                v_kayit.id, v_kayit.decided_at, v_yeni_id;
        END IF;
    END LOOP;

    RAISE NOTICE 'Yeniden numaralandirma tamamlandi. Yeni MAX(id) = %',
        (SELECT MAX(id) FROM decision_log);
END $$;

-- --------------------------------------------------------------
-- ADIM 2: sequence'i dogru degere sabitle (bir sonraki carpismayi onler)
-- --------------------------------------------------------------
SELECT setval(
    'decision_log_id_seq',
    GREATEST((SELECT MAX(id) FROM decision_log), 1),
    true
);

-- --------------------------------------------------------------
-- ADIM 3: PRIMARY KEY ekle (idempotent — zaten varsa atlanir)
-- --------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        WHERE t.relname = 'decision_log' AND c.contype = 'p'
    ) THEN
        ALTER TABLE public.decision_log ADD PRIMARY KEY (id, decided_at);
        RAISE NOTICE 'PRIMARY KEY (id, decided_at) eklendi';
    ELSE
        RAISE NOTICE 'PRIMARY KEY zaten mevcut — atlandi';
    END IF;
END $$;

COMMIT;

-- ---------------------------------------------------------------------
-- DOGRULAMA: hicbir tekrarlanan id kalmamali, PK var olmali
-- ---------------------------------------------------------------------
SELECT 'tekrarlanan_id_grubu' AS kontrol, COUNT(*) AS deger
FROM (SELECT id FROM decision_log GROUP BY id HAVING COUNT(*) > 1) x
UNION ALL
SELECT 'toplam_satir', COUNT(*) FROM decision_log
UNION ALL
SELECT 'primary_key_var_mi', COUNT(*)::int
FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid
WHERE t.relname = 'decision_log' AND c.contype = 'p';
