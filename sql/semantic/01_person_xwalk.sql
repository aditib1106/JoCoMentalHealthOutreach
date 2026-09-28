\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

DROP TABLE IF EXISTS semantic.person_xwalk;

CREATE TABLE semantic.person_xwalk AS
SELECT source,
       CASE WHEN sourceid IS NOT NULL THEN btrim(sourceid)
            ELSE encode(hash_sourceid, 'hex') END AS source_id,
       MIN(joid)            AS entity_id,
       COUNT(DISTINCT joid) AS n_entity_ids
FROM raw.jocojococlient
WHERE sourceid IS NOT NULL OR hash_sourceid IS NOT NULL
GROUP BY 1, 2;

CREATE INDEX ON semantic.person_xwalk (source, source_id);
ANALYZE semantic.person_xwalk;

ALTER TABLE semantic.person_xwalk OWNER TO jail_mh2;
