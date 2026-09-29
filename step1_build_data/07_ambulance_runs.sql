\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

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

DROP TABLE IF EXISTS semantic.ambulance_runs;
CREATE TABLE semantic.ambulance_runs AS
SELECT x.entity_id, a.*
FROM tmp a
LEFT JOIN semantic.person_xwalk x
       ON x.source = 'jocoMEDACTIncidents.RcdID'
      AND x.source_id = a.hash_rcdid;

CREATE UNIQUE INDEX ON semantic.ambulance_runs (hash_rcdid);
CREATE INDEX ON semantic.ambulance_runs (entity_id, incident_ts);
ANALYZE semantic.ambulance_runs;
ALTER TABLE semantic.ambulance_runs OWNER TO jail_mh2;
