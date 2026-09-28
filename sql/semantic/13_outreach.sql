\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

CREATE TEMP TABLE tmp_cases AS
SELECT encode(hash_mnh_no_0, 'hex') AS booking_no,
       btrim(mni_13) AS mni_text,
       CASE WHEN btrim(book_date_12)  ~ '^\d{2}/\d{2}/\d{4}$' THEN to_date(btrim(book_date_12),  'MM/DD/YYYY') END AS book_date,
       CASE WHEN btrim(rel_date_14)   ~ '^\d{2}/\d{2}/\d{4}$' THEN to_date(btrim(rel_date_14),   'MM/DD/YYYY') END AS release_date,
       CASE WHEN btrim(connect_dt_28) ~ '^\d{2}/\d{2}/\d{4}$' THEN to_date(btrim(connect_dt_28), 'MM/DD/YYYY') END AS connect_date,
       NULLIF(btrim(jcmhc_id_16), '')    AS jcmhc_id,
       NULLIF(btrim(mhc_status_17), '')  AS mhc_status,
       NULLIF(btrim(mcrt_assert_18), '') AS mcrt_assert,
       NULLIF(btrim(final_dispo_33), '') AS final_dispo
FROM raw.jocojimsmnhdata;

DROP TABLE IF EXISTS semantic.outreach_cases;
CREATE TABLE semantic.outreach_cases AS
SELECT b.entity_id, (b.booking_no IS NOT NULL) AS booking_found, o.*
FROM tmp_cases o
LEFT JOIN semantic.bookings b USING (booking_no);

CREATE INDEX ON semantic.outreach_cases (entity_id, release_date);
ANALYZE semantic.outreach_cases;
ALTER TABLE semantic.outreach_cases OWNER TO jail_mh2;

CREATE TEMP TABLE tmp_attempts AS
SELECT encode(hash_mnh_no_0, 'hex') AS booking_no,
       CASE WHEN btrim(attempt_date_24) ~ '^\d{2}/\d{2}/\d{4}$' THEN to_date(btrim(attempt_date_24), 'MM/DD/YYYY') END AS attempt_date,
       NULLIF(btrim(contact_type_26), '') AS contact_type,
       NULLIF(btrim(outcome_27), '')      AS outcome
FROM raw.jocojimsmnh_attempts;

DROP TABLE IF EXISTS semantic.outreach_attempts;
CREATE TABLE semantic.outreach_attempts AS
SELECT b.entity_id, a.*
FROM tmp_attempts a
LEFT JOIN semantic.bookings b USING (booking_no);

CREATE INDEX ON semantic.outreach_attempts (entity_id, attempt_date);
ANALYZE semantic.outreach_attempts;
ALTER TABLE semantic.outreach_attempts OWNER TO jail_mh2;
