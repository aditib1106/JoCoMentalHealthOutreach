"""Four fairness-vs-performance scatter plots for the Update 7 RF run.

Reads test_results.aequitas (populated by run_bias_afaqk.py) for the last
validation list and plots TPR and FDR disparity against precision@100 for
Black/White and Female/Male. y=1 is parity; further right is more precise.
"""
import os
import yaml
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sqlalchemy import text
from sqlalchemy.engine.url import URL
from triage.util.db import create_engine

MODEL_COMMENT = 'jail_mh2_update7_rf_afaqk'
EVAL_DATE = '2018-06-01'
THRESHOLD = '100_abs'
OUT_DIR = '/class/groups/jail_mh2/step3_triage/update8_afaqk/exports'
PANELS = [('race', 'B', 'W', 'Black vs White'),
          ('sex', 'FEMALE', 'MALE', 'Female vs Male')]


def get_engine():
    with open(os.path.expanduser('~/database.yaml')) as f:
        db = yaml.safe_load(f)
    url = URL.create('postgresql+psycopg2', host=db['host'], username=db['user'],
                     password=db['pass'], port=db['port'],
                     database='johnson_county_ddj_jail_mh2')
    return create_engine(url, connect_args={'options': '-c enable_nestloop=off'})


def load(engine, attribute_name, attribute_value):
    q = text("""
        SELECT m.model_group_id,
               m.model_type,
               a.tpr, a.tpr_disparity, a.fdr, a.fdr_disparity, a.group_size,
               e.stochastic_value AS precision_at_100
        FROM test_results.aequitas a
        JOIN triage_metadata.models m ON m.model_id = a.model_id
        JOIN test_results.evaluations e
             ON e.model_id = a.model_id
            AND e.metric = 'precision@' AND e.parameter = :thr
            AND e.subset_hash = ''
            AND e.evaluation_start_time = :eval_date
        WHERE m.model_comment = :mc
          AND a.parameter = :thr
          AND a.attribute_name = :attr
          AND a.attribute_value = :val
    """)
    return pd.read_sql(q, engine, params={
        'mc': MODEL_COMMENT, 'thr': THRESHOLD, 'eval_date': EVAL_DATE,
        'attr': attribute_name, 'val': attribute_value})


def scatter(df, ycol, title, ylabel, path):
    fig, ax = plt.subplots(figsize=(7, 5))
    # Dummy excluded: constant score -> random top-100, disparity is a tie-break artifact.
    plot_df = df[~df.model_type.str.contains('Dummy')]
    is_rf = plot_df.model_type.str.contains('RandomForest')
    for mask, c, m, lbl in [(is_rf, '#d62728', '^', 'Random forest'),
                            (~is_rf, '#888888', 's', 'Baseline')]:
        sub = plot_df[mask]
        if len(sub):
            ax.scatter(sub.precision_at_100, sub[ycol], c=c, marker=m, s=70, label=lbl)
    for _, r in plot_df.iterrows():
        ax.annotate(f"mg{int(r.model_group_id)}", (r.precision_at_100, r[ycol]),
                    textcoords='offset points', xytext=(6, 4), fontsize=8)
    ax.axhline(1.0, ls='--', c='k', lw=1)
    ax.set_xlabel(f'precision@100 (validation list {EVAL_DATE})')
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(loc='best', fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f'wrote {path}')


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    engine = get_engine()
    full = []
    for attr, prot, ref, label in PANELS:
        df = load(engine, attr, prot)
        if df.empty:
            print(f'NO aequitas rows for {attr}={prot} on {EVAL_DATE} -- run run_bias_afaqk.py first')
            continue
        df['attribute'] = attr
        df['protected_value'] = prot
        df['reference_value'] = ref
        full.append(df)
        scatter(df, 'tpr_disparity', f'TPR (recall) disparity, {label}',
                f'TPR disparity ({prot} / {ref})',
                os.path.join(OUT_DIR, f'tpr_disparity_{attr}.png'))
        scatter(df, 'fdr_disparity', f'FDR disparity, {label}',
                f'FDR disparity ({prot} / {ref})',
                os.path.join(OUT_DIR, f'fdr_disparity_{attr}.png'))
    if full:
        pd.concat(full).to_csv(os.path.join(OUT_DIR, 'disparities.csv'), index=False)
        print(f'wrote {OUT_DIR}/disparities.csv')


if __name__ == '__main__':
    main()
