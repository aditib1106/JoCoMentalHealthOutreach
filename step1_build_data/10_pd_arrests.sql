\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

CREATE TEMP TABLE tmp AS
SELECT armainid, name_identifier, date_arr,
       btrim(charge)   AS charge,
       btrim(arr_type) AS arr_type,
       btrim(agency)   AS agency,
       joco_resident, arstatus, arre_id, case_id
FROM cleaned.jocopdarrests;

DROP TABLE IF EXISTS semantic.pd_arrests;
CREATE TABLE semantic.pd_arrests AS
SELECT x.entity_id, x.resolution, a.*
FROM tmp a
LEFT JOIN semantic.person_xwalk x
       ON x.source = 'jocoPDArrests.NAME_ID'
      AND x.source_id = a.name_identifier::bigint::text;

CREATE UNIQUE INDEX ON semantic.pd_arrests (armainid);
CREATE INDEX ON semantic.pd_arrests (entity_id, date_arr);
ANALYZE semantic.pd_arrests;
ALTER TABLE semantic.pd_arrests OWNER TO jail_mh2;
