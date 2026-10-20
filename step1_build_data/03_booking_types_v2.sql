\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

-- =============================================================================
-- Booking types v2 (Jail MH 2, branch jail-mh2-fixes)
--
-- Same shape as semantic.booking_types; written to semantic_v2 so Update 1
-- and Update 2 remain reproducible from the frozen branches.
--
-- One row per booking_no with the full set of booking types that appear on
-- its charges. book_type is character padded, so we btrim before de-dup.
-- Downstream label definitions in step3_triage/mcrt_triage_config.yaml
-- compare against this array with && to decide whether a booking is a
-- "new-arrest booking" (VIEW / WARR / BW).
-- =============================================================================

CREATE TEMP TABLE tmp_charges AS
SELECT booking_no,
       NULLIF(btrim(book_type), '') AS book_type
FROM cleaned.jocojimsinmatecharges;

DROP TABLE IF EXISTS semantic_v2.booking_types;
CREATE TABLE semantic_v2.booking_types AS
SELECT booking_no,
       array_agg(DISTINCT book_type ORDER BY book_type)
           FILTER (WHERE book_type IS NOT NULL) AS book_types,
       COUNT(*)                                 AS n_charges
FROM tmp_charges
GROUP BY booking_no;

CREATE UNIQUE INDEX ON semantic_v2.booking_types (booking_no);
ANALYZE semantic_v2.booking_types;
ALTER TABLE semantic_v2.booking_types OWNER TO jail_mh2;
