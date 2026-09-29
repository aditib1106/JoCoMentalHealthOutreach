-- Project Update 1: cohort, base rate and baseline precision at k for every month Jan 2017 - Jun 2018, averaged.
\set ON_ERROR_STOP on
\pset pager off
SET enable_nestloop = off;

-- ================= PARAMETERS (change only here) =================
-- How far back a release may be for someone to be eligible [DECIDE]
\set lookback '12 months'
-- Outcome window after the ranking date
\set label_window '12 months'
-- Data lag in days: only records dated at least this many days before the ranking date are used
\set lag 7
-- "Actively engaged" = any JCMHC service in this many days before (ranking date - lag)
\set engaged_days 90
-- List size (JCMHC capacity per month)
\set k 100
-- LSI-R need rule [DECIDE]: joco = county rule (items 37-50, or 0 on 39/40); emotional = items 46-50
\set lsir_rule joco
-- Johnson County residents only? [DECIDE] true = must be flagged resident at some earlier booking
\set resident_only false
-- =================================================================

DROP TABLE IF EXISTS u1_dates, u1_released, u1_flagged, u1_cohort, u1_labels, u1_scores, u1_keys;

CREATE TEMP TABLE u1_dates AS
SELECT generate_series('2017-01-01'::date, '2018-06-01'::date, '1 month')::date AS as_of;

-- 1. Released from jail within the look-back window and not in jail on the ranking date
CREATE TEMP TABLE u1_released AS
SELECT d.as_of, b.entity_id,
       max(b.release_date) FILTER (WHERE b.release_date < d.as_of) AS last_release
FROM u1_dates d
JOIN semantic.bookings b ON b.booking_date < d.as_of AND b.entity_id IS NOT NULL
GROUP BY 1, 2
HAVING max(b.release_date) FILTER (WHERE b.release_date < d.as_of) >= d.as_of - :'lookback'::interval
   AND NOT bool_or(b.release_date IS NULL OR b.release_date >= d.as_of)
   AND (NOT :resident_only OR coalesce(bool_or(b.joco_resident), false));

-- 2. Flagged for mental health need by a jail-side assessment known by (date - lag)
CREATE TEMP TABLE u1_flagged AS
SELECT r.* FROM u1_released r
WHERE EXISTS (SELECT 1 FROM semantic.bookings b
              WHERE b.entity_id = r.entity_id AND b.booking_date < r.as_of - :lag AND b.bjmhs_referred = 1)
   OR EXISTS (SELECT 1 FROM semantic.pretrial p
              WHERE p.entity_id = r.entity_id AND p.create_date < r.as_of - :lag AND p.assessment_mh_flag = 1)
   OR EXISTS (SELECT 1 FROM semantic.lsir l
              WHERE l.entity_id = r.entity_id
                AND GREATEST(l.assessment_date, l.created_date) < r.as_of - :lag
                AND CASE WHEN :'lsir_rule' = 'joco'
                         THEN (1 IN (l.ans_37,l.ans_38,l.ans_39,l.ans_40,l.ans_41,l.ans_42,l.ans_43,
                                     l.ans_44,l.ans_45,l.ans_46,l.ans_47,l.ans_48,l.ans_49,l.ans_50)
                               OR l.ans_39 = 0 OR l.ans_40 = 0)
                         ELSE (1 IN (l.ans_46,l.ans_47,l.ans_48,l.ans_49,l.ans_50)) END);

-- 3. Not actively engaged: no JCMHC service in the engaged_days before (date - lag)
CREATE TEMP TABLE u1_cohort AS
SELECT f.* FROM u1_flagged f
WHERE NOT EXISTS (SELECT 1 FROM semantic.jcmhc_services s
                  WHERE s.entity_id = f.entity_id
                    AND s.svc_date >= f.as_of - :lag - :engaged_days
                    AND s.svc_date <  f.as_of - :lag);

