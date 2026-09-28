\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

-- 1. Pull the foreign table once, collapsing the duplicate rows
CREATE TEMP TABLE tmp_bookings AS
SELECT booking_no,
       MIN(mni_no)                                  AS mni_no,
       MIN(booking_date)                            AS booking_date,
       MIN(release_date)                            AS release_date,
       BOOL_OR(joco_resident)                       AS joco_resident,
       MAX(bjmhs_referred)                          AS bjmhs_referred,
       MAX(mhs_total)                               AS mhs_total,
       MIN(btrim(sex))                              AS sex,
       MIN(btrim(race))                             AS race,
       MIN(EXTRACT(YEAR FROM date_of_birth))::int   AS birth_year,
       COUNT(*)                                     AS n_source_rows,
       COUNT(DISTINCT mni_no)                       AS n_mni,
       (MIN(release_date) IS DISTINCT FROM MAX(release_date)) AS release_conflict
FROM cleaned.jocojimsinmatedata
GROUP BY booking_no;

-- 2. Attach entity_id locally (jail id must be zero-padded to 9 characters)
DROP TABLE IF EXISTS semantic.bookings;
CREATE TABLE semantic.bookings AS
SELECT x.entity_id, b.*
FROM tmp_bookings b
LEFT JOIN semantic.person_xwalk x
       ON x.source    = 'jocoJIMSNameIndex.MNI_NO_0'
      AND x.source_id = lpad(b.mni_no::text, 9, '0');

CREATE UNIQUE INDEX ON semantic.bookings (booking_no);
CREATE INDEX ON semantic.bookings (entity_id, booking_date);
ANALYZE semantic.bookings;

ALTER TABLE semantic.bookings OWNER TO jail_mh2;
