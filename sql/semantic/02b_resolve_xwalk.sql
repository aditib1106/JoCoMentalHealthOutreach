\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

-- All (source id -> person) pairs, pulled from the foreign crosswalk once
CREATE TEMP TABLE tmp_all AS
SELECT DISTINCT source,
       CASE WHEN sourceid IS NOT NULL THEN btrim(sourceid)
            ELSE encode(hash_sourceid, 'hex') END AS source_id,
       joid
FROM raw.jocojococlient
WHERE sourceid IS NOT NULL OR hash_sourceid IS NOT NULL;

-- Everyone with at least one jail booking
CREATE TEMP TABLE tmp_jail_people AS
SELECT DISTINCT entity_id FROM semantic.bookings WHERE entity_id IS NOT NULL;

-- For each ambiguous source id: how many candidates are in the jail population
CREATE TEMP TABLE tmp_resolved AS
SELECT a.source, a.source_id,
       COUNT(*) FILTER (WHERE j.entity_id IS NOT NULL)    AS n_jail_candidates,
       MIN(a.joid) FILTER (WHERE j.entity_id IS NOT NULL) AS jail_joid
FROM tmp_all a
JOIN semantic.person_xwalk x
  ON x.source = a.source AND x.source_id = a.source_id AND x.n_entity_ids > 1
LEFT JOIN tmp_jail_people j ON j.entity_id = a.joid
GROUP BY 1, 2;

ALTER TABLE semantic.person_xwalk
  ADD COLUMN IF NOT EXISTS n_jail_candidates int,
  ADD COLUMN IF NOT EXISTS resolution text;

UPDATE semantic.person_xwalk
SET resolution = 'unique'
WHERE n_entity_ids = 1;

UPDATE semantic.person_xwalk x
SET n_jail_candidates = r.n_jail_candidates,
    entity_id  = CASE WHEN r.n_jail_candidates = 1 THEN r.jail_joid ELSE x.entity_id END,
    resolution = CASE WHEN r.n_jail_candidates = 1 THEN 'jail_match'
                      WHEN r.n_jail_candidates = 0 THEN 'ambiguous_no_jail'
                      ELSE 'ambiguous_multi_jail' END
FROM tmp_resolved r
WHERE x.source = r.source AND x.source_id = r.source_id;

ANALYZE semantic.person_xwalk;
