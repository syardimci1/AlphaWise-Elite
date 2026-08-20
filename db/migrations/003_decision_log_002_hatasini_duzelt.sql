-- =====================================================================
-- 003 — decision_log: 002 migration'indaki ctid hatasini duzeltir
-- =====================================================================
-- Uygulandi   : 2026-08-20
-- Veritabani  : alphawise_db (TimescaleDB 2.28.2 / PostgreSQL 16.14)
--
-- ---------------------------------------------------------------------
-- 002'DE BULUNAN HATA: ctid HYPERTABLE'DA GLOBAL BENZERSIZ DEGIL
-- ---------------------------------------------------------------------
-- 002 migration'i, tekrarlanan id'leri yeniden numaralandirmak icin
-- su deseni kullandi:
--
--   UPDATE decision_log SET id = v_yeni_id WHERE ctid = v_kayit.ctid;
--
-- Bu YANLISTI. decision_log bir hypertable'dir; fiziksel olarak birden
-- fazla ayri tabloya (chunk) bolunmustur. `ctid` yalnizca TEK BIR fiziksel
-- tablo icinde benzersizdir — FARKLI chunk'lardaki satirlar AYNI ctid
-- degerine (orn. (0,1)) sahip olabilir. `UPDATE ... WHERE ctid = X`
-- hypertable'in TAMAMINA karsi calistirilinca, ayni ctid'ye sahip TUM
-- chunk'lardaki satirlari AYNI ANDA guncelledi.
--
-- SONUC: 002 calistiktan sonra dogrulama sorgusu 0 degil 44 tekrarlanan
-- id grubu gosterdi. Ornegin id=107, birbirinden tamamen BAGIMSIZ 4 farkli
-- eski kayidi (07-21, 07-25, 08-01, 08-20 tarihli) ustune almisti — cunku
-- bu 4 satir 4 ayri chunk'ta ayni ctid'yi paylasiyordu.
--
-- IYI HABER: HICBIR VERI KAYBOLMADI VE BOZULMADI. Icerik parmak izi
-- (ticker|decision|decided_at|source|price_at_decision, id HARIC) hem
-- 002'den ONCE hem 002'den SONRA birebir ayni: 548060bbf52f0d841f2147eb0f4f5c12.
-- Ayrica (id, decided_at) cifti hala benzersizdi (PRIMARY KEY bu yuzden
-- basariyla eklenebildi) — sadece id DEGERLERI yanlis dagitildi, satirlarin
-- kendisi bozulmadi.
--
-- ---------------------------------------------------------------------
-- DUZELTME: ctid DEGIL, (id, decided_at) CIFTI ILE ESLESTIRME
-- ---------------------------------------------------------------------
-- 002 migration'i PRIMARY KEY (id, decided_at) eklemeyi BASARDI — yani
-- bu cift GERCEKTEN benzersiz. Bu betik, gecici bir eslesme tablosunda
-- (mevcut id, mevcut decided_at) -> (yeni id) haritasini kurar ve
-- UPDATE'i SUTUN DEGERLERINE gore yapar, ctid'ye degil. Sutun degeri
-- eslestirmesi TimescaleDB'de her zaman guvenlidir; planlayici dogru
-- chunk'a yonlendirir.
--
-- IKI FAZLI GUNCELLEME: PRIMARY KEY aktifken tek adimda yeniden
-- numaralandirma, gecici olarak baska bir satirin MEVCUT id'siyle
-- carpisabilir (kisit ihlali). Bu yuzden:
--   FAZ 1: tum id'ler CAKISMASIZ bir gecici araliga tasinir (+100000)
--   FAZ 2: gecici araliktan NIHAI, temiz sirali id'lere gecilir
-- Bu iki fazda da hicbir asamada iki satir ayni id'yi paylasmaz.
--
-- ---------------------------------------------------------------------
-- CALISTIRMA
-- ---------------------------------------------------------------------
--   docker exec -i alphawise-timescaledb \
--     psql -U alphawise -d alphawise_db -f - < 003_...sql
--
-- Idempotenttir: id'ler zaten benzersizse (COUNT(*) GROUP BY id hepsi 1)
-- hicbir sey yapmadan atlar.
-- =====================================================================

BEGIN;

DO $$
DECLARE
    v_tekrar_var boolean;
    v_toplam_once integer;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM (SELECT id FROM decision_log GROUP BY id HAVING COUNT(*) > 1) x
    ) INTO v_tekrar_var;

    IF NOT v_tekrar_var THEN
        RAISE NOTICE 'id zaten benzersiz — duzeltme gerekmiyor, atlandi';
        RETURN;
    END IF;

    SELECT COUNT(*) INTO v_toplam_once FROM decision_log;
    RAISE NOTICE 'Duzeltme basliyor. Islem oncesi toplam satir: %', v_toplam_once;

    -- Gecici eslesme tablosu: SUTUN DEGERLERINE gore (ctid'ye DEGIL).
    -- decided_at + eski id ile birlikte GERCEK bir sira numarasi (temp_key)
    -- tutulur ki her satir tekil sekilde hedeflenebilsin.
    CREATE TEMP TABLE _id_esleme AS
    SELECT
        id AS eski_id,
        decided_at AS eski_decided_at,
        ROW_NUMBER() OVER (ORDER BY decided_at ASC, id ASC) AS yeni_id
    FROM decision_log;

    -- FAZ 1: cakismasiz gecici araliga tasi (+100000).
    -- decided_at DEGISMEZ, sadece id degisir; eslestirme (eski_id, eski_decided_at)
    -- SUTUN DEGERLERINE gore yapilir.
    UPDATE decision_log dl
    SET id = e.yeni_id + 100000
    FROM _id_esleme e
    WHERE dl.id = e.eski_id AND dl.decided_at = e.eski_decided_at;

    RAISE NOTICE 'FAZ 1 tamamlandi: tum id + 100000 gecici araligina tasindi';

    -- FAZ 2: gecici araliktan nihai, temiz sirali id'lere gec.
    UPDATE decision_log dl
    SET id = e.yeni_id
    FROM _id_esleme e
    WHERE dl.id = e.yeni_id + 100000 AND dl.decided_at = e.eski_decided_at;

    RAISE NOTICE 'FAZ 2 tamamlandi: nihai id degerleri atandi';

    DROP TABLE _id_esleme;

    IF (SELECT COUNT(*) FROM decision_log) != v_toplam_once THEN
        RAISE EXCEPTION 'SATIR SAYISI DEGISTI (once %, simdi %) — ISLEM DURDURULUYOR',
            v_toplam_once, (SELECT COUNT(*) FROM decision_log);
    END IF;
END $$;

-- Sequence'i yeni MAX(id)'nin uzerine sabitle.
SELECT setval(
    'decision_log_id_seq',
    GREATEST((SELECT MAX(id) FROM decision_log), 1),
    true
);

COMMIT;

-- ---------------------------------------------------------------------
-- DOGRULAMA
-- ---------------------------------------------------------------------
SELECT 'tekrarlanan_id_grubu' AS kontrol, COUNT(*) AS deger
FROM (SELECT id FROM decision_log GROUP BY id HAVING COUNT(*) > 1) x
UNION ALL
SELECT 'toplam_satir', COUNT(*) FROM decision_log
UNION ALL
SELECT 'primary_key_var_mi', COUNT(*)::int
FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid
WHERE t.relname = 'decision_log' AND c.contype = 'p';
