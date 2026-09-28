\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

CREATE TEMP TABLE tmp AS
SELECT urno, patient_no, encounter_date,
       btrim(program) AS program,
       btrim(cosite)  AS cosite,
       btrim(zip_code) AS zip_code,
       tract2010id
FROM raw.jocojcdheencounter;

DROP TABLE IF EXISTS semantic.health_dept;
CREATE TABLE semantic.health_dept AS
SELECT x.entity_id, e.*
FROM tmp e
LEFT JOIN semantic.person_xwalk x
       ON x.source = 'jocoJCDHEEncounter.Patient_no'
      AND x.source_id = e.patient_no::text;

CREATE INDEX ON semantic.health_dept (entity_id, encounter_date);
ANALYZE semantic.health_dept;
ALTER TABLE semantic.health_dept OWNER TO jail_mh2;
