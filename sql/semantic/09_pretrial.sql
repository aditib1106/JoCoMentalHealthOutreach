\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

CREATE TEMP TABLE tmp AS
SELECT hash_pta_no, create_date,
       ks_resident, employed, age AS age_band, felony_flag, drug_flag,
       prior_jail_time, substance_flag, assessment_mh_flag,
       total_score, btrim(risk_level) AS risk_level, risk_level_int, no_assess
FROM cleaned.jocojimspretrialassessdata;

DROP TABLE IF EXISTS semantic.pretrial;
CREATE TABLE semantic.pretrial AS
SELECT b.entity_id, b.booking_date, (b.booking_no IS NOT NULL) AS booking_found, p.*
FROM tmp p
LEFT JOIN semantic.bookings b ON b.booking_no = p.hash_pta_no;

CREATE INDEX ON semantic.pretrial (entity_id, create_date);
ANALYZE semantic.pretrial;
ALTER TABLE semantic.pretrial OWNER TO jail_mh2;
