# Project Update 1: formulation and baselines (Team Jail MH 2)

Which 100 people, flagged for mental health need in jail but not in care, should the Johnson County
Mental Health Center (JCMHC) reach each month? This folder computes the numbers on our Update 1
slides: cohort size, base rate (the prior) and precision/recall at 100 for two common-sense baselines.

## Files
- `update1_baselines.sql`: the three ranking dates on slide 4 (1 Apr, 1 May, 1 Jun 2018). About 3–5 min.
- `update1_monthly_average.sql`: same cohort and baselines for every month Jan 2017 – Jun 2018,
  averaged (slide 4, last row). About 15–25 min.
- `compare_windows.sh`: sensitivity checks on slide 5 (outcome window 3/6/9/12 months; release
  look-back 12 months/2/3 years), one change at a time. About 25–30 min.

All three read only the `semantic` schema and print aggregates only. They create temporary tables
and never modify the database.

## How to reproduce
Requirements: class server access, `psql`, and your database password in `~/.pgpass`.

1. **The `semantic` schema must exist** in `johnson_county_ddj_jail_mh2`. It is already built there.
   To rebuild it from the county tables, see `sql/semantic/README.md` (about 10 min).
2. From the repository root:
   ```bash
   psql -h database.mlpolicylab.dssg.io -U <andrew id> -d johnson_county_ddj_jail_mh2 -f sql/update1/update1_baselines.sql
   psql -h database.mlpolicylab.dssg.io -U <andrew id> -d johnson_county_ddj_jail_mh2 -f sql/update1/update1_monthly_average.sql
   PGUSER=<andrew id> bash sql/update1/compare_windows.sh
   ```
3. Self-checks: in the output of `update1_baselines.sql`, section 3's `list_size_check` must be 100.0
   on every row, and section 1 should show cohorts of 4,392 / 4,462 / 4,526.

## Definitions (parameters at the top of each SQL file)
- **Ranking date:** first day of the month.
- **Cohort:** released from the Johnson County jail in the past 12 months; not in jail on the
  ranking date; flagged for mental health need by a jail-side assessment (positive booking screen,
  pretrial mental health flag, or LSI-R need items under the county's rule: 1 on items 37–50 or 0 on
  39/40); no JCMHC service in the 90 days before.
- **Data lag:** only records dated at least 7 days before the ranking date are used as inputs
  (jail bookings and releases as of the ranking date).
- **Outcome:** a jail booking for a new arrest (booking type VIEW, WARR or BW: on-view arrest,
  arrest warrant, bench warrant) within 12 months after the ranking date. The SQL also reports
  "any booking" and "booking with a positive screen" for comparison.
- **Prior:** a random 100 from the cohort; its expected precision equals the base rate.
- **B1:** the 100 with the highest booking-screen score at their most recent screened booking.
- **B2:** the 100 with the highest latest LSI-R total score; people without one next, by pretrial
  risk level.
- **Ties:** broken by most recent release; any remaining ties share the last places equally, so the
  reported precision is the exact expected value over all tie-breaks.
- **Precision at 100:** share of the 100 listed who have the outcome. **Recall at 100:** share of all
  cohort members with the outcome who are on the list.
- **Ambiguous ids:** records whose id the county matched to more than one person are not linked
  (see `sql/semantic/README.md`).

## Why these dates and windows
- Jail booking data are complete through June 2019, so 1 Jun 2018 is the latest ranking date with a
  full 12-month outcome window. The jail screen covers about 89–95% of bookings from 2017 on.
- `compare_windows.sh` shows why 12 months was chosen for both the outcome window and the look-back.

## Results (new-arrest outcome)
| Ranking date | Cohort | Base rate | B1 | B2 |
|---|---|---|---|---|
| 1 Apr 2018 | 4,392 | 25.5% | 29% | 30% |
| 1 May 2018 | 4,462 | 25.8% | 23% | 28% |
| 1 Jun 2018 | 4,526 | 25.6% | 24% | 27% |
| 18-month average (Jan 2017 – Jun 2018) | ~3,790 | 26.9% | 29.4% | 31.7% |
