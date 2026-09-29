-- 02_label.sql
-- Adds the outcome to each cohort row.
--
-- Label : 1 if the person has any jail booking in the 12 months after as_of_date,
--         otherwise 0. Matching is by person (entity_id), so a booking under a
--         different jail ID for the same person still counts.
--
-- Input  : temp table cohort (01_cohort.sql), semantic.bookings
-- Output : temp table labels

DROP TABLE IF EXISTS pg_temp.labels;
CREATE TEMP TABLE labels AS
SELECT
    c.as_of_date,
    c.entity_id,
    EXISTS (
        SELECT 1
        FROM semantic.bookings f
        WHERE f.entity_id = c.entity_id
          AND f.booking_date >= c.as_of_date
          AND f.booking_date <  c.as_of_date + interval '12 months'
    ) AS label
FROM cohort c;

CREATE INDEX ON labels (entity_id, as_of_date);
ANALYZE labels;

-- Summary: base rate (prior) of the label
SELECT count(*)                       AS cohort_rows,
       sum(label::int)                AS positives,
       round(avg(label::int), 3)      AS base_rate
FROM labels;
