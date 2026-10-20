\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

-- =============================================================================
-- JCMHC crisis calls v2 (Jail MH 2, branch jail-mh2-fixes)
-- See 04_jcmhc_services_v2.sql for the full rationale. v2 keeps every row
-- and attaches check_linkage; v1 had dropped roughly 10% of call rows.
-- =============================================================================

CREATE TEMP TABLE tmp AS
SELECT patid,
       call_date,
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

DROP TABLE IF EXISTS semantic_v2.jcmhc_calls;
CREATE TABLE semantic_v2.jcmhc_calls AS
SELECT x.entity_id,
       x.n_entity_ids,
       x.check_linkage,
       c.*
FROM tmp c
LEFT JOIN semantic_v2.person_xwalk x
       ON x.source    = 'jocoJCMHCDemographics.PATID'
      AND x.source_id = c.patid::text;

CREATE INDEX ON semantic_v2.jcmhc_calls (entity_id, call_date);
ANALYZE semantic_v2.jcmhc_calls;
ALTER TABLE semantic_v2.jcmhc_calls OWNER TO jail_mh2;
