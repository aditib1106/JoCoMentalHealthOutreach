\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

-- =============================================================================
-- Health department encounters v2 (Jail MH 2, branch jail-mh2-fixes)
--
-- Reads from raw, not cleaned: the cleaned table is exactly double the raw
-- one (verified in Update 1 Phase 2). JCDHE patient ids had 0 ambiguous
-- links; check_linkage carried for schema uniformity.
-- =============================================================================

CREATE TEMP TABLE tmp AS
SELECT urno, patient_no, encounter_date,
       btrim(program) AS program,
       btrim(cosite)  AS cosite,
       btrim(zip_code) AS zip_code,
       tract2010id
FROM raw.jocojcdheencounter;

DROP TABLE IF EXISTS semantic_v2.health_dept;
CREATE TABLE semantic_v2.health_dept AS
SELECT x.entity_id,
       x.check_linkage,
       e.*
FROM tmp e
LEFT JOIN semantic_v2.person_xwalk x
       ON x.source    = 'jocoJCDHEEncounter.Patient_no'
      AND x.source_id = e.patient_no::text;

CREATE INDEX ON semantic_v2.health_dept (entity_id, encounter_date);
ANALYZE semantic_v2.health_dept;
ALTER TABLE semantic_v2.health_dept OWNER TO jail_mh2;

