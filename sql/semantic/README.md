# semantic schema: clean, person-linked tables

Built from the county's `raw` and `cleaned` foreign tables. Every table has an integer
`entity_id` (the county's `joid`), an event date, and no duplicate rows.
Analyses (e.g. `sql/update1/`) read only from this schema.

## Rebuild order
00_schema, 01_person_xwalk, 02_bookings, 03_booking_types, 04 … 13,
then check_phase1.sql and check_phase2.sql.

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
- Some source ids map to several people in the county crosswalk. Those ids are **not linked to
  anyone** (`entity_id` NULL, `resolution = 'ambiguous_excluded'`): 2,820 mental health ids
  (about 12% of mental health service rows), 128 police ids, 278 public-booking ids, 1 state
  corrections id. We do not guess: a wrong link could make someone look already in care and
  remove them from outreach. `n_entity_ids` keeps how many people each id was matched to.
- `cleaned.jocojcmhcservices` = raw with exact duplicate rows removed and service names
  uppercased (verified row for row: 4,895,853 raw rows, 4,609,027 distinct = cleaned).
- Health department data comes from `raw` because the cleaned table is exactly doubled
  (verified: 1,801,990 cleaned vs 900,995 raw).
- LSI-R: about 15% of assessments have no usable date. Use the later of
  assessment_date and created_date as the knowledge date (the created_date decoding was
  verified: 99.4% on or after the assessment date).
- Mental health records before about 2000 are sparse. State corrections data end April 2018.
- Outreach tables are for evaluation only, never model features. Some attempt dates are
  invalid; filter to 2016-11-01 to 2019-07-03.
- The source tables are foreign tables with no planner statistics. For ad-hoc queries
  against raw/cleaned, run `SET enable_nestloop = off;` first.