-- 4. Outcomes in the label window (three candidate outcomes; the team reports one) [DECIDE which]
CREATE TEMP TABLE u1_labels AS
SELECT c.as_of, c.entity_id, c.last_release,
  EXISTS (SELECT 1 FROM semantic.bookings b
          WHERE b.entity_id = c.entity_id
            AND b.booking_date >= c.as_of AND b.booking_date < c.as_of + :'label_window'::interval) AS y_any,
  EXISTS (SELECT 1 FROM semantic.bookings b JOIN semantic.booking_types t USING (booking_no)
          WHERE b.entity_id = c.entity_id
            AND b.booking_date >= c.as_of AND b.booking_date < c.as_of + :'label_window'::interval
            AND t.book_types && ARRAY['VIEW','WARR','BW']) AS y_arrest,
  EXISTS (SELECT 1 FROM semantic.bookings b
          WHERE b.entity_id = c.entity_id AND b.bjmhs_referred = 1
            AND b.booking_date >= c.as_of AND b.booking_date < c.as_of + :'label_window'::interval) AS y_mh
FROM u1_cohort c;

-- 5. Baseline inputs, each known by (date - lag)
CREATE TEMP TABLE u1_scores AS
SELECT l.*,
  (SELECT b.mhs_total FROM semantic.bookings b
    WHERE b.entity_id = l.entity_id AND b.booking_date < l.as_of - :lag AND b.mhs_total IS NOT NULL
    ORDER BY b.booking_date DESC LIMIT 1) AS screen_score,
  (SELECT COALESCE(x.total_score, x.score) FROM semantic.lsir x
    WHERE x.entity_id = l.entity_id
      AND GREATEST(x.assessment_date, x.created_date) < l.as_of - :lag
      AND COALESCE(x.total_score, x.score) IS NOT NULL
    ORDER BY GREATEST(x.assessment_date, x.created_date) DESC LIMIT 1) AS lsir_score,
  (SELECT p.risk_level_int FROM semantic.pretrial p
    WHERE p.entity_id = l.entity_id AND p.create_date < l.as_of - :lag AND p.risk_level_int IS NOT NULL
    ORDER BY p.create_date DESC LIMIT 1) AS pretrial_risk
FROM u1_labels l;

-- 6. Ranking keys. Higher key = earlier in the list. Ties on every key share the remaining places.
--    B1: highest screen score at the most recent screened booking; ties -> most recent release.
--    B2: highest latest LSI-R total score; people without one next, by highest pretrial risk level;
--        ties -> most recent release.
CREATE TEMP TABLE u1_keys AS
SELECT 'B1 screen score' AS baseline, as_of,
       screen_score::numeric AS k1, NULL::numeric AS k2, last_release AS k3, y_any, y_arrest, y_mh
FROM u1_scores
UNION ALL
SELECT 'B2 LSI-R, then pretrial risk', as_of,
       lsir_score::numeric, pretrial_risk::numeric, last_release, y_any, y_arrest, y_mh
FROM u1_scores;

\echo '=== 1. Cohort funnel and base rates (base rate = expected precision of a random 100 = the prior) ==='
SELECT r.as_of,
       (SELECT count(*) FROM u1_released x WHERE x.as_of = r.as_of) AS released_not_in_jail,
       (SELECT count(*) FROM u1_flagged  x WHERE x.as_of = r.as_of) AS with_jail_mh_flag,
       count(*)                                                     AS cohort,
       sum(y_any::int)    AS n_any,    round(100.0 * avg(y_any::int), 1)    AS base_rate_any,
       sum(y_arrest::int) AS n_arrest, round(100.0 * avg(y_arrest::int), 1) AS base_rate_new_arrest,
       sum(y_mh::int)     AS n_mh,     round(100.0 * avg(y_mh::int), 1)     AS base_rate_mh_booking
FROM u1_labels r GROUP BY r.as_of ORDER BY r.as_of;

