\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

-- =============================================================================
-- JCMHC services v2 (Jail MH 2, branch jail-mh2-fixes)
--
-- Change from v1: the v1 build silently dropped rows whose patid was linked
-- to more than one joid in the county crosswalk. That removed roughly 12%
-- of service rows (about 559,145 of 4,609,027), tied to 2,820 patient ids.
-- The instructor asked us to keep every row and flag the ones with linkage
-- issues instead; v2 does that via semantic_v2.person_xwalk.check_linkage.
-- Rows where the patid does not appear in the crosswalk at all keep
-- entity_id NULL (same as v1) and check_linkage NULL.
-- =============================================================================

CREATE TEMP TABLE tmp AS
SELECT patid,
       svc_date,
       btrim(provider_id)  AS provider_id,
       btrim(svc_code)     AS svc_code,
       btrim(service_desc) AS service_desc
FROM cleaned.jocojcmhcservices;

DROP TABLE IF EXISTS semantic_v2.jcmhc_services;
CREATE TABLE semantic_v2.jcmhc_services AS
SELECT x.entity_id,
       x.n_entity_ids,
       x.check_linkage,
       s.*
FROM tmp s
LEFT JOIN semantic_v2.person_xwalk x
       ON x.source    = 'jocoJCMHCDemographics.PATID'
      AND x.source_id = s.patid::text;

CREATE INDEX ON semantic_v2.jcmhc_services (entity_id, svc_date);
ANALYZE semantic_v2.jcmhc_services;
ALTER TABLE semantic_v2.jcmhc_services OWNER TO jail_mh2;
