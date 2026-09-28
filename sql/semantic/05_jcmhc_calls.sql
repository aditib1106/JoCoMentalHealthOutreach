\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

CREATE TEMP TABLE tmp AS
SELECT patid, call_date,
       btrim(call_type)             AS call_type,
       btrim(unit)                  AS unit,
       btrim(status)                AS status,
       btrim(presenting_issue)      AS presenting_issue,
       btrim(suicide_homicide_risk) AS suicide_homicide_risk,
       btrim(degree_of_risk)        AS degree_of_risk,
       btrim(visit_type)            AS visit_type,
       btrim(sud_acuity)            AS sud_acuity,
       btrim(sud_risk_factors)      AS sud_risk_factors,
       btrim(disposition)           AS disposition
FROM cleaned.jocojcmhccalldetails;

DROP TABLE IF EXISTS semantic.jcmhc_calls;
CREATE TABLE semantic.jcmhc_calls AS
SELECT x.entity_id, x.n_entity_ids, x.resolution, c.*
FROM tmp c
LEFT JOIN semantic.person_xwalk x
       ON x.source = 'jocoJCMHCDemographics.PATID'
      AND x.source_id = c.patid::text;

CREATE INDEX ON semantic.jcmhc_calls (entity_id, call_date);
ANALYZE semantic.jcmhc_calls;
ALTER TABLE semantic.jcmhc_calls OWNER TO jail_mh2;
