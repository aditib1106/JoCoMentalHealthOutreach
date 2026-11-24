#!/usr/bin/env python
"""Export test_results.aequitas joined to model metadata + precision@100 as CSV.

WHAT THIS DOES
--------------
After the bias audit has been run (via `python step3_triage/run.py --replace=False`
with the bias_audit_config added to the YAML), aequitas has written a bunch of
rows to test_results.aequitas — one per (model_id, attribute_name,
attribute_value, parameter). To make the fairness scatter plots in Update 8 we
need every one of those rows joined to:
  - the model_group_id / model_type / hyperparameters (so we can label and
    color-code points by model type on the scatter plots)
  - the precision@100 from test_results.evaluations (so we have the x-axis
    for the scatter plots)
This script does exactly that join, pulls the rows for one validation date,
and writes them to a single long-format CSV that fairness_plots.py consumes.

WHY A SEPARATE SCRIPT
---------------------
Aditi's export_results.py already pulls evaluation metrics, but it doesn't
touch aequitas. Rather than modify her script (which the team may still be
using for other things), we write a focused companion that reuses her
get_engine() pattern. Separation of concerns keeps both scripts shorter and
easier to defend to the prof.

WHY ONE VALIDATION DATE AT A TIME
---------------------------------
Lecture 18 slide 26's example scatter plot is "for all models applied to the
most recent validation set". Update 8's deck template says the same. A single
validation date keeps each scatter plot readable (one dot per model group
rather than one per model) and matches how we chose the model in Update 7.
Update 9 can repeat across all 30 dates if we want stability analysis.

WHY NOT xlsx LIKE export_results.py
-----------------------------------
fairness_plots.py downstream reads CSV directly with pandas — no Excel step
needed. One file per date keeps things simple.

USAGE
-----
    python export_aequitas.py \\
        --as-of-date 2018-06-01 \\
        --out /class/vidhikot/u8_audit/aequitas_2018-06-01.csv

The 2018-06-01 date matches the "most recent validation list" we used for the
Update 7 PR-k slide. Use the same date for consistency across updates.
"""
import argparse
import os

import pandas as pd
import yaml
from sqlalchemy import text
from sqlalchemy.engine.url import URL
# triage.util.db.create_engine wraps sqlalchemy with triage's connection
# defaults (pool recycling, SSL, etc). Using it keeps us consistent with how
# Aditi's export_results.py connects.
from triage.util.db import create_engine


# ~/database.yaml is the standard per-user DB credentials file used
# everywhere else in the project. Same pattern as Aditi's export_results.py.
DB_CONFIG_PATH = os.path.expanduser('~/database.yaml')


def get_engine():
    """Open a Postgres connection using the shared ~/database.yaml creds.

    Copied verbatim from Aditi's export_results.py so both scripts talk to the
    database the same way. One important flag:
        -c enable_nestloop=off
    disables nested-loop joins at the session level, which empirically speeds
    up triage's wide read queries on this DB by 10x+ because the planner tends
    to pick bad nested loops on the aequitas/evaluations join.
    """
    with open(DB_CONFIG_PATH) as f:
        db = yaml.safe_load(f)
    url = URL.create(
        'postgresql+psycopg2',
        host=db['host'], username=db['user'], password=db['pass'],
        port=db['port'], database='johnson_county_ddj_jail_mh2',
    )
    return create_engine(url, connect_args={'options': '-c enable_nestloop=off'})


# ---------------------------------------------------------------------------
# Column selection
# ---------------------------------------------------------------------------
# triage versions vary in exactly which aequitas columns they write. We can't
# hard-code a SELECT list because a missing column would throw. Instead we
# SELECT * from aequitas and reorder below. PREFERRED_ORDER lists the columns
# we care about most (for human eyeballing the CSV and for downstream plots);
# anything triage writes that's not in this list is kept but moved to the
# right. This makes the CSV self-documenting when opened in Excel.
PREFERRED_ORDER = [
    # ---- identifiers --------------------------------------------------------
    'model_id',                     # unique per train_end_time x hyperparams combo
    'model_group_id',               # groups runs of the same model across splits
    'model_type',                   # sklearn class path, used for scatter plot color
    'hyperparameters',              # JSON blob, kept so we can grep for which RF variant
    'model_comment',                # free-text tag we set in the config
    'train_end_time',               # when training data for this model ended
    'evaluation_start_time',        # the validation date; one per CSV file
    'parameter',                    # aequitas threshold, e.g. '100_abs' for top_n=100

    # ---- group identity -----------------------------------------------------
    'attribute_name',               # 'race' or 'sex'
    'attribute_value',              # 'W', 'B', 'MALE', 'FEMALE', ...
    'ref_group_value',              # 'W' for race, 'MALE' for sex

    # ---- raw group counts ---------------------------------------------------
    # These are the inputs to every metric aequitas computes. Having them in
    # the CSV lets us reconstruct any metric we didn't anticipate without
    # re-querying the DB.
    'group_size',                   # people from this group in the cohort on this date
    'group_label_pos',              # actual positives in this group
    'prevalence',                   # group_label_pos / group_size — the base rate
    'tp', 'fp', 'fn', 'tn',         # confusion matrix for this group at top_n=100
    'pp', 'pn',                     # predicted positive/negative counts

    # ---- per-group metrics --------------------------------------------------
    'tpr',                          # recall for this group (PRIMARY per fairness tree)
    'tnr', 'fpr', 'fnr',
    'precision',                    # ppv for this group
    'fdr',                          # 1 - precision; SECONDARY diagnostic metric
    'ppr',                          # predicted positive rate = pp / cohort
    'pprev',                        # predicted prevalence = pp / group_size

    # ---- disparity ratios (metric / metric_of_reference_group) --------------
    # These are the y-axes for our four scatter plots. 1.0 means parity.
    'tpr_disparity',                # PRIMARY plot axis for race-TPR and sex-TPR
    'fpr_disparity',
    'fnr_disparity',
    'fdr_disparity',                # SECONDARY plot axis for race-FDR and sex-FDR
    'precision_disparity',
    'pprev_disparity',
    'ppr_disparity',

    # ---- selection metrics for the x-axis -----------------------------------
    # Pulled from test_results.evaluations and merged in below. These are what
    # we plot on the horizontal axis; pp@100 recall is kept alongside for the
    # discussion slide bullet points.
    'precision_at_100',
    'recall_at_100',
]


