\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

CREATE TEMP TABLE tmp AS
SELECT patid, svc_date,
       btrim(provider_id)  AS provider_id,
       btrim(svc_code)     AS svc_code,
       btrim(service_desc) AS service_desc
FROM cleaned.jocojcmhcservices;

DROP TABLE IF EXISTS semantic.jcmhc_services;
CREATE TABLE semantic.jcmhc_services AS
SELECT x.entity_id, x.n_entity_ids, x.resolution, s.*
FROM tmp s
LEFT JOIN semantic.person_xwalk x
       ON x.source = 'jocoJCMHCDemographics.PATID'
      AND x.source_id = s.patid::text;

CREATE INDEX ON semantic.jcmhc_services (entity_id, svc_date);
ANALYZE semantic.jcmhc_services;
ALTER TABLE semantic.jcmhc_services OWNER TO jail_mh2;
