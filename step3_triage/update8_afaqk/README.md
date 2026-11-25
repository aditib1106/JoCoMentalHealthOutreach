# Update 8 — Bias and fairness audit of the RF extremes run

Audits the Update 7 RF-only extremes sweep (330 models, 11 model groups) with triage's built-in aequitas tool, as the deliverable asks. Produces the four scatter plots (TPR and FDR disparity vs precision@100, for Black/White and Female/Male) on the last validation list (2018-06-01).

## How to run

```bash
# 1. Run the audit. Reuses the existing RF run dir, so no retraining.
#    Takes ~20-40 min. Watch step3_triage/update8_afaqk/logs/audit.log.
python step3_triage/update8_afaqk/run_bias_afaqk.py

# 2. Plot from test_results.aequitas.
python step3_triage/update8_afaqk/fairness_plots.py
```

## Files

| File | Purpose |
|---|---|
| `run_bias_afaqk.py` | Injects `bias_audit_config` (race, sex, top_n=100) into `mcrt_triage_config_afaqk.yaml` and runs triage with `project_path` pointed at the existing RF run dir so the 330 trained pickles are reused. Writes rows to `test_results.aequitas`. |
| `fairness_plots.py` | Reads `test_results.aequitas` joined to `test_results.evaluations` for the 2018-06-01 validation list and writes four PNGs + one CSV. |
| `exports/disparities.csv` | Long-format audit table: one row per `(model_group, attribute, value)`. |
| `exports/*.png` | The four scatter plots for slide 26 of the Update 8 deck. |
| `logs/audit.log` | Audit progress log (expect many "Skipping matrix because already exists" lines — that's the pickle reuse we want). |

## Design choices (locked, per team plan)

| Choice | Decision | Why |
|---|---|---|
| Attributes | race, sex | Policy-salient, available on every entity via `semantic.bookings` |
| Reference groups | White (race), Male (sex) | Predefined, majority group |
| Primary metric | **TPR / recall parity** | Fairness tree: assistive intervention + small fraction → recall parity |
| Secondary diagnostic | FDR | Measures how outreach slots are spent; not a second fairness objective |
| Threshold | top_n = 100 | JCMHC monthly outreach capacity |
| Model selection | Pareto frontier (precision@100 vs TPR disparity) | Course lecture explicitly recommends this over hard thresholds |

## Critical caveat (first-class)

Our label is **observed jail rebooking following a new arrest**, not a direct measure of criminal behavior or mental-health need. Because the label is mediated by policing, observed TPR disparity may reflect upstream differences in the label as well as model behavior. Disparity is diagnostic; it does not prove the model is biased.

## One gotcha we hit (for the team record)

`run_afaqk.py` (and `run.py`) always mint a new timestamped `project_path`, so an audit launched that way finds zero pickles and retrains everything. `run_bias_afaqk.py` fixes this by pointing `project_path` at the existing `triage_runs_v2/20261118_191929_afaqk_rf` directory. Same fix would apply to an audit of Aditi's medium grid (point at `triage_runs_v2/20261116_205916_afaqk/`).
