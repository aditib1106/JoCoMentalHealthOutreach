\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

-- =============================================================================
-- Bookings v2 (Jail MH 2, branch jail-mh2-fixes)
--
-- Change from v1 (semantic.bookings):
--   v1 joined to semantic.person_xwalk which hid people whose source id was
--   matched to more than one joid. v2 joins to semantic_v2.person_xwalk which
--   keeps every id and attaches check_linkage. Jail ids had no ambiguous
--   links in Update 1 so check_linkage is expected to be FALSE on every row,
--   but we carry it for schema uniformity across v2 tables.
--
-- Everything else is unchanged from v1:
--   * one row per booking_no (the source stores every booking twice);
--   * counters that let us check the duplicates were identical before
--     collapsing (n_source_rows, n_mni, release_conflict);
--   * jail MNI zero-padded to 9 characters before matching the crosswalk
--     (handled inside semantic_v2.person_xwalk via btrim on sourceid).
-- =============================================================================

-- Pull the foreign table once, collapsing the duplicate source rows per booking
CREATE TEMP TABLE tmp_bookings AS
SELECT booking_no,
       MIN(mni_no)                                           AS mni_no,
       MIN(booking_date)                                     AS booking_date,
       MIN(release_date)                                     AS release_date,
       BOOL_OR(joco_resident)                                AS joco_resident,
       MAX(bjmhs_referred)                                   AS bjmhs_referred,
       MAX(mhs_total)                                        AS mhs_total,
       MIN(btrim(sex))                                       AS sex,
       MIN(btrim(race))                                      AS race,
       MIN(EXTRACT(YEAR FROM date_of_birth))::int            AS birth_year,
       COUNT(*)                                              AS n_source_rows,
       COUNT(DISTINCT mni_no)                                AS n_mni,
       (MIN(release_date) IS DISTINCT FROM MAX(release_date)) AS release_conflict
FROM cleaned.jocojimsinmatedata
GROUP BY booking_no;

-- Attach entity_id and check_linkage via the v2 crosswalk.
-- The jail id must be zero-padded to 9 characters before matching sourceid,
-- which the crosswalk already stores btrimmed; we lpad on this side.
DROP TABLE IF EXISTS semantic_v2.bookings;
CREATE TABLE semantic_v2.bookings AS
SELECT x.entity_id,
       x.check_linkage,
       b.*
FROM tmp_bookings b
LEFT JOIN semantic_v2.person_xwalk x
       ON x.source    = 'jocoJIMSNameIndex.MNI_NO_0'
      AND x.source_id = lpad(b.mni_no::text, 9, '0');

CREATE UNIQUE INDEX ON semantic_v2.bookings (booking_no);
CREATE INDEX ON semantic_v2.bookings (entity_id, booking_date);
ANALYZE semantic_v2.bookings;
ALTER TABLE semantic_v2.bookings OWNER TO jail_mh2;
