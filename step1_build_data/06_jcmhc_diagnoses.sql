\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

CREATE TEMP TABLE tmp AS
SELECT patid, dx_date,
       btrim(dx_code)                       AS dx_code,
       btrim(diagnosis_description)         AS diagnosis_description,
       btrim(diagnosis_dsm5_classification) AS dsm5_classification
FROM cleaned.jocojcmhcdiagnoses;

DROP TABLE IF EXISTS semantic.jcmhc_diagnoses;
CREATE TABLE semantic.jcmhc_diagnoses AS
SELECT x.entity_id, x.n_entity_ids, x.resolution, d.*
FROM tmp d
LEFT JOIN semantic.person_xwalk x
       ON x.source = 'jocoJCMHCDemographics.PATID'
      AND x.source_id = d.patid::text;

CREATE INDEX ON semantic.jcmhc_diagnoses (entity_id, dx_date);
ANALYZE semantic.jcmhc_diagnoses;
ALTER TABLE semantic.jcmhc_diagnoses OWNER TO jail_mh2;
