# Johnson County Mental Health Outreach

Identifying people released from Johnson County jail who are at highest risk of being
booked again, so the Johnson County Mental Health Center (JCMHC) can prioritize its
~100 monthly outreach slots.

## Problem formulation

| | |
|---|---|
| Prediction date | 1st of every month |
| Cohort | Adults released from jail in the previous month, not in jail on the prediction date, with at least one prior JCMHC record |
| Label | Booked into jail again within 12 months of the prediction date |
| Evaluation period | Monthly, Jan 2014 – Jun 2018 |
| Metric | Precision and recall at top 100 |

## Preliminary baselines

Average over 54 monthly lists (see `sql/03_baselines.sql`):

| Method | Precision@100 | Recall@100 |
|---|---|---|
| Prior (random selection) | 52.7% | 33.2% |
| Most jail bookings in past 3 years | 65.8% | 41.5% |
| Shortest time from release to rebooking | 65.7% | 41.4% |

## Repository layout

| File | Step |
|---|---|
| `sql/01_cohort.sql` | Monthly prediction dates and the eligible cohort |
| `sql/02_label.sql` | 12-month rebooking label and base rate |
| `sql/03_baselines.sql` | Baseline rankings and precision/recall at top 100 |

## Data sources

All inputs come from the `semantic` schema of the project database, where records from
each county system are linked to a single person ID (`entity_id`):

- `semantic.bookings`: jail bookings and releases
- `semantic.jcmhc_services`, `semantic.jcmhc_diagnoses`, `semantic.jcmhc_calls`: JCMHC records

## Running

Requires access to the project database with credentials in `~/.pgpass`. The steps use
temporary tables, so they must run in one session and do not modify the database.

```bash
psql -h database.mlpolicylab.dssg.io -d johnson_county_ddj_jail_mh2 \
     -f sql/01_cohort.sql -f sql/02_label.sql -f sql/03_baselines.sql
```

No data is stored in this repository.
