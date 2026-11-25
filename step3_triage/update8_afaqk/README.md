# Update 8 — Afaq's complementary fairness audit

Companion to Vidhi's `step3_triage/export_aequitas.py` + `mcrt_triage_config_medium.yaml` `bias_audit_config`. Both target the same deliverable, but take different paths and cover different model sets.

## What's here

| File | What it does |
|---|---|
| `fairness_from_predictions.py` | Computes precision@100, TPR and FDR per race/sex group directly from `test_results.predictions` joined to `semantic.bookings`. **Read-only, no triage, no retraining.** |
| `run_bias_afaqk.py` | Aequitas fallback for models without stored predictions. Injects `bias_audit_config` into Afaq's RF config and points at the existing RF run dir so pickles are reused. |
| `exports/disparities.csv` | Per-model group counts, TPR/FDR per group, disparity ratios. Source of truth for the plots. |
| `exports/*.png` | Four scatter plots: TPR and FDR disparity vs precision@100, for Black/White and Female/Male. |

## Which models this covers

10 models that have per-person predictions stored in `test_results.predictions` on **2018-06-01**:

- `jail_mh2_update7_focus` (6 models): LR champion **mg 41** (C=0.1, L2), alternate **mg 30** (C=1, L1), + mg 31 / 40 variants, Dummy mg 25, baseline mg 29.
- `jail_mh2_u5_mini_prk` (4 models): RF **mg 24**, LR mg 22, Dummy mg 20, baseline mg 21.

Does **not** cover the 330 Afaq RF-extremes models (no stored predictions) or the 7,247 Aditi medium-grid models. For those, Vidhi's triage/aequitas path is the way — see note below.

## Why two paths

Different models have predictions saved (vs not), so no single approach covers everything cheaply:

- **Stored predictions** → compute fairness math by hand, instant, transparent. (This folder.)
- **No stored predictions** → need triage to re-evaluate with `bias_audit_config` and `replace=False`. The audit populates `test_results.aequitas`. (Vidhi's `export_aequitas.py`.)

**Important gotcha** we hit: `run.py` / `run_afaqk.py` create a new timestamped `project_path` on every invocation, so the audit launched that way finds zero pickles and retrains from scratch. Fix: point `project_path` at the **existing** run directory. `run_bias_afaqk.py` encodes this for the RF dir; the same fix is needed for the medium-grid audit (point at `triage_runs_v2/20261116_205916_afaqk/`).

## Headline numbers (2018-06-01, top-100)

| mg | model | prec@100 | race TPR disp (B/W) | sex TPR disp (F/M) | race FDR disp | sex FDR disp |
|----|-------|---------|------|------|------|------|
| 41 | **LR champion** C=0.1 L2 | 0.69 | **1.03** | 0.89 | 0.68 | 1.11 |
| 30 | LR alternate C=1 L1    | 0.68 | 0.97 | 1.13 | 0.57 | 1.22 |
| 24 | Random forest          | 0.58 | 1.00 | 1.66 | 0.58 | 0.91 |
| 29 | Baseline prior-arrest  | 0.43 | 0.83 | 0.49 | 1.00 | 0.93 |

1.0 = parity. Dummy excluded from plots (constant score → random top-100). Only ~20 Black people and ~27 women in each top-100 — one or two people swing a ratio. Label is jail rebooking, so disparity ≠ proven model bias (see plan.md).
