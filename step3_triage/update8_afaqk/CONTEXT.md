# Update 8 — full story of how we got to the final audit

Written for the team record so nobody re-learns these bugs. Chronological.

---

## 0. Starting point (Mon 2026-11-18)

Afaq ran `mcrt_triage_config_afaqk.yaml` + `run_afaqk.py` — the RF-only extremes sweep: **n_estimators ∈ {10, 5000} × max_depth ∈ {2, 10, null}** (plus 4 baselines + Dummy). 330 models total (11 groups × 30 monthly splits). Headline (precision@100 across 30 splits, in `test_results.evaluations`):

- mg 485 (RF 5000 × depth 10): 0.623  ← winner
- mg 483 (RF 5000 × depth 2):  0.621
- mg 482 (RF 10 × depth 2):    0.618
- Best baseline mg 475 (prior arrests): 0.471

## 1. First bug: summary step crashes

Triage prints "SUCCESS Training, testing and evaluating models completed" and then its post-run summary (`experiment_summarizer.py:476`) blows up:

```python
if df.metric_value.isna().unique():
ValueError: The truth value of an array with more than one element is ambiguous.
```

Root cause: `.isna().unique()` returns a numpy array `[True, False]` when some models lack an evaluation row for `recall@1_pct` (the default triage looks for), and Python can't coerce it to a boolean. Intent is clearly `.all()` or `.any()`. **Non-fatal to results** — training, evaluation, and (later) aequitas all write to the DB before this runs. The process exits non-zero but the data is safe.

## 2. Second bug: BJMHS baseline has no data pre-2016

Model group 472 (baseline that ranks by `jail_entity_id_all_mhs_total_max`) only produces predictions for 19 of the 30 monthly splits. We traced it: `semantic.bookings.mhs_total` is near-empty before 2016 (3 rows in 2014, 0 in 2015), ramps up through 2016, hits full coverage in 2017+. For every validation list before 2016-12, that baseline's one feature is all-imputed-zero → ties for every entity → no rank → no prediction. Not a modeling bug, a data-availability one. We note it in Update 8 and move on.

## 3. Vidhi's approach to Update 8 (Mon 11-24)

