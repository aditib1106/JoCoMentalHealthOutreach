-- Cross-tabs for slide 22.
-- Prerequisite: the U7 focused refit has completed (model_comment='jail_mh2_update7_focus')
-- and test_results.predictions has rows for the champion on 2018-06-01.
--
-- Pick the champion model_id (highest precision@100 among the LR groups in the U7 run).

-- Step 1: identify champion model_id
WITH champ AS (
  SELECT m.model_id
  FROM triage_metadata.models m
  JOIN test_results.evaluations e USING (model_id)
  WHERE m.model_comment = 'jail_mh2_update7_focus'
    AND m.model_type = 'triage.component.catwalk.estimators.classifiers.ScaledLogisticRegression'
    AND e.evaluation_start_time::date = '2018-06-01'
    AND e.metric = 'precision@' AND e.parameter = '100_abs'
  ORDER BY e.stochastic_value DESC
  LIMIT 1
),
-- Step 2: top 100 vs rest, join to feature matrix
-- (Replace <feature_matrix_table> with the actual matrix table name for the
--  champion model's test matrix — find it in triage_metadata.matrices; name
--  pattern is usually like 'features.<hash>' or query triage_metadata.matrices
--  for the uuid matching the model's test matrix.)
ranked AS (
  SELECT p.entity_id, p.score,
         ROW_NUMBER() OVER (ORDER BY p.score DESC) AS rnk,
         CASE WHEN ROW_NUMBER() OVER (ORDER BY p.score DESC) <= 100 THEN 'top_100'
              ELSE 'rest' END AS bucket
  FROM test_results.predictions p
  JOIN champ USING (model_id)
  WHERE p.as_of_date = '2018-06-01'
)
SELECT bucket, COUNT(*) FROM ranked GROUP BY 1;
-- Then join `ranked` to the feature matrix on (entity_id, as_of_date) and
-- compute AVG(feature) GROUP BY bucket. Build the final table in Python/pandas:
-- fastest path is to export ranked + features as parquet and compute in pandas.