def fetch_aequitas(engine, as_of_date):
    """Pull every aequitas row for the given validation date, with model metadata.

    The join is aequitas -> triage_metadata.models on model_id. We bring along
    model_group_id and model_type so downstream plot code can color-code points
    without a second query. hyperparameters is kept as text (not jsonb) so it
    survives the CSV round-trip without pandas trying to parse it.
    """
    q = text("""
        SELECT a.*,
               m.model_group_id,
               m.model_type,
               m.hyperparameters::text AS hyperparameters,
               m.model_comment,
               m.train_end_time::date  AS train_end_time
        FROM   test_results.aequitas a
        JOIN   triage_metadata.models m USING (model_id)
        WHERE  a.evaluation_start_time = :as_of
    """)
    return pd.read_sql(q, engine, params={'as_of': as_of_date})


def fetch_precision_at_100(engine, as_of_date):
    """Pull precision@100 and recall@100 for every model on the same date.

    WHY '100_abs' NOT '100'
    -----------------------
    triage stores the top_n=100 threshold as parameter='100_abs' (absolute
    count) to distinguish it from percentile thresholds like '1_pct' (top 1%).
    We lock to the absolute-100 version because JCMHC's capacity is a fixed
    100 contacts, not a percentage.

    WHY subset_hash = ''
    --------------------
    '' is the triage convention for "the full cohort, no subset filter." If we
    omitted this filter we'd pull extra rows for any subsetted evaluations
    triage happened to compute. We want the overall precision@100.

    WHY stochastic_value NOT value
    ------------------------------
    When a model has score ties at the top_n=100 boundary, the deterministic
    value depends on sort stability; stochastic_value is the expected value
    averaged over random tie-breaks. Lecture 18 slide 25 (and the underlying
    Chouldechova paper) uses stochastic_value as the honest estimate.
    """
    q = text("""
        SELECT model_id,
               MAX(CASE WHEN metric = 'precision@'
                         AND parameter = '100_abs'
                        THEN stochastic_value END) AS precision_at_100,
               MAX(CASE WHEN metric = 'recall@'
                         AND parameter = '100_abs'
                        THEN stochastic_value END) AS recall_at_100
        FROM   test_results.evaluations
        WHERE  evaluation_start_time = :as_of
          AND  subset_hash = ''
          AND  metric IN ('precision@', 'recall@')
          AND  parameter = '100_abs'
        GROUP  BY model_id
    """)
    return pd.read_sql(q, engine, params={'as_of': as_of_date})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--as-of-date', required=True,
                    help='Validation date (YYYY-MM-DD), e.g. 2018-06-01')
    ap.add_argument('--out', required=True,
                    help='Output CSV path')
    args = ap.parse_args()

    engine = get_engine()

    # Step 1: aequitas rows + model metadata.
    print(f'fetching aequitas rows for {args.as_of_date}')
    aeq = fetch_aequitas(engine, args.as_of_date)
    print(f'  pulled {len(aeq):,} rows across {aeq.model_id.nunique()} models '
          f'and {aeq.attribute_name.nunique()} attributes')

    # Step 2: precision@100 / recall@100 per model on the same date.
    print(f'fetching precision@100 / recall@100 for the same date')
    prk = fetch_precision_at_100(engine, args.as_of_date)
    print(f'  pulled {len(prk):,} per-model rows')

    # Step 3: left-join on model_id. Left-join (not inner) so that if some
    # aequitas rows exist for a model that has no precision@100 (shouldn't
    # happen, but could if evaluations was pruned), we don't silently drop
    # audit rows.
    merged = aeq.merge(prk, on='model_id', how='left')

    # Step 4: reorder columns for human readability in the CSV. See
    # PREFERRED_ORDER's comments above for why each column is wanted.
    present = [c for c in PREFERRED_ORDER if c in merged.columns]
    leftover = [c for c in merged.columns if c not in present]
    merged = merged[present + leftover]

    # Step 5: write the CSV. dirname('') handles the case where --out is just
    # a filename with no directory; os.makedirs() would error on empty string.
    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    merged.to_csv(args.out, index=False)
    print(f'wrote {len(merged):,} rows to {args.out}')


if __name__ == '__main__':
    main()
