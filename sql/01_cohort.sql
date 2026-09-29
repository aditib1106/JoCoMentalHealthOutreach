-- 01_cohort.sql
-- Builds the cohort: the people JCMHC could contact on each monthly prediction date.
--
-- Prediction dates : 1st of every month, 2014-01-01 to 2018-06-01. The last date is
--                    the latest one with a full 12-month label window (data ends
--                    2019-06-30).
-- Cohort           : one row per (entity_id, as_of_date) for people who
--                      * were released from jail in the month before as_of_date,
--                      * were 18 or older at release,
--                      * are not in jail on as_of_date, and
--                      * have at least one JCMHC service, diagnosis or crisis call
--                        dated before as_of_date.
--
-- Inputs : semantic.bookings (one row per jail booking, keyed by person entity_id)
--          semantic.jcmhc_services, semantic.jcmhc_diagnoses, semantic.jcmhc_calls
-- Output : temp tables as_of_dates, cohort
--
-- Run all steps in one session:
--   psql -d johnson_county_ddj_jail_mh2 -f sql/01_cohort.sql -f sql/02_label.sql -f sql/03_baselines.sql

DROP TABLE IF EXISTS pg_temp.as_of_dates;
CREATE TEMP TABLE as_of_dates AS
SELECT d::date AS as_of_date
FROM generate_series('2014-01-01'::date, '2018-06-01'::date, interval '1 month') AS d;

DROP TABLE IF EXISTS pg_temp.cohort;
CREATE TEMP TABLE cohort AS
SELECT DISTINCT a.as_of_date, b.entity_id
FROM as_of_dates a
JOIN semantic.bookings b
  ON b.release_date >= a.as_of_date - interval '1 month'
 AND b.release_date <  a.as_of_date
WHERE b.entity_id IS NOT NULL
  AND extract(year FROM b.release_date) - b.birth_year >= 18
  -- not in jail on as_of_date
  AND NOT EXISTS (
        SELECT 1
        FROM semantic.bookings c
        WHERE c.entity_id = b.entity_id
          AND c.booking_date < a.as_of_date
          AND (c.release_date >= a.as_of_date OR c.release_date IS NULL))
  -- mental-health history, using only records dated before as_of_date
  AND (   EXISTS (SELECT 1 FROM semantic.jcmhc_services s
                  WHERE s.entity_id = b.entity_id AND s.svc_date < a.as_of_date)
       OR EXISTS (SELECT 1 FROM semantic.jcmhc_diagnoses d
                  WHERE d.entity_id = b.entity_id AND d.dx_date < a.as_of_date)
       OR EXISTS (SELECT 1 FROM semantic.jcmhc_calls k
                  WHERE k.entity_id = b.entity_id AND k.call_date < a.as_of_date));

CREATE INDEX ON cohort (entity_id, as_of_date);
ANALYZE cohort;

-- Summary
SELECT count(DISTINCT as_of_date)             AS n_as_of_dates,
       count(*)                               AS cohort_rows,
       count(DISTINCT entity_id)              AS people,
       round(count(*)::numeric / count(DISTINCT as_of_date)) AS avg_per_month
FROM cohort;
