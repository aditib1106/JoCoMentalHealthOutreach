"""Update 8 fairness audit, computed directly from stored predictions.

No triage re-run. Reads test_results.predictions for the models that have
per-person predictions on the most recent validation list, joins race/sex
from semantic.bookings, and computes precision@100, TPR and FDR per group
and the disparity vs the reference group. Everything comes from one top-100
list per model, so the numbers are self-consistent and easy to check by hand.

TPR_group = (positives in top100 AND group) / (all positives in group)
FDR_group = (negatives in top100 AND group) / (all in top100 AND group)
disparity = group_metric / reference_group_metric
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

MODEL_COMMENTS = ('jail_mh2_update7_focus', 'jail_mh2_u5_mini_prk')
EVAL_DATE = '2018-06-01'
TOP_N = 100
OUT_DIR = '/class/groups/jail_mh2/exports/fairness'
# (attribute, protected value, reference value, label)
PANELS = [('race', 'B', 'W', 'Black vs White'),
          ('sex', 'FEMALE', 'MALE', 'Female vs Male')]


def get_engine():
    with open(os.path.expanduser('~/database.yaml')) as f:
        db = yaml.safe_load(f)
    url = URL.create('postgresql+psycopg2', host=db['host'], username=db['user'],
                     password=db['pass'], port=db['port'],
                     database='johnson_county_ddj_jail_mh2')
    return create_engine(url, connect_args={'options': '-c enable_nestloop=off'})


def load_predictions(engine):
    q = text("""
        SELECT m.model_group_id,
               split_part(m.model_type, '.', 4) AS model_type,
               m.model_type AS full_type,
               p.entity_id, p.score, p.label_value, p.rank_abs_no_ties
        FROM test_results.predictions p
        JOIN triage_metadata.models m USING(model_id)
        WHERE m.model_comment = ANY(:mcs) AND p.as_of_date = :d
    """)
    return pd.read_sql(q, engine, params={'mcs': list(MODEL_COMMENTS), 'd': EVAL_DATE})


def load_demographics(engine):
    # One race/sex per person: the most recent booking on or before the list date.
    q = text("""
        SELECT DISTINCT ON (entity_id) entity_id, race, sex
        FROM semantic.bookings
        WHERE booking_date <= :d AND entity_id IS NOT NULL
        ORDER BY entity_id, booking_date DESC
    """)
    return pd.read_sql(q, engine, params={'d': EVAL_DATE})


def disparities(preds, demo):
    df = preds.merge(demo, on='entity_id', how='left')
    rows = []
    for (gid, mtype, ftype), g in df.groupby(['model_group_id', 'model_type', 'full_type']):
        top = g[g.rank_abs_no_ties <= TOP_N]
        prec100 = top.label_value.mean()
        rec = {'model_group_id': gid, 'model_type': mtype, 'full_type': ftype,
               'precision_at_100': prec100}
        for attr, prot, ref, _ in PANELS:
            for val in (prot, ref):
                grp = g[g[attr] == val]
                top_grp = top[top[attr] == val]
                pos = (grp.label_value == 1).sum()
                tpr = (top_grp.label_value == 1).sum() / pos if pos else float('nan')
                fdr = (top_grp.label_value == 0).sum() / len(top_grp) if len(top_grp) else float('nan')
                rec[f'{attr}_{val}_tpr'] = tpr
                rec[f'{attr}_{val}_fdr'] = fdr
                rec[f'{attr}_{val}_n_top100'] = len(top_grp)
            # disparity = protected / reference
            rec[f'{attr}_tpr_disparity'] = rec[f'{attr}_{prot}_tpr'] / rec[f'{attr}_{ref}_tpr']
            rec[f'{attr}_fdr_disparity'] = rec[f'{attr}_{prot}_fdr'] / rec[f'{attr}_{ref}_fdr']
        rows.append(rec)
    return pd.DataFrame(rows).sort_values('precision_at_100', ascending=False)


def scatter(res, ycol, title, ylabel, path):
    fig, ax = plt.subplots(figsize=(7, 5))
    is_rf = res.full_type.str.contains('RandomForest')
    is_lr = res.full_type.str.contains('LogisticRegression')
    is_dummy = res.full_type.str.contains('Dummy')
    is_base = ~is_rf & ~is_lr & ~is_dummy
    # Dummy excluded from the disparity axis: constant score -> random top 100.
    for mask, c, m, lbl in [(is_lr, '#1f77b4', 'o', 'Logistic regression'),
                            (is_rf, '#d62728', '^', 'Random forest'),
                            (is_base, '#888888', 's', 'Baseline')]:
        sub = res[mask]
        if len(sub):
            ax.scatter(sub.precision_at_100, sub[ycol], c=c, marker=m, s=70, label=lbl)
    for _, r in res[~is_dummy].iterrows():
        ax.annotate(f"mg{int(r.model_group_id)}", (r.precision_at_100, r[ycol]),
                    textcoords='offset points', xytext=(6, 4), fontsize=8)
    ax.axhline(1.0, ls='--', c='k', lw=1)
    ax.set_xlabel(f'precision@{TOP_N} (validation list {EVAL_DATE})')
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
    res = disparities(load_predictions(engine), load_demographics(engine))
    csv = os.path.join(OUT_DIR, 'disparities.csv')
    res.to_csv(csv, index=False)
    print(f'wrote {csv}  ({len(res)} models)')
    # exclude dummy from the disparity plots
    plot_res = res[~res.full_type.str.contains('Dummy')]
    for attr, prot, ref, label in PANELS:
        scatter(plot_res, f'{attr}_tpr_disparity', f'TPR (recall) disparity, {label}',
                f'TPR disparity ({prot} / {ref})',
                os.path.join(OUT_DIR, f'tpr_disparity_{attr}.png'))
        scatter(plot_res, f'{attr}_fdr_disparity', f'FDR disparity, {label}',
                f'FDR disparity ({prot} / {ref})',
                os.path.join(OUT_DIR, f'fdr_disparity_{attr}.png'))


if __name__ == '__main__':
    main()
