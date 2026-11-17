# Update 7 — focused refit for cross-tabs + PR-k

Purpose: produce per-entity predictions for the U6 champion on the last
validation date (2018-06-01), so we can build:
  - Slide 18/21: PR-k curve for the champion on the most recent validation set
  - Slide 22: cross-tabs (mean of each feature over top k% vs bottom (100-k)%)
  - Feature importances (slide 21) are ALREADY in train_results.feature_importances
    for every LR 41 model — no refit needed for the importances plot itself.

Prerequisite: the U6 feature matrices + labels + cohort tables must already exist
in the DB (they do — the main U6 run has been using them for 20+ hours).

Config shape:
  - Same label_config + feature_aggregations as U6 (so matrix hashes match → reuse)
  - temporal_config restricted to the single most recent split (train_end 2018-06-01)
  - grid_config: just the current champion (LR C=0.1, l2) + runner-up (LR C=1, l1),
    both of which are already at ~0.649 avg P@100
  - scoring: same percentiles 1..100 so the PR-k curve comes from evaluations
  - model_comment: 'jail_mh2_update7_focus' (so this run gets its own hash)
  - run.py uses save_predictions=True (the key difference)

After the run:
  - test_results.predictions will have rows for every (model_id, entity_id, as_of_date)
  - For cross-tabs: join predictions to the feature matrix on (entity_id, as_of_date),
    rank by score desc, take top k, compute means. See crosstabs.sql in this folder.
