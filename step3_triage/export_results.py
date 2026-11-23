"""Export triage model results to an Excel workbook or CSVs."""
import argparse
import os
import re
import yaml
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine.url import URL
from triage.util.db import create_engine

DB_CONFIG_PATH = os.path.expanduser('~/database.yaml')
METRICS = ('precision@', 'recall@')


def get_engine():
    with open(DB_CONFIG_PATH) as f:
        db = yaml.safe_load(f)
    url = URL.create(
        'postgresql+psycopg2',
        host=db['host'], username=db['user'], password=db['pass'],
        port=db['port'], database='johnson_county_ddj_jail_mh2',
    )
    return create_engine(url, connect_args={'options': '-c enable_nestloop=off'})


def build_scope(model_comments, experiment_hashes):
    parts, params = [], {}
    if experiment_hashes:
        parts.append("em.experiment_hash = ANY(:exp_hashes)")
        params['exp_hashes'] = list(experiment_hashes)
    if model_comments:
        subs = []
        for i, c in enumerate(model_comments):
            key = f'mc_{i}'
            subs.append(f"m.model_comment ILIKE :{key}")
            params[key] = f'%{c}%'
        parts.append('(' + ' OR '.join(subs) + ')')
    return (' AND '.join(parts) if parts else 'TRUE'), params


def fetch_model_groups(engine, where, params):
    q = text(f"""
        SELECT DISTINCT
               m.model_group_id,
               m.model_type,
               m.hyperparameters::text AS hyperparameters,
               m.model_comment
        FROM triage_metadata.models m
        JOIN triage_metadata.experiment_models em USING (model_hash)
        WHERE {where}
        ORDER BY m.model_group_id
    """)
    return pd.read_sql(q, engine, params=params)


def fetch_by_split(engine, where, params):
    q = text(f"""
        SELECT m.model_id,
               m.model_group_id,
               m.model_type,
               m.hyperparameters::text AS hyperparameters,
               m.model_comment,
               m.train_end_time::date AS train_end_time,
               e.metric,
               e.parameter,
               e.stochastic_value AS metric_value,
               e.num_labeled_examples,
               e.num_positive_labels
        FROM triage_metadata.models m
        JOIN triage_metadata.experiment_models em USING (model_hash)
        JOIN test_results.evaluations e ON e.model_id = m.model_id
        WHERE {where}
          AND e.subset_hash = ''
          AND e.metric IN :metrics
        ORDER BY m.model_group_id, m.train_end_time, e.metric, e.parameter
    """).bindparams(metrics=METRICS)
    return pd.read_sql(q, engine, params=params)


def summarize(by_split):
    g = by_split.groupby(
        ['model_group_id', 'model_type', 'hyperparameters',
         'model_comment', 'metric', 'parameter'],
        dropna=False,
    )['metric_value']
    out = g.agg(['mean', 'std', 'min', 'max', 'count']).reset_index()
    return out.rename(columns={
        'mean': 'mean_value', 'std': 'sd_value',
        'min': 'min_value', 'max': 'max_value', 'count': 'n_splits',
    })


def wide_prec100(by_split):
    sub = by_split[(by_split.metric == 'precision@') & (by_split.parameter == '100_abs')]
    if sub.empty:
        return pd.DataFrame()
    return (
        sub.pivot_table(index='train_end_time',
                        columns='model_group_id',
                        values='metric_value',
                        aggfunc='mean')
           .sort_index()
    )


_SHEET_CLEAN = re.compile(r'[\[\]\*\?\:\\\/]')


def sheet_name(mg_id, model_type):
    short = model_type.rsplit('.', 1)[-1]
    name = f'mg{mg_id}_{short}'
    name = _SHEET_CLEAN.sub('_', name)
    return name[:31]


def write_xlsx(path, groups, by_split, summary, wide):
    print(f'writing workbook to {path}')
    with pd.ExcelWriter(path, engine='openpyxl') as xl:
        summary.to_excel(xl, sheet_name='summary', index=False)
        groups.to_excel(xl, sheet_name='model_groups', index=False)
        if not wide.empty:
            wide.to_excel(xl, sheet_name='prec100_by_date')
        for mg_id, mg_rows in by_split.groupby('model_group_id'):
            mt = mg_rows['model_type'].iloc[0]
            mg_rows.drop(columns=['model_group_id', 'model_type', 'hyperparameters',
                                  'model_comment']) \
                   .to_excel(xl, sheet_name=sheet_name(mg_id, mt), index=False)


def write_csvs(out_dir, prefix, groups, by_split, summary, wide):
    print(f'writing CSVs to {out_dir}')
    groups.to_csv(os.path.join(out_dir, f'{prefix}_model_groups.csv'), index=False)
    by_split.to_csv(os.path.join(out_dir, f'{prefix}_by_split.csv'), index=False)
    summary.to_csv(os.path.join(out_dir, f'{prefix}_summary.csv'), index=False)
    if not wide.empty:
        wide.to_csv(os.path.join(out_dir, f'{prefix}_prec100_by_date_wide.csv'))
    per_mg_dir = os.path.join(out_dir, f'{prefix}_by_model_group')
    os.makedirs(per_mg_dir, exist_ok=True)
    for mg_id, mg_rows in by_split.groupby('model_group_id'):
        mt = mg_rows['model_type'].iloc[0].rsplit('.', 1)[-1]
        fname = f'mg{mg_id}_{mt}.csv'
        mg_rows.to_csv(os.path.join(per_mg_dir, fname), index=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out-dir', default='.')
    ap.add_argument('--prefix', default='results')
    ap.add_argument('--model-comment', action='append', default=[])
    ap.add_argument('--experiment-hash', action='append', default=[])
    ap.add_argument('--format', choices=['xlsx', 'csv', 'both'], default='xlsx')
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    engine = get_engine()
    where, params = build_scope(args.model_comment, args.experiment_hash)

    print('fetching model group metadata from DB')
    groups = fetch_model_groups(engine, where, params)
    print(f'  found {len(groups)} model groups')

    print('fetching per-split evaluations from DB')
    by_split = fetch_by_split(engine, where, params)
    print(f'  pulled {len(by_split):,} rows across {by_split.model_id.nunique()} models')

    print('aggregating across splits')
    summary = summarize(by_split)
    wide = wide_prec100(by_split)

    if args.format in ('xlsx', 'both'):
        write_xlsx(os.path.join(args.out_dir, f'{args.prefix}.xlsx'),
                   groups, by_split, summary, wide)
    if args.format in ('csv', 'both'):
        write_csvs(args.out_dir, args.prefix, groups, by_split, summary, wide)

    print('done')


if __name__ == '__main__':
    main()
