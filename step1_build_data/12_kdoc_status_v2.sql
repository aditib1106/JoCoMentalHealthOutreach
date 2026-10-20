\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

-- =============================================================================
-- State corrections status v2 (Jail MH 2, branch jail-mh2-fixes)
-- 1 KDOC source id had an ambiguous link in Update 1; v2 keeps those rows
-- and flags them via check_linkage. Data ends April 2018.
-- =============================================================================

CREATE TEMP TABLE tmp AS
SELECT urno, encode(hash_docnum, 'hex') AS docnum_hex,
       btrim(status) AS status, startdate, termdate, seq,
       btrim(risklevel) AS risklevel, btrim(warrant) AS warrant, warrantdt,
       btrim(unitname) AS unitname
FROM raw.jocokdocstatus;

DROP TABLE IF EXISTS semantic_v2.kdoc_status;
CREATE TABLE semantic_v2.kdoc_status AS
SELECT x.entity_id,
       x.check_linkage,
       k.*
FROM tmp k
LEFT JOIN semantic_v2.person_xwalk x
       ON x.source    = 'jocoKDOCDemographics.DOCNum'
      AND x.source_id = k.docnum_hex;

CREATE INDEX ON semantic_v2.kdoc_status (entity_id, startdate);
ANALYZE semantic_v2.kdoc_status;
ALTER TABLE semantic_v2.kdoc_status OWNER TO jail_mh2;