\echo '=== 2. How many cohort members have each baseline input ==='
SELECT as_of, count(*) AS cohort,
       count(screen_score)  AS with_screen_score,
       count(lsir_score)    AS with_lsir_score,
       count(pretrial_risk) AS with_pretrial_risk,
       count(*) FILTER (WHERE lsir_score IS NULL AND pretrial_risk IS NULL) AS with_neither
FROM u1_scores GROUP BY as_of ORDER BY as_of;

\echo '=== 3. Baseline precision and recall at k (exact expected value over tie-breaks) ==='
WITH g AS (
  SELECT baseline, as_of, k1, k2, k3, count(*) AS m,
         sum(y_any::int) AS p_any, sum(y_arrest::int) AS p_arrest, sum(y_mh::int) AS p_mh
  FROM u1_keys GROUP BY baseline, as_of, k1, k2, k3),
c AS (
  SELECT g.*, coalesce(sum(m) OVER (PARTITION BY baseline, as_of
                ORDER BY k1 DESC NULLS LAST, k2 DESC NULLS LAST, k3 DESC NULLS LAST
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0) AS before
  FROM g),
w AS (
  SELECT c.*, GREATEST(0, LEAST(m, :k - before))::numeric / m AS incl FROM c),
tot AS (
  SELECT as_of, sum(y_any::int) AS t_any, sum(y_arrest::int) AS t_arrest, sum(y_mh::int) AS t_mh
  FROM u1_labels GROUP BY as_of)
SELECT w.baseline, w.as_of,
       round(sum(w.incl * w.m), 1)                                  AS list_size_check,
       round(100 * sum(w.incl * w.p_any)    / :k, 1)                AS prec_any,
       round(100 * sum(w.incl * w.p_arrest) / :k, 1)                AS prec_new_arrest,
       round(100 * sum(w.incl * w.p_mh)     / :k, 1)                AS prec_mh_booking,
       round(100 * sum(w.incl * w.p_any)    / max(t.t_any), 1)      AS recall_any,
       round(100 * sum(w.incl * w.p_arrest) / max(t.t_arrest), 1)   AS recall_new_arrest,
       round(100 * sum(w.incl * w.p_mh)     / max(t.t_mh), 1)       AS recall_mh_booking
FROM w JOIN tot t USING (as_of)
GROUP BY w.baseline, w.as_of ORDER BY w.baseline, w.as_of;

\echo '=== 4. Averages over all monthly ranking dates (new-arrest outcome) ==='
DROP TABLE IF EXISTS u1_prec;
CREATE TEMP TABLE u1_prec AS
WITH g AS (
  SELECT baseline, as_of, k1, k2, k3, count(*) AS m, sum(y_arrest::int) AS p_arrest
  FROM u1_keys GROUP BY baseline, as_of, k1, k2, k3),
c AS (
  SELECT g.*, coalesce(sum(m) OVER (PARTITION BY baseline, as_of
                ORDER BY k1 DESC NULLS LAST, k2 DESC NULLS LAST, k3 DESC NULLS LAST
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0) AS before
  FROM g),
w AS (SELECT c.*, GREATEST(0, LEAST(m, :k - before))::numeric / m AS incl FROM c)
SELECT baseline, as_of, 100 * sum(incl * p_arrest) / :k AS prec
FROM w GROUP BY baseline, as_of;

SELECT 'Prior (base rate)' AS rule, count(*) AS n_dates,
       round(100 * avg(br), 1) AS avg_precision, round(100 * min(br), 1) AS lowest, round(100 * max(br), 1) AS highest,
       round(avg(n)) AS avg_cohort
FROM (SELECT as_of, avg(y_arrest::int) AS br, count(*) AS n FROM u1_labels GROUP BY as_of) x
UNION ALL
SELECT baseline, count(*), round(avg(prec), 1), round(min(prec), 1), round(max(prec), 1), NULL
FROM u1_prec GROUP BY baseline
ORDER BY 1;

