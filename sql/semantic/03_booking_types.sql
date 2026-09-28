\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

-- 1. Pull the charges foreign table once (book_type is padded character, so trim it)
CREATE TEMP TABLE tmp_charges AS
SELECT booking_no,
       NULLIF(btrim(book_type), '') AS book_type
FROM cleaned.jocojimsinmatecharges;

-- 2. One row per booking with the full set of booking types on its charges
DROP TABLE IF EXISTS semantic.booking_types;
CREATE TABLE semantic.booking_types AS
SELECT booking_no,
       array_agg(DISTINCT book_type ORDER BY book_type)
           FILTER (WHERE book_type IS NOT NULL) AS book_types,
       COUNT(*)                                 AS n_charges
FROM tmp_charges
GROUP BY booking_no;

CREATE UNIQUE INDEX ON semantic.booking_types (booking_no);
ANALYZE semantic.booking_types;

ALTER TABLE semantic.booking_types OWNER TO jail_mh2;
