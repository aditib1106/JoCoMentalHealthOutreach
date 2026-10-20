\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

-- =============================================================================
-- Ambulance runs v2 (Jail MH 2, branch jail-mh2-fixes)
--
-- Each incident is stored on two rows in cleaned.jocomedactincidents, so we
-- collapse to one row per hash_rcdid and record counters that let us check
-- the two copies agreed before collapsing. hash_rcdid identifies an
-- incident, not a person; one person can have many.
--
-- Change from v1: joins to semantic_v2.person_xwalk and keeps every row,
-- attaching check_linkage. Ambulance ids had 0 ambiguous links in Update 1
-- so check_linkage should be FALSE on every row; kept for schema uniformity.
-- =============================================================================

CREATE TEMP TABLE tmp AS
SELECT lower(hash_rcdid)                  AS hash_rcdid,
       MIN(incidentdate)                  AS incident_ts,
       MIN(btrim(primaryimpression))      AS primary_impression,
       MIN(btrim(secondaryimpression))    AS secondary_impression,
       MIN(btrim(chiefcomplaint))         AS chief_complaint,
       MIN(btrim(triage))                 AS triage,
       MIN(btrim(disposition))            AS disposition,
       BOOL_OR(transported)               AS transported,
       BOOL_OR(treated)                   AS treated,
       BOOL_OR(homeless)                  AS homeless,
       BOOL_OR(joco_resident)             AS joco_resident,
       COUNT(*)                           AS n_source_rows,
       COUNT(DISTINCT incidentdate)       AS n_distinct_dates,
       COUNT(DISTINCT primaryimpression)  AS n_distinct_primary
FROM cleaned.jocomedactincidents
GROUP BY 1;

DROP TABLE IF EXISTS semantic_v2.ambulance_runs;
CREATE TABLE semantic_v2.ambulance_runs AS
SELECT x.entity_id,
       x.check_linkage,
       a.*
FROM tmp a
LEFT JOIN semantic_v2.person_xwalk x
       ON x.source    = 'jocoMEDACTIncidents.RcdID'
      AND x.source_id = a.hash_rcdid;

CREATE UNIQUE INDEX ON semantic_v2.ambulance_runs (hash_rcdid);
CREATE INDEX ON semantic_v2.ambulance_runs (entity_id, incident_ts);
ANALYZE semantic_v2.ambulance_runs;
ALTER TABLE semantic_v2.ambulance_runs OWNER TO jail_mh2;
