\pset pager off

\echo '=== A. Rows, link rate, people, date range per table ==='
SELECT 'jcmhc_services' AS tbl, count(*) AS rows, count(entity_id) AS linked, count(DISTINCT entity_id) AS people, min(svc_date)::date AS first, max(svc_date)::date AS last FROM semantic.jcmhc_services
UNION ALL SELECT 'jcmhc_calls',      count(*), count(entity_id), count(DISTINCT entity_id), min(call_date)::date,      max(call_date)::date      FROM semantic.jcmhc_calls
UNION ALL SELECT 'jcmhc_diagnoses',  count(*), count(entity_id), count(DISTINCT entity_id), min(dx_date)::date,        max(dx_date)::date        FROM semantic.jcmhc_diagnoses
UNION ALL SELECT 'ambulance_runs',   count(*), count(entity_id), count(DISTINCT entity_id), min(incident_ts)::date,    max(incident_ts)::date    FROM semantic.ambulance_runs
UNION ALL SELECT 'lsir',             count(*), count(entity_id), count(DISTINCT entity_id), min(event_date)::date,     max(event_date)::date     FROM semantic.lsir
UNION ALL SELECT 'pretrial',         count(*), count(entity_id), count(DISTINCT entity_id), min(create_date)::date,    max(create_date)::date    FROM semantic.pretrial
UNION ALL SELECT 'pd_arrests',       count(*), count(entity_id), count(DISTINCT entity_id), min(date_arr)::date,       max(date_arr)::date       FROM semantic.pd_arrests
UNION ALL SELECT 'health_dept',      count(*), count(entity_id), count(DISTINCT entity_id), min(encounter_date)::date, max(encounter_date)::date FROM semantic.health_dept
UNION ALL SELECT 'kdoc_status',      count(*), count(entity_id), count(DISTINCT entity_id), min(startdate)::date,      max(startdate)::date      FROM semantic.kdoc_status
UNION ALL SELECT 'outreach_cases',   count(*), count(entity_id), count(DISTINCT entity_id), min(book_date)::date,      max(book_date)::date      FROM semantic.outreach_cases
UNION ALL SELECT 'outreach_attempts',count(*), count(entity_id), count(DISTINCT entity_id), min(attempt_date)::date,   max(attempt_date)::date   FROM semantic.outreach_attempts;

\echo '=== B. Mental health rows whose patient id maps to several people ==='
SELECT 'services' AS tbl, sum((n_entity_ids > 1)::int) AS ambiguous_rows, count(*) AS rows FROM semantic.jcmhc_services
UNION ALL SELECT 'calls',     sum((n_entity_ids > 1)::int), count(*) FROM semantic.jcmhc_calls
UNION ALL SELECT 'diagnoses', sum((n_entity_ids > 1)::int), count(*) FROM semantic.jcmhc_diagnoses;

\echo '=== C. Ambulance: did the two copies of each incident agree? ==='
SELECT sum((n_source_rows <> 2)::int)    AS incidents_not_2_rows,
       sum((n_distinct_dates > 1)::int)   AS date_conflicts,
       sum((n_distinct_primary > 1)::int) AS impression_conflicts
FROM semantic.ambulance_runs;

\echo '=== D. LSI-R: case found, date coverage ==='
SELECT count(*) AS assessments,
       sum(case_found::int)                  AS case_found,
       sum((assessment_date IS NULL)::int)   AS no_assessment_date,
       sum((event_date IS NULL)::int)        AS no_date_at_all,
       sum((assessment_date IS NOT NULL AND created_date IS NOT NULL
            AND assessment_date <> created_date)::int) AS assessment_vs_created_differ
FROM semantic.lsir;

\echo '=== E. Pretrial and outreach: matched to a booking ==='
SELECT 'pretrial' AS tbl, count(*) AS rows, sum(booking_found::int) AS booking_found FROM semantic.pretrial
UNION ALL SELECT 'outreach_cases', count(*), sum(booking_found::int) FROM semantic.outreach_cases;

\echo '=== F. Crosswalk resolution by source ==='
SELECT source, resolution, count(*) AS source_ids
FROM semantic.person_xwalk
WHERE n_entity_ids > 1
GROUP BY 1, 2 ORDER BY 1, 2;

\echo '=== G. Rows not linked because the source id is ambiguous ==='
SELECT 'services' AS tbl, sum((resolution = 'ambiguous_excluded')::int) AS ambiguous_rows,
       sum((entity_id IS NULL)::int) AS unlinked_rows, count(*) AS rows FROM semantic.jcmhc_services
UNION ALL SELECT 'calls',     sum((resolution = 'ambiguous_excluded')::int), sum((entity_id IS NULL)::int), count(*) FROM semantic.jcmhc_calls
UNION ALL SELECT 'diagnoses', sum((resolution = 'ambiguous_excluded')::int), sum((entity_id IS NULL)::int), count(*) FROM semantic.jcmhc_diagnoses;
