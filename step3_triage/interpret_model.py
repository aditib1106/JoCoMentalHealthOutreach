#!/usr/bin/env python
"""
Project Update 7 (understanding the model) for Jail MH 2.

For the model with the highest average precision@100 across validation sets, on the most
recent validation set, this produces:
  * interp_prk.png         PR-k curve
  * interp_importance.png  top built-in feature importances
  * interp_crosstab.csv    every feature: mean in the top k vs the rest
and prints the selection table, the top-10 cross-tab and the top importances.

Run from the repo root in the jail_mh2 env:
    pyenv shell jail_mh2
    python step3_triage/interpret_model.py                  # auto-pick best ML group
    python step3_triage/interpret_model.py --group 15
    python step3_triage/interpret_model.py --model-id 416   # force a model with saved predictions

Predictions must be saved for the model (see run_prk_rerun.py); the validation matrix is read
from the Triage project folder.
"""
import argparse
import glob
import os
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DATABASE = "johnson_county_ddj_jail_mh2"          # same hardcoded db as run.py
FEATURE_RE = re.compile(r"^(jailrel|jail|mhsvc|mhcall|ambbeh|amb|risk)_entity_id_")
BASELINE_HINTS = ("Dummy", "baselines")
RED, BLUE = "#d62728", "#1f77b4"


# ------------------------------------------------------------------ pure functions
def crosstab(feats: pd.DataFrame, top_mask: pd.Series) -> pd.DataFrame:
    """Mean of each feature in the top group vs the rest, ranked by standardized difference.

    Ranking uses the standardized mean difference (difference / pooled std) so features on
    different scales (counts, days, flags) are comparable. The plain difference and ratio of
    means are reported alongside.
    """
    top, rest = feats[top_mask], feats[~top_mask]
    m_top, m_rest = top.mean(), rest.mean()
    pooled = np.sqrt((top.var(ddof=0) + rest.var(ddof=0)) / 2)
    smd = (m_top - m_rest) / pooled.replace(0, np.nan)
    ratio = (m_top / m_rest.replace(0, np.nan))
    out = pd.DataFrame({"mean_top": m_top, "mean_rest": m_rest, "diff": m_top - m_rest,
                        "ratio": ratio, "std_diff": smd})
    out = out.dropna(subset=["std_diff"])
    return out.reindex(out["std_diff"].abs().sort_values(ascending=False).index)


def curve(rank: np.ndarray, label: np.ndarray):
    order = np.argsort(rank, kind="mergesort")
    y = label[order].astype(float)
    n, pos = len(y), y.sum()
    tp = np.cumsum(y)
    k = np.arange(1, n + 1)
    return k / n * 100, tp / k * 100, tp / pos * 100, n, int(pos)


def plot_prk(rank, label, date, title, out, k_abs=100):
    x, prec, rec, n, pos = curve(np.asarray(rank), np.asarray(label))
    base = pos / n * 100
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    ax2 = ax.twinx()
    ax.plot(x, prec, color=RED, lw=2, label="Precision")
    ax.axhline(base, color="#999999", ls="--", lw=1.5, label=f"Base rate ({base:.1f}%)")
    ax2.plot(x, rec, color=BLUE, lw=2, label="Recall")
    k = min(k_abs, n)
    x100, p100 = k / n * 100, prec[k - 1]
    ax.axvline(x100, color="black", ls=":", lw=1)
    ax.scatter([x100], [p100], color="black", zorder=5)
    ax.annotate(f"top {k}: {p100:.0f}% precision, {rec[k - 1]:.0f}% recall", (x100, p100),
                xytext=(x100 + 8, min(p100 + 15, 92)), fontsize=10,
                arrowprops=dict(arrowstyle="-", color="black", lw=0.8))
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax2.set_ylim(0, 100)
    ax.set_xlabel(f"Percent of population (k), validation {date}")
    ax.set_ylabel("Precision (%)", color=RED); ax2.set_ylabel("Recall (%)", color=BLUE)
    ax.tick_params(axis="y", colors=RED); ax2.tick_params(axis="y", colors=BLUE)
    ax.grid(alpha=0.3)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="center right", fontsize=9)
    ax.set_title(f"{title}\ncohort N={n}, positives={pos}", fontsize=11)
    fig.tight_layout()
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("saved", out)
    return p100


