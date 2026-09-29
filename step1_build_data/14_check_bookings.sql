\pset pager off

\echo '=== A. Bookings: quality checks ==='
SELECT count(*)                                AS bookings,
       count(entity_id)                        AS linked_to_person,
       count(DISTINCT entity_id)               AS people,
       sum((n_source_rows <> 2)::int)          AS bookings_not_exactly_2_rows,
       sum((n_mni > 1)::int)                   AS bookings_with_2_jail_ids,
       sum(release_conflict::int)              AS release_date_conflicts,
       sum((release_date < booking_date)::int) AS release_before_booking,
       sum((release_date IS NULL)::int)        AS no_release_date,
       min(booking_date), max(booking_date)
FROM semantic.bookings;

\echo '=== B. Mental health screen coverage by year ==='
SELECT extract(year FROM booking_date) AS yr,
       count(*) AS bookings,
       round(100.0 * avg((bjmhs_referred IS NOT NULL)::int), 1) AS pct_screened
FROM semantic.bookings
WHERE booking_date >= '2014-01-01'
GROUP BY 1 ORDER BY 1;

\echo '=== C. Bookings per booking type ==='
SELECT t AS book_type, count(*) AS bookings
FROM semantic.booking_types, unnest(book_types) t
GROUP BY 1 ORDER BY 2 DESC;

\echo '=== D. Charges vs bookings ==='
SELECT count(*)                         AS bookings_with_charges,
       sum((b.booking_no IS NULL)::int) AS charge_bookings_missing_from_bookings,
       sum((t.book_types IS NULL)::int) AS bookings_with_no_type
FROM semantic.booking_types t
LEFT JOIN semantic.bookings b USING (booking_no);