Strategy correct per the course deliverable — "use triage's built-in bias audit tool." She added a `bias_audit_config` to `mcrt_triage_config_medium.yaml` (Aditi's big grid, 7,247 models) and tried to re-run with `replace=False` expecting triage to reuse pickles and just write aequitas rows.

**What broke:** `step3_triage/run.py` (and `run_afaqk.py`) mint a fresh timestamped `project_path` on every invocation. With no pickles at the new path, triage retrained from scratch — 2,231 models queued before she killed it. Her instinct that no retraining *should* be needed was right; the script silently defeated it.

Secondary issue she'd have hit anyway: of the medium grid's 8,700 declared specs, only ~7,247 actually trained the first time. Auditing the other ~1,453 specs with `bias_audit_config` present would still trigger training attempts.

Her commits: `96a34fa` (bias_audit_config added) and `bfb475f` (run.py pointed at medium config) on `upstream/update8-fairness`.

## 4. Afaq's first attempt (sidetrack, discarded)

To avoid any retrain risk, Afaq computed TPR/FDR directly from `test_results.predictions` joined to `semantic.bookings`. That worked for **10 models** that have per-person predictions stored (LR champion mg 41, alternate mg 30, RF mg 24, baselines from the `jail_mh2_update7_focus` and `jail_mh2_u5_mini_prk` comments). Instant, read-only, no triage.

**Problem:** those 10 are from Aditi's earlier runs, not our team's current RF extremes sweep. Deliverable says "different models you *built*". Wrong scope. We dropped this path (`fairness_from_predictions.py` was removed in commit `0d5a7d3`).

## 5. The single path that actually works

`run_bias_afaqk.py` in `step3_triage/update8_afaqk/`:

- Loads `mcrt_triage_config_afaqk.yaml` unchanged.
- Injects a `bias_audit_config` pointed at `semantic.bookings` (race: `W`/`B`, sex: `MALE`/`FEMALE`, top_n=100).
- **Points `project_path` at the existing `triage_runs_v2/20261118_191929_afaqk_rf/`** — this is the fix for Vidhi's retrain trap. With 330 pickles + 60 matrices already there, triage reuses them.
- Sets `role=jail_mh2` on the connection so any new tables (`protected_groups_*`, `labels_*`) are owned by the team role.

## 6. Three more bugs hit, three more fixes

**Bug A: permission denied on `protected_groups_754ccd6d7e2af7a7ac88df2745e18b6d`.**
Vidhi's killed run left behind a `protected_groups_*` table owned by her login (`vidhikot`). Our audit tried to read it and couldn't.
Fix: `DROP TABLE` the orphan. New table now owned by `jail_mh2` so any teammate can run again.

**Bug B: `ZeroDivisionError` in `BaselineRankMultiFeature`.**
When a baseline's feature has no variance on an early split (BJMHS pre-2016 problem again), the ranker's final normalization does `[r/max_rank for r in ranks]` with `max_rank == 0`.
Fix: one-line patch to the installed triage (`component/catwalk/baselines/rankers.py:188`) — guard with `[0.0 for _ in ranks] if max_rank == 0 else ...`. Local only; apply again if the venv is rebuilt.

**Bug C: baseline models re-trained.**
The RF pickles reused cleanly (they have `random_state=2193` baked into hyperparameters). Baselines and Dummy don't set `random_state`, so their `model_hash` shifted when `bias_audit_config` was present and triage trained fresh pickles for them. Not a correctness problem — the new pickles produce the same deterministic rankings — but it did add ~20 min to the run. In the DB, every baseline model_group has two model_ids on 2018-06-01 now (original + audit-run); `fairness_plots.py` dedupes with `DISTINCT ON (model_group_id) ... ORDER BY model_id DESC`.

**Bug D: same isna().unique() summary crash from §1.** Post-audit, the summary step crashes again. Still non-fatal; all aequitas data is already written.

## 7. Final state

- `test_results.aequitas`: 3,072 rows, 349 models (330 original + 19 retrained baselines/dummy with new model_ids). `jail_mh2_update7_rf_afaqk` comment.
- Outputs at `step3_triage/update8_afaqk/exports/`:
  - `disparities.csv` — 22 rows (11 model groups × 2 attributes × 1 date).
  - `tpr_disparity_{race,sex}.png`, `fdr_disparity_{race,sex}.png` — the four Update 8 scatter plots.

**Headline (2018-06-01, top-100):**

| mg | model | prec@100 | race B TPR disp | sex F TPR disp | race B FDR disp | sex F FDR disp |
|---|---|---|---|---|---|---|
| 485 | RF 5000 × d10 | **0.58** | 0.82 | 1.05 | 0.94 | 0.85 |
| 484 | RF 10 × d10 | 0.57 | 1.02 | 0.67 | 0.65 | 1.52 |
| 483 | RF 5000 × d2 | 0.54 | **1.00** | 1.06 | 0.64 | 0.67 |
| 482 | RF 10 × d2 | 0.54 | 0.88 | 0.95 | 0.70 | 0.92 |
| 487 | RF 5000 × d∞ | 0.48 | 1.17 | 0.94 | 0.85 | 0.85 |
| 486 | RF 10 × d∞ | 0.45 | 1.14 | 1.85 | 0.74 | 0.83 |
| 475 | Baseline prior-arrests | 0.44 | 0.83 | 0.49 | 1.05 | 0.86 |
| 471 | Dummy prior | 0.26 | — excluded (constant score) — | | | |

mg 485 is best on precision; mg 483 gives 4-pt-lower precision with closer-to-parity recall on both attributes. That's the Pareto trade-off for the discussion slide.

## 8. What "mg" means in the plots

`mg` = `model_group_id`. One unique model recipe (type + hyperparameters) that was trained on every monthly time split. So "mg 485" is the shorthand label for "the specific RF with n_estimators=5000, max_depth=10, min_samples_split=10, criterion=gini." The id lets us put 11 dots on a scatter plot without writing the whole hyperparameter list for each.