def plot_importance(imp: pd.DataFrame, title, out, k=10):
    top = imp.reindex(imp["feature_importance"].abs().sort_values(ascending=False).index).head(k)
    top = top.iloc[::-1]
    colors = [RED if v < 0 else BLUE for v in top["feature_importance"]]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.barh(top["feature"], top["feature_importance"], color=colors)
    ax.set_xlabel("Built-in importance (blue: positive, red: negative)")
    ax.set_title(title, fontsize=11)
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("saved", out)


# ------------------------------------------------------------------ database / files
def get_engine():
    import sqlalchemy as sa
    import yaml
    with open(Path.home() / "database.yaml") as fd:
        cfg = yaml.safe_load(fd)
    url = sa.engine.url.URL.create("postgresql+psycopg2", host=cfg["host"], username=cfg["user"],
                                   password=cfg["pass"], port=cfg["port"], database=DATABASE)
    return sa.create_engine(url)


def read_matrix(path):
    p = str(path)
    if p.endswith((".csv.gz", ".csv")):
        df = pd.read_csv(p)
    elif p.endswith(".parquet"):
        df = pd.read_parquet(p)
    elif p.endswith(".h5"):
        df = pd.read_hdf(p)
    else:
        raise ValueError(f"don't know how to read {p}")
    if "entity_id" not in df.columns:
        df = df.reset_index()
    return df


def find_matrix(uuid, extra_dirs):
    repo = Path(__file__).resolve().parent.parent
    dirs = [repo / "triage_output_prk" / "matrices", repo / "triage_output" / "matrices"]
    dirs += [Path(d) for d in extra_dirs]
    dirs += [Path(d) for d in glob.glob("/class/groups/jail_mh2/triage_runs_v2/*/matrices")]
    for d in dirs:
        hits = sorted(glob.glob(str(d / f"{uuid}*")))
        if hits:
            return hits[0]
    raise SystemExit(f"Could not find matrix {uuid} in {[str(d) for d in dirs[:3]]} ... "
                     "pass --matrix-dir with the folder that holds it.")


