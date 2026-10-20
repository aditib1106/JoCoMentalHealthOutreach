\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

-- =============================================================================
-- JCMHC diagnoses v2 (Jail MH 2, branch jail-mh2-fixes)
-- See 04_jcmhc_services_v2.sql for the full rationale. v2 keeps every row
-- and attaches check_linkage; v1 had dropped roughly 8% of diagnosis rows.
-- =============================================================================

CREATE TEMP TABLE tmp AS
SELECT patid,
       dx_date,
       btrim(dx_code)                       AS dx_code,
       btrim(diagnosis_description)         AS diagnosis_description,
       btrim(diagnosis_dsm5_classification) AS dsm5_classification
FROM cleaned.jocojcmhcdiagnoses;

DROP TABLE IF EXISTS semantic_v2.jcmhc_diagnoses;
CREATE TABLE semantic_v2.jcmhc_diagnoses AS
SELECT x.entity_id,
       x.n_entity_ids,
       x.check_linkage,
       d.*
FROM tmp d
LEFT JOIN semantic_v2.person_xwalk x
       ON x.source    = 'jocoJCMHCDemographics.PATID'
      AND x.source_id = d.patid::text;

CREATE INDEX ON semantic_v2.jcmhc_diagnoses (entity_id, dx_date);
ANALYZE semantic_v2.jcmhc_diagnoses;
ALTER TABLE semantic_v2.jcmhc_diagnoses OWNER TO jail_mh2;
