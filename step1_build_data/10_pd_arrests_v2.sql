\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

-- =============================================================================
-- Police arrests v2 (Jail MH 2, branch jail-mh2-fixes)
-- Keeps every row and attaches check_linkage via semantic_v2.person_xwalk.
-- 128 PD source ids had ambiguous links in Update 1; v1 silently dropped
-- the roughly 593 arrest rows tied to them. v2 keeps them.
-- =============================================================================

CREATE TEMP TABLE tmp AS
SELECT armainid, name_identifier, date_arr,
       btrim(charge)   AS charge,
       btrim(arr_type) AS arr_type,
       btrim(agency)   AS agency,
       joco_resident, arstatus, arre_id, case_id
FROM cleaned.jocopdarrests;

DROP TABLE IF EXISTS semantic_v2.pd_arrests;
CREATE TABLE semantic_v2.pd_arrests AS
SELECT x.entity_id,
       x.check_linkage,
       a.*
FROM tmp a
LEFT JOIN semantic_v2.person_xwalk x
       ON x.source    = 'jocoPDArrests.NAME_ID'
      AND x.source_id = a.name_identifier::bigint::text;

CREATE UNIQUE INDEX ON semantic_v2.pd_arrests (armainid);
CREATE INDEX ON semantic_v2.pd_arrests (entity_id, date_arr);
ANALYZE semantic_v2.pd_arrests;
ALTER TABLE semantic_v2.pd_arrests OWNER TO jail_mh2;
