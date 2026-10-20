\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

-- =============================================================================
-- Pretrial assessments v2 (Jail MH 2, branch jail-mh2-fixes)
--
-- The pretrial number IS the hashed booking number, so each pretrial row
-- joins straight to semantic_v2.bookings (no crosswalk hop). check_linkage
-- is inherited from the booking.
-- =============================================================================

CREATE TEMP TABLE tmp AS
SELECT hash_pta_no, create_date,
       ks_resident, employed, age AS age_band, felony_flag, drug_flag,
       prior_jail_time, substance_flag, assessment_mh_flag,
       total_score, btrim(risk_level) AS risk_level, risk_level_int, no_assess
FROM cleaned.jocojimspretrialassessdata;

DROP TABLE IF EXISTS semantic_v2.pretrial;
CREATE TABLE semantic_v2.pretrial AS
SELECT b.entity_id,
       b.check_linkage,
       b.booking_date,
       (b.booking_no IS NOT NULL) AS booking_found,
       p.*
FROM tmp p
LEFT JOIN semantic_v2.bookings b ON b.booking_no = p.hash_pta_no;

CREATE INDEX ON semantic_v2.pretrial (entity_id, create_date);
ANALYZE semantic_v2.pretrial;
ALTER TABLE semantic_v2.pretrial OWNER TO jail_mh2;
