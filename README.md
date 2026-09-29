# Jail MH 2: Proactive mental health outreach (Project Update 1)

**Question.** Each month, which 100 people, flagged for mental health need in the Johnson County
jail but not in mental health care, should the Johnson County Mental Health Center (JCMHC) contact?

This branch contains everything needed to reproduce our Update 1 numbers. Run the two steps in order.
(The course's original project description is in `PROJECT_DESCRIPTION.md`.)

## Repository layout (in order of execution)

| Order | Folder / file | What it does | Time |
|---|---|---|---|
| 1 | `step1_build_data/00_schema.sql` … `13_outreach.sql` | Builds clean, person-linked tables in schema `semantic` from the county tables | ~10 min |
| 1 | `step1_build_data/14_check_bookings.sql`, `15_check_other_tables.sql` | Validation checks (aggregates only) | ~1 min |
| 2 | `step2_update1_baselines/1_baselines_three_dates.sql` | Slide 4: cohort, base rate, baselines for 1 Apr, 1 May, 1 Jun 2018 | ~3–5 min |
| 2 | `step2_update1_baselines/2_baselines_18_month_avg.sql` | Slide 4 last row: same, every month Jan 2017 – Jun 2018, averaged | ~15–25 min |
| 2 | `step2_update1_baselines/3_sensitivity_checks.sh` | Slide 5: outcome window 3/6/9/12 months; release look-back 12 months/2/3 years | ~25–30 min |

## How to reproduce

Requirements: class server account, `psql`, database password in `~/.pgpass`. Run from the repository root.

```bash
DB="-h database.mlpolicylab.dssg.io -U <andrew id> -d johnson_county_ddj_jail_mh2"

# Step 1 (optional: the semantic schema is already built in the team database)
for f in step1_build_data/[01][0-9]_*.sql; do psql $DB -f "$f" || break; done

# Step 2
psql $DB -f step2_update1_baselines/1_baselines_three_dates.sql
psql $DB -f step2_update1_baselines/2_baselines_18_month_avg.sql
PGUSER=<andrew id> bash step2_update1_baselines/3_sensitivity_checks.sh
```

Self-checks: in `1_baselines_three_dates.sql`, section 1 shows cohorts of 4,392 / 4,462 / 4,526 and
section 3's `list_size_check` is 100.0 on every row. Nothing writes to the database except step 1
(schema `semantic`); step 2 uses temporary tables only and prints aggregates only.

## Formulation

> Every month, for people released from the Johnson County jail in the past 12 months who are not in
> jail on the 1st, were flagged for mental health need by a jail assessment (booking screen, pretrial
> assessment or LSI-R), and have had no JCMHC service in the past 90 days, identify the 100 people most
> likely to be booked into jail for a new arrest within the next 12 months, so JCMHC can offer them
> proactive outreach before a crisis.

- **Ranking date:** 1st of each month. **List size:** 100 (JCMHC's monthly capacity).
- **Need flag:** positive jail mental health screen, pretrial mental health flag, or LSI-R need under
  the county's rule (1 on items 37–50, or 0 on items 39/40).
- **Outcome:** jail booking for a new arrest (types VIEW, WARR, BW) within 12 months.
- **Data lag:** inputs use only records dated at least 7 days before the ranking date.
- **Prior:** a random 100 from the cohort (expected precision = base rate).
- **B1:** highest jail mental health screen score at the most recent screened booking.
- **B2:** highest latest LSI-R total score; people without one next, by pretrial risk level.
- **Ties:** broken by most recent release; remaining ties share the last places equally (exact expected value).
- **Precision at 100:** share of the 100 listed with the outcome.

## Results (new-arrest outcome)

| Ranking date | Cohort | Base rate | B1 | B2 |
|---|---|---|---|---|
| 1 Apr 2018 | 4,392 | 25.5% | 29% | 30% |
| 1 May 2018 | 4,462 | 25.8% | 23% | 28% |
| 1 Jun 2018 | 4,526 | 25.6% | 24% | 27% |
| 18-month average (Jan 2017 – Jun 2018) | ~3,790 | 26.9% | 29.4% | 31.7% |

The county's existing tools select only 1.1–1.2× as many future re-arrests as random.

## Data decisions (all verified on the database)
- Jail bookings are stored twice in the source; `semantic.bookings` has one row per booking.
- Jail ids are zero-padded to 9 characters to match the county crosswalk.
- Ids the county matched to more than one person are linked to nobody (about 12% of mental health
  service rows). We do not guess, because a wrong link could make someone look already in care.
- Mental health services come from the cleaned table (= raw with exact duplicates removed); health
  department data from raw (the cleaned table is exactly doubled).
- Jail booking data are complete through June 2019, so 1 Jun 2018 is the latest ranking date with a
  full 12-month outcome window. The jail screen covers 89–95% of bookings from 2017.
- Remote county tables have no planner statistics: for ad-hoc queries run `SET enable_nestloop = off;`.

No data or query output is stored in this repository.
