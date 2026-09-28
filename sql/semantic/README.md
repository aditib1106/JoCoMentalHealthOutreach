# semantic schema: clean, person-linked tables

Built from the county's `raw` and `cleaned` foreign tables. Every table has an integer
`entity_id` (the county's `joid`), an event date, and no duplicate rows.

## Rebuild order
00_schema, 01_person_xwalk, 02_bookings, 02b_resolve_xwalk, 03_booking_types,
04 … 13, then check_phase1.sql and check_phase2.sql.

Run each with:
psql -h database.mlpolicylab.dssg.io -U <you> -d johnson_county_ddj_jail_mh2 -f sql/semantic/<file>.sql

## Tables
| Table | One row per | Date column |
|---|---|---|
| person_xwalk | source system id | (none) |
| bookings | jail booking | booking_date, release_date |
| booking_types | jail booking | (join to bookings) |
| jcmhc_services | mental health service | svc_date |
| jcmhc_calls | crisis line call | call_date |
| jcmhc_diagnoses | diagnosis | dx_date |
| ambulance_runs | ambulance incident | incident_ts |
| lsir | LSI-R assessment | event_date (see notes) |
| pretrial | pretrial assessment | create_date |
| pd_arrests | police arrest | date_arr |
| health_dept | health dept encounter | encounter_date |
| kdoc_status | state corrections status row | startdate, termdate |
| outreach_cases / outreach_attempts | outreach case / attempt | book_date / attempt_date |

## Things to know
- The source jail table stores every booking twice; `bookings` has one row each.
- Jail ids must be zero-padded to 9 characters to match the crosswalk (handled here).
- Some source ids map to several people. `resolution` says how each was handled:
  unique, jail_match (only one candidate has jail bookings), ambiguous_no_jail,
  ambiguous_multi_jail (about 1% of mental health rows; decide at the feature stage).
- LSI-R: about 15% of assessments have no usable date. Use the later of
  assessment_date and created_date as the knowledge date.
- Mental health records before about 2000 are sparse. State corrections data end April 2018.
- Outreach tables are for evaluation only, never model features. Some attempt dates are
  invalid; filter to 2016-11-01 to 2019-07-03.
- The source tables are foreign tables with no planner statistics. For ad-hoc queries
  against raw/cleaned, run `SET enable_nestloop = off;` first.
