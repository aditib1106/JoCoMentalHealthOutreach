# Update 7 — Teammate Handoff Context

**Due:** Monday 2026-11-23, 23:59 (realistically tonight, 12 hours from write time)
**Audience:** Teammate opening a fresh SSH session on the course server with no prior context.
**Your job:** Build slides 1–21 of the Update 7 deck from data that is already in the project database. You do NOT need to run Triage. One focused refit is being launched separately (~10 min) to unblock slide 22.

---

## 0. One-time setup (SSH session)

```bash
ssh <andrewid>@server.mlpolicylab.dssg.io
cd /class/groups/jail_mh2
pyenv shell mlpolicyclass     # IMPORTANT: NOT jail_mh2 — triage lives here
git fetch --all
git checkout update6-models   # has the U6 feedback applied; this is where U7 continues from
```

DB credentials live in `~/database.yaml` (don't commit, don't share outside the team).

## 1. What's already done (as of this handoff)

- **U6 training run:** completed through model group counts of LR 14/14, DT 112/112, RF 120/120 trained (though RF is only *scored* on the first 21 of 30 validation months), ExtraTrees 36/36 trained (scored 20/30), AdaBoost 3/3 (scored 20/30), Dummy + 4 Baselines on 30/30.
- **Database state** (`built_in_triage_run = 24`): 7,214+ models, ~1.5M evaluation rows, ~764k feature-importance rows.
- **CSV snapshots on disk** (durable):
  - `triage_runs_v2/20261116_205916_afaqk/u6_FINAL_model_group_summary.csv` — 290 model groups, avg P@100, SD, dates scored
  - `triage_runs_v2/20261116_205916_afaqk/u6_prec100_by_date_wide.csv` — Dummy + 4 baselines + LR 41 across 28 months
  - `triage_runs_v2/20261116_205916_afaqk/u6_prk_curve_avg.csv` — avg precision at every percentile 1–100 for the headline groups
  - `triage_runs_v2/20261116_205916_afaqk/run_stdout.log` — 19 MB full triage log

## 2. The champion model for U7

**Group 41 — ScaledLogisticRegression, `C=0.1, L2, saga`.** This is the model you'll analyze on slides 17, 21, 22.

Why this one (cite this on slide 20 if asked):
- Highest avg precision@100 on the **full 30 validation months (0.6493)**.
- Lowest standard deviation across months in the top 10 (σ = 0.0381).
- Within 0.3 percentage points of the best RF (group 320, avg 0.6519) on the 21 months both were scored.
- Shallow RFs (`max_depth=5`) dominated the RF leaderboard; deeper/larger RFs (1000 or 5000 trees) did not improve on the 50-tree RF — i.e. RF plateaued at depth 5, consistent with the professor's "scale up until performance flattens" guidance.

Model IDs for group 41 on each train_end_time are in `triage_metadata.models` — the one for the most recent validation (train_end = 2018-06-01) is **model_id 4233**, and that's the one slide 21 asks about ("one model, trained on your last training set").

## 3. Slide-by-slide checklist

### Slides 1–10 (carry-forward from U6)
Copy the content from the submitted U6 deck (slides 85–95, team Jail MH 2). Add a one-liner caption on 2, 3, 7, 10:

> "Updated per Update 6 feedback: `birth_year` moved to its own `age` block with interval `['all']` only and aggregated with `avg` (mean) instead of `max`, since bookings for the same person can carry different birth years."

### Slides 11–13: v0 baseline run (carry forward from U6)
Baselines are unchanged — re-use the U6 table. Precision@100 across 30 months:
- Dummy prior: 0.274 — base rate
- B4 (prior new-arrest count): 0.472 — the strongest baseline
- B2 (LSI-R + pretrial tiebreak): 0.334
- B1 (BJMHS screen score): 0.332 (only 17 months — early months have no screen data)
- B3 (stay_days sum): 0.322

### Slide 14: planned model grid
Paste the `grid_config` section from `step3_triage/mcrt_triage_config.yaml` (lines 314–378).

### Slide 15: current model runs
Same `grid_config` as slide 14. Add a short note:

> "Resolved medium preset: 290 model groups × 30 monthly splits = 8,700 planned. We completed all Logistic Regression (14/14), Decision Tree (112/112), Baselines (4/4), and Dummy on all 30 months; RandomForest (120 groups) was scored on 21 of 30, ExtraTrees (36) and AdaBoost (3) on 20 of 30. The remaining models are heavier variants (RF with 1000–5000 trees, ExtraTrees with 1000) that did not improve on the shallower top performers; see the limitations slide."

### Slide 16: results over time
Plot: x = validation as-of date, y = precision@100, one line per model group, plus dashed "best case" envelope. Include base rate and baselines.

SQL to pull:
```sql
SELECT m.model_group_id, split_part(m.model_type, '.', -1) AS type,
       e.evaluation_start_time::date AS d,
       e.stochastic_value AS prec100
FROM test_results.evaluations e
JOIN triage_metadata.models m USING (model_id)
WHERE m.built_in_triage_run = 24
  AND e.metric = 'precision@' AND e.parameter = '100_abs'
ORDER BY d, model_group_id;
```

