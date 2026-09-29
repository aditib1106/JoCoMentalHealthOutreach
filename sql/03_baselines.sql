-- 03_baselines.sql
-- Evaluates the prior and two commonsense baselines.
--
-- Each month, every rule ranks the cohort and flags the top 100 people (JCMHC's
-- monthly outreach capacity). Ties are broken randomly but reproducibly.
--
--   Prior       : random selection; its expected precision equals the base rate.
--   Baseline 1  : most jail bookings in the 3 years before as_of_date.
--   Baseline 2  : shortest time between the person's most recent booking and the
--                 release before it (people who return quickly rank first).
--                 People with no earlier release rank last.
--
-- Metrics : precision@100 = share of the 100 flagged people who are rebooked
--           recall@100    = share of all rebooked people who were flagged
--
-- Input  : temp table labels (02_label.sql), semantic.bookings
-- Output : temp tables scores, monthly_metrics; overall and yearly results

DROP TABLE IF EXISTS pg_temp.scores;
CREATE TEMP TABLE scores AS
SELECT
    l.as_of_date,
    l.entity_id,
    l.label,
    (SELECT count(*)
     FROM semantic.bookings p
     WHERE p.entity_id = l.entity_id
       AND p.booking_date >= l.as_of_date - interval '3 years'
       AND p.booking_date <  l.as_of_date)                    AS prior_bookings_3y,
    (SELECT last_b.booking_date - max(r.release_date)
     FROM (SELECT max(b.booking_date) AS booking_date
           FROM semantic.bookings b
           WHERE b.entity_id = l.entity_id
             AND b.booking_date < l.as_of_date) last_b
     JOIN semantic.bookings r
       ON r.entity_id = l.entity_id
      AND r.booking_date <  last_b.booking_date
      AND r.release_date <= last_b.booking_date
     GROUP BY last_b.booking_date)                            AS days_to_rebook,
    md5(l.entity_id::text || l.as_of_date::text)              AS tiebreak
FROM labels l;

DROP TABLE IF EXISTS pg_temp.monthly_metrics;
CREATE TEMP TABLE monthly_metrics AS
WITH ranked AS (
    SELECT s.*,
           row_number() OVER (PARTITION BY as_of_date
                              ORDER BY prior_bookings_3y DESC, tiebreak)          AS rank_b1,
           row_number() OVER (PARTITION BY as_of_date
                              ORDER BY days_to_rebook ASC NULLS LAST, tiebreak)   AS rank_b2
    FROM scores s
)
SELECT
    as_of_date,
    count(*)                                          AS cohort_size,
    avg(label::int)                                   AS prior,
    avg(label::int) FILTER (WHERE rank_b1 <= 100)     AS b1_precision,
    avg(label::int) FILTER (WHERE rank_b2 <= 100)     AS b2_precision,
    100.0 / count(*)                                  AS prior_recall,   -- expected recall of a random 100
    sum(label::int) FILTER (WHERE rank_b1 <= 100)::numeric / nullif(sum(label::int), 0) AS b1_recall,
    sum(label::int) FILTER (WHERE rank_b2 <= 100)::numeric / nullif(sum(label::int), 0) AS b2_recall
FROM ranked
GROUP BY as_of_date;

-- Results: average over all prediction dates
SELECT count(*)                          AS n_as_of_dates,
       round(avg(cohort_size))           AS avg_cohort_size,
       round(avg(prior), 3)              AS prior_precision,
       round(avg(b1_precision), 3)       AS b1_precision,
       round(avg(b2_precision), 3)       AS b2_precision,
       round(avg(prior_recall), 3)       AS prior_recall,
       round(avg(b1_recall), 3)          AS b1_recall,
       round(avg(b2_recall), 3)          AS b2_recall
FROM monthly_metrics;

-- Results by year
SELECT extract(year FROM as_of_date)::int AS year,
       round(avg(cohort_size))            AS avg_cohort_size,
       round(avg(prior), 3)               AS prior_precision,
       round(avg(b1_precision), 3)        AS b1_precision,
       round(avg(b2_precision), 3)        AS b2_precision,
       round(avg(b1_recall), 3)           AS b1_recall,
       round(avg(b2_recall), 3)           AS b2_recall
FROM monthly_metrics
GROUP BY 1
ORDER BY 1;
