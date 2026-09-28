\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

CREATE TEMP TABLE tmp AS
SELECT urno, encode(hash_docnum, 'hex') AS docnum_hex,
       btrim(status) AS status, startdate, termdate, seq,
       btrim(risklevel) AS risklevel, btrim(warrant) AS warrant, warrantdt,
       btrim(unitname) AS unitname
FROM raw.jocokdocstatus;

DROP TABLE IF EXISTS semantic.kdoc_status;
CREATE TABLE semantic.kdoc_status AS
SELECT x.entity_id, k.*
FROM tmp k
LEFT JOIN semantic.person_xwalk x
       ON x.source = 'jocoKDOCDemographics.DOCNum'
      AND x.source_id = k.docnum_hex;

CREATE INDEX ON semantic.kdoc_status (entity_id, startdate);
ANALYZE semantic.kdoc_status;
ALTER TABLE semantic.kdoc_status OWNER TO jail_mh2;