Plot in Python/matplotlib: group by model_type → color; plot each model_group_id as a thin line; overlay dashed line at MAX across groups per date = "best case"; overlay dotted line for Dummy = base rate; overlay solid thick lines for the 4 baselines.

### Slide 17: selected model details
Headline table — two LR variants, because they are the only two top-10 model groups scored on **all 30 months** (RFs only cover 21 months, so they can't appear on the "most recent validation set" = 2018-06-01):

| | Model 1 (champion) | Model 2 |
|---|---|---|
| model_group_id | **41** | **30** |
| Model type | ScaledLogisticRegression | ScaledLogisticRegression |
| Hyperparameters | C=0.1, penalty=l2, solver=saga | C=1, penalty=l1, solver=saga |
| Avg precision@100 (30 dates) | **0.6493** | **0.6490** |
| Standard deviation | 0.0381 | 0.0493 |
| Precision@100 on 2018-06-01 | 0.690 | 0.680 |

Mention on the limitations slide (19 or 20): the best RF (group 320) scored 0.6519 on the 21 months it was scored, but was not scored on 2018-06-01, so it cannot appear on slide 18's "most recent validation set". The LR models cover every month and are within 0.3 pp of the best RF where both overlap.

### Slide 18: PR-k curves (champion + runner-up + best baseline, at 2018-06-01)
Three panels: Baseline 4 (group 29), LR champion (group 41), LR runner-up (group 30).
Pull from DB:
```sql
SELECT m.model_group_id, split_part(m.model_type,'.',-1) AS type,
       e.metric,
       CAST(replace(e.parameter, '_pct', '') AS int) AS pct,
       e.stochastic_value AS value
FROM test_results.evaluations e
JOIN triage_metadata.models m USING (model_id)
WHERE m.built_in_triage_run = 24
  AND e.metric IN ('precision@', 'recall@')
  AND e.parameter LIKE '%_pct'
  AND e.evaluation_start_time::date = '2018-06-01'
  AND m.model_group_id IN (41, 30, 29)
ORDER BY model_group_id, metric, pct;
```
Plot 3 panels side by side: Baseline 4 (group 29), LR champion (41), LR runner-up (30). x = % of cohort (1–100), left y = precision (blue line), right y = recall (red line). Dashed vertical at k = 100/4526 ≈ 2.2% of the cohort. Expected numbers at k=100: Baseline 4 ≈ 0.44 precision, LR 41 ≈ 0.69, LR 30 ≈ 0.68; recall@100 ≈ 0.06 for both LR models (100 picks × 0.69 ÷ 1160 positives).

### Slide 19: key changes since U6
1. Applied U6 feedback meeting fixes: `birth_year` moved to its own `age` block, interval `['all']`, aggregated with `avg` (mean) instead of `max`.
2. Completed the medium-preset grid run: 290 model groups × 30 monthly splits planned; finished all LR, DT, baselines, Dummy; partial on RF/ET/AdaBoost (see limitations).
3. Chose Logistic Regression (group 41) as champion for interpretability analysis on the basis of (a) full coverage on all 30 months, (b) lowest variance, (c) within 0.3 pp of the best RF where both were scored.

### Slide 20: ML results over time discussion
Three bullets:
- **Performance change:** Best average P@100 moved from 0.69 at a single month in U5 (small grid, one date) to **0.649 across all 30 months** in U6 with the medium grid. LR and shallow RF converged on the same answer; deeper/larger RFs did not help, suggesting the feature set — not model complexity — is now the bottleneck.
- **Selection strategy:** Mean precision@100 across the full validation window, with standard deviation as a tie-break. JCMHC runs the model monthly, so stability month-to-month matters as much as peak average.
- **Refinements of interest:** The 5 deferred feature categories from the Update 5 context (warrants, charge-group bookings, police arrests, probation status, days-to-first-service). Also demographic fairness audit on the champion before deployment.

### Slide 21 (part 1): one-model interpretability — feature importances
For model_id 4233 (group 41, LR C=0.1 L2, train_end 2018-06-01):

```sql
SELECT feature, feature_importance, rank_abs
FROM train_results.feature_importances
WHERE model_id = 4233
ORDER BY rank_abs
LIMIT 20;
```

Plot as a horizontal bar chart, sorted by absolute importance, bars coloured by sign (positive importance = red = increases risk; negative = blue = decreases risk). The top predictors should be: `jail_entity_id_1year_is_new_arrest_sum`, `jail_entity_id_all_is_new_arrest_sum`, `amb_entity_id_1year_runs_count`, and `age_entity_id_all_birth_year_avg` at rank 5 (the new U6 age feature contributes!).

### Slide 21 (part 2) + Slide 22: cross-tabs

✅ **The focused refit has already finished.** Champion predictions are in `test_results.predictions` for `model_id = 7667` (same group 41, C=0.1 L2, train_end 2018-06-01).

Recipe — runnable in a notebook:

```python
import os, yaml, gzip, pandas as pd
from sqlalchemy import create_engine

# 1. DB engine
db = yaml.safe_load(open(os.path.expanduser('~/database.yaml')))
eng = create_engine(
    f"postgresql+psycopg2://{db['user']}:{db['pass']}@{db['host']}:{db['port']}"
    "/johnson_county_ddj_jail_mh2",
    connect_args={'options': '-c enable_nestloop=off'})

# 2. Predictions for the champion on the most recent validation date
preds = pd.read_sql("""
  SELECT entity_id, score, label_value
  FROM test_results.predictions
  WHERE model_id = 7667 AND as_of_date = '2018-06-01'
""", eng)  # ~4,526 rows

# 3. The matching feature matrix (reused from U6, saved at this exact path)
MTX = "/class/groups/jail_mh2/triage_runs_v2/20261116_205916_afaqk/matrices/4f285d57c1e59cf700bfa90135d4ecda.csv.gz"
feats = pd.read_csv(MTX)  # columns: entity_id + ~230 feature columns + label

# 4. Join + rank
df = preds.merge(feats, on='entity_id', how='inner')
df = df.sort_values('score', ascending=False).reset_index(drop=True)
df['bucket'] = ['top_100' if i < 100 else 'rest' for i in df.index]

# 5. Mean of each feature by bucket, with ratio
feature_cols = [c for c in feats.columns if c not in ('entity_id', 'as_of_date', df.columns[-1])]
means = df.groupby('bucket')[feature_cols].mean().T  # rows=features, cols=[rest, top_100]
means['ratio'] = means['top_100'] / means['rest'].replace(0, pd.NA)
means['abs_log_ratio'] = means['ratio'].apply(lambda r: abs(pd.np.log(r)) if r and r > 0 else 0)

# 6. Top 10 features where the top-100 bucket is most different from the rest
top_crosstab = means.sort_values('abs_log_ratio', ascending=False).head(10)[['top_100', 'rest', 'ratio']]
top_crosstab.round(3).to_csv('step3_triage/u7/slide22_crosstabs.csv')
print(top_crosstab)
```

Drop the resulting table onto slide 22 (5–10 rows, sorted by ratio). Pick features that TELL A STORY — don't just show whatever is at the top of the auto-sort; e.g. prior arrest counts, age, screen score, LSI-R, days-since-release. Slide 22's whole point is "these are the features that separate the people the model thinks are highest-risk from everyone else" — you want readers to look at it and go "yes, that makes sense."

### Slides 23, 24
Discussion of feature importances + cross-tabs + a final "key changes" bullet list that mirrors slide 19.

## 4. Division of labour (suggested)

- **You (teammate):** slides 1–20, and the plots on 21. Everything pulls from DB; no Triage needed.
- **Me/coordinator:** launch the focused refit, build cross-tabs (slide 22) when it finishes, assemble the final deck.

## 5. Things NOT to do

- Don't launch another Triage experiment. The focused refit has already completed.
- Don't run `git push` with `Co-Authored-By: Claude …`; keep commits under your own name only.
- Don't change `step3_triage/mcrt_triage_config.yaml` — it's locked at the U6-with-feedback state and that's what the DB numbers are tied to. New configs for U7 go under `step3_triage/u7/`.

## 6. Submission

- Deck: upload to the course Google Slides file. **Ask Aditi for the URL** — I don't have it.
- Code: put the notebook under `step3_triage/u7/notebooks/`, commit as yourself (no Co-Authored-By trailer), push to `update6-models` (or make a new `update7-models` branch and push that — ask Afaq which the team prefers).
- Due: Monday 2026-11-23, 23:59 — but the team wants it tonight if possible.

## 7. Quick sanity check you can run before you start plotting

```bash
pyenv shell mlpolicyclass
python -c "
import yaml, os
from sqlalchemy import create_engine
db = yaml.safe_load(open(os.path.expanduser('~/database.yaml')))
eng = create_engine(f\"postgresql+psycopg2://{db['user']}:{db['pass']}@{db['host']}:{db['port']}/johnson_county_ddj_jail_mh2\")
import pandas as pd
print('U6 model groups:', pd.read_sql(\"SELECT COUNT(DISTINCT model_group_id) FROM triage_metadata.models WHERE built_in_triage_run = 24\", eng).iloc[0,0])
print('Champion predictions:', pd.read_sql(\"SELECT COUNT(*) FROM test_results.predictions WHERE model_id = 7667\", eng).iloc[0,0])
print('Feature importances for model 4233:', pd.read_sql(\"SELECT COUNT(*) FROM train_results.feature_importances WHERE model_id = 4233\", eng).iloc[0,0])
"
```

You should see: 290 model groups, 4,526 predictions, 107 feature importances. If any is 0 or errors, stop and ping Afaq.
