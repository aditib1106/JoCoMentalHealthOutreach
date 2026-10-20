 \set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

-- =============================================================================
-- Person crosswalk v2 (Jail MH 2, branch jail-mh2-fixes)
--
-- Change from v1 (semantic.person_xwalk):
--   v1 set entity_id = NULL whenever the county matched a source id to more
--   than one joid, which silently dropped those people from every event table
--   that joined on entity_id. For JCMHC services alone that was 2,820 patient
--   ids and roughly 12% of all service rows. The instructor flagged this
--   ("you're outsourcing deaths to Claude") and asked us to keep every link
--   and flag the ones that need review instead of dropping them.
--
-- What this file does:
--   Rebuilds the crosswalk in schema semantic_v2 with every (source, source_id)
--   row preserved. For each source id we keep MIN(joid) as entity_id, record
--   how many joids were seen (n_entity_ids), and set check_linkage = TRUE for
--   any id that mapped to more than one person. Downstream event tables keep
--   every row and inherit this flag so analyses can filter, split, or run
--   sensitivity on linked groups.
--
-- MIN(joid) is still arbitrary when n_entity_ids > 1; the flag makes that
-- visible instead of hiding it. If the team later prefers a different rule
-- (duplicate the event per candidate, split into two people, etc.) that
-- happens in a sensitivity run, not here.
-- =============================================================================

DROP TABLE IF EXISTS semantic_v2.person_xwalk;

CREATE TABLE semantic_v2.person_xwalk AS
SELECT
    source,
    -- sourceid is text for JIMS, JCMHC, JCDHE, PD. hash_sourceid is bytea for
    -- MED-ACT, AIMS, KDOC. Exactly one is populated per row (verified during
    -- Phase 1 of semantic). We store the text form as source_id, trimming
    -- JIMS leading-zero padding on the way in so downstream joins can
    -- compare without worrying about padding again. For hashed systems we
    -- store the bytea as lowercase hex, matching how cleaned.* tables
    -- already carry the same values.
    CASE
        WHEN sourceid IS NOT NULL THEN btrim(sourceid)
        ELSE encode(hash_sourceid, 'hex')
    END                                           AS source_id,
    MIN(joid)                                     AS entity_id,
    COUNT(DISTINCT joid)                          AS n_entity_ids,
    -- check_linkage flags source ids that the county matched to more than
    -- one person. Keep the row; let downstream analyses decide what to do.
    (COUNT(DISTINCT joid) > 1)                    AS check_linkage
FROM raw.jocojococlient
WHERE sourceid IS NOT NULL OR hash_sourceid IS NOT NULL
GROUP BY 1, 2;

CREATE INDEX ON semantic_v2.person_xwalk (source, source_id);
ANALYZE semantic_v2.person_xwalk;
ALTER TABLE semantic_v2.person_xwalk OWNER TO jail_mh2;