def main():
    import sqlalchemy as sa
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2018-06-01", help="most recent validation as-of date")
    ap.add_argument("--group", type=int, default=None, help="model_group_id (default: best ML)")
    ap.add_argument("--model-id", type=int, default=None, help="use this model_id directly")
    ap.add_argument("--k", type=int, default=100, help="top k people (absolute)")
    ap.add_argument("--matrix-dir", action="append", default=[])
    ap.add_argument("--out-prefix", default="interp")
    args = ap.parse_args()

    eng = get_engine()
    with eng.connect() as c:
        def q(sql, **p):
            return pd.read_sql(sa.text(sql), c, params=p)

        # ---------------------------------------------- 1. which model has the best average?
        ev_cols = set(q("select column_name from information_schema.columns "
                        "where table_schema='test_results' and table_name='evaluations'")
                      ["column_name"])
        val = next(x for x in ("stochastic_value", "value", "best_value") if x in ev_cols)
        sel = q(f"""
            select m.model_group_id as grp, min(m.model_type) as model_type,
                   round(avg(e.{val})::numeric, 3) as avg_p100, count(*) as n_splits
            from triage_metadata.models m
            join test_results.evaluations e on e.model_id = m.model_id
             and e.metric = 'precision@' and e.parameter = '100_abs'
            group by 1 order by 3 desc limit 40""")
        sel["model_type"] = sel["model_type"].str.split(".").str[-1]
        print("\n=== models ranked by average precision@100 across validation sets ===")
        print(sel.to_string(index=False))
        ml = sel[~sel["model_type"].str.contains("Dummy|Baseline")]
        full = ml[ml["n_splits"] == ml["n_splits"].max()]   # scored on every validation date
        print(f"(choosing among ML groups scored on all {int(ml['n_splits'].max())} dates; "
              "partially scored groups can't be evaluated on the last date)")
        ml = full
        best = int(ml.iloc[0]["grp"])
        group = args.group or best
        print(f"\nhighest-average ML group: {best}  (using group {group})")
        hp = q("select hyperparameters, model_type from triage_metadata.model_groups "
               "where model_group_id = :g", g=group)
        print("hyperparameters:", hp.iloc[0]["hyperparameters"] if len(hp) else "?")

        # ---------------------------------------------- 2. a model with saved predictions
        if args.model_id:
            model_id = args.model_id
        else:
            cand = q("select model_id, model_group_id, model_type from triage_metadata.models "
                     "where train_end_time::date = cast(:d as date)", d=args.date)
            counts = q("select model_id, count(*) as n from test_results.predictions "
                       "where model_id = any(:ids) and as_of_date = cast(:d as timestamp) "
                       "group by 1", ids=[int(x) for x in cand.model_id], d=args.date)
            have = cand.merge(counts, on="model_id")
            mine = have[have.model_group_id == group]
            if mine.empty:
                mtype = ml[ml.grp == group].iloc[0]["model_type"]
                same = have[have.model_type.str.endswith(mtype)]
                print(f"\n!! group {group} has no saved predictions on {args.date}.")
                print("   models that do:\n", have.to_string(index=False))
                if len(same) != 1:
                    raise SystemExit("Pick one and rerun with --model-id <id> (same settings "
                                     "as the selected group), or rerun it with "
                                     "save_predictions=True.")
                mine = same
                g2 = int(mine.iloc[0].model_group_id)
                hp2 = q("select hyperparameters from triage_metadata.model_groups "
                        "where model_group_id = :g", g=g2)
                print(f"   using refit group {g2}; hyperparameters: "
                      f"{hp2.iloc[0]['hyperparameters'] if len(hp2) else '?'}")
            model_id = int(mine.iloc[0].model_id)
        print("\nmodel_id used:", model_id)

        # ---------------------------------------------- 3. predictions + validation matrix
        pcols = set(q("select column_name from information_schema.columns "
                      "where table_schema='test_results' and table_name='predictions'")
                    ["column_name"])
        rk = "rank_abs_no_ties" if "rank_abs_no_ties" in pcols else (
            "rank_abs" if "rank_abs" in pcols else "NULL")
        pred = q(f"select entity_id, score, label_value as label, {rk} as rk, matrix_uuid "
                 "from test_results.predictions where model_id = :m "
                 "and as_of_date = cast(:d as timestamp)", m=model_id, d=args.date)
        if pred.empty:
            raise SystemExit("No predictions for that model/date.")
        if pred.rk.isna().all():
            pred["rk"] = pred.score.rank(ascending=False, method="first")
        uuid = pred.matrix_uuid.iloc[0]
        mat_path = find_matrix(uuid, args.matrix_dir)
        print("matrix:", mat_path)
        mat = read_matrix(mat_path)
        skip = {"entity_id", "as_of_date", "label", "label_value", "outcome"}
        feats = [x for x in mat.select_dtypes("number").columns if x not in skip]
        data = pred.merge(mat[["entity_id"] + feats], on="entity_id", how="inner")
        print(f"validation rows: {len(data)} (predictions {len(pred)}), features: {len(feats)}")

        # ---------------------------------------------- 4. PR-k
        title = f"Model {model_id} (group {group}) on validation {args.date}"
        p100 = plot_prk(data.rk, data.label, args.date, title, f"{args.out_prefix}_prk.png",
                        args.k)
        print(f"precision@{args.k} = {p100:.1f}%")

        # ---------------------------------------------- 5. cross-tab
        top_mask = data.rk <= args.k
        ct = crosstab(data[feats].astype(float), top_mask)
        ct.to_csv(f"{args.out_prefix}_crosstab.csv")
        n_top = int(top_mask.sum())
        print(f"\n=== cross-tab: top {n_top} ({n_top / len(data) * 100:.1f}%) vs the other "
              f"{len(data) - n_top} ===")
        print("ranked by standardized difference (diff / pooled std); ratio = top mean / rest mean")
        show = ct.head(10).copy()
        show.index.name = "feature"
        with pd.option_context("display.float_format", lambda v: f"{v:,.3f}",
                               "display.width", 200, "display.max_colwidth", 60):
            print(show.reset_index().to_string(index=False))

        # ---------------------------------------------- 6. built-in importances
        imp = q("select feature, feature_importance from train_results.feature_importances "
                "where model_id = :m", m=model_id)
        print(f"\n=== built-in importances, model {model_id}: {len(imp)} features, "
              f"{int((imp.feature_importance.abs() > 0).sum())} non-zero ===")
        topimp = imp.reindex(imp.feature_importance.abs().sort_values(ascending=False).index)
        print(topimp.head(15).to_string(index=False))
        plot_importance(imp, f"Top 10 built-in importances: model {model_id} (group {group})",
                        f"{args.out_prefix}_importance.png")

        both = set(ct.head(10).index) & set(topimp.head(15).feature)
        print("\nfeatures in BOTH the top-10 cross-tab and the top-15 importances:", sorted(both))


if __name__ == "__main__":
    main()
