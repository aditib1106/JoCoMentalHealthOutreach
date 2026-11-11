#!/usr/bin/env python
"""
Three-panel PR-k figure for slide 18/102: Baseline 4, logistic regression, random forest,
all on one validation date (default 2018-06-01), from test_results.predictions.

Needs predictions saved by step3_triage/run_prk_rerun.py.

Usage (repo root, jail_mh2 env):
    pyenv shell jail_mh2
    python step3_triage/plot_prk.py
    python step3_triage/plot_prk.py --model-ids 414,415,416,417      # if auto-detect fails
Writes prk_3panel.png next to where you run it, and prints precision@100 per model so
you can check it against the audition plot.
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DATABASE = "johnson_county_ddj_jail_mh2"      # same hardcoded db as run.py
EXPERIMENT_HASH = "bc404bff7f6a7ace96b76036b781297a"   # printed by run_prk_rerun.py

PANELS = [  # (model_type suffix, title)
    ("BaselineRankMultiFeature", "Baseline 4 (rank by prior new-arrest bookings)"),
    ("ScaledLogisticRegression", "Logistic regression (C=1, L1)"),
    ("RandomForestClassifier", "Random forest (50 trees, depth 5)"),
]
RED, BLUE, GREY = "#d62728", "#1f77b4", "#999999"


def curve(df):
    """df has columns rk (rank, 1 = highest risk) and label. Returns x%, precision%, recall%."""
    d = df.sort_values("rk", kind="mergesort")
    y = d["label"].to_numpy(dtype=float)
    n, pos = len(y), y.sum()
    tp = np.cumsum(y)
    k = np.arange(1, n + 1)
    return k / n * 100, tp / k * 100, tp / pos * 100, n, int(pos)


def plot_panels(data, date, out):
    """data: list of (title, DataFrame[rk, label]). Pure function, no DB."""
    fig, axes = plt.subplots(1, len(data), figsize=(7 * len(data), 5.6))
    axes = np.atleast_1d(axes)
    n_all = pos_all = None
    for ax, (title, df) in zip(axes, data):
        x, prec, rec, n, pos = curve(df)
        n_all, pos_all = n, pos
        base = pos / n * 100
        ax2 = ax.twinx()
        ax.plot(x, prec, color=RED, lw=2, label="Precision")
        ax.axhline(base, color=GREY, ls="--", lw=1.5, label=f"Base rate ({base:.1f}%)")
        ax2.plot(x, rec, color=BLUE, lw=2, label="Recall")
        # mark JCMHC capacity: the top 100 people
        k100 = min(100, n)
        x100, p100 = k100 / n * 100, prec[k100 - 1]
        ax.axvline(x100, color="black", lw=1, ls=":")
        ax.scatter([x100], [p100], color="black", zorder=5)
        ax.annotate(f"top 100: {p100:.0f}% precision", (x100, p100),
                    xytext=(x100 + 6, min(p100 + 18, 95)), fontsize=10,
                    arrowprops=dict(arrowstyle="-", color="black", lw=0.8))
        ax.set_title(title, fontsize=12)
        ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax2.set_ylim(0, 100)
        ax.set_xlabel(f"Percent of population (k), validation {date}")
        ax.set_ylabel("Precision (%)", color=RED); ax2.set_ylabel("Recall (%)", color=BLUE)
        ax.tick_params(axis="y", colors=RED); ax2.tick_params(axis="y", colors=BLUE)
        ax.grid(alpha=0.3)
        h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, loc="center right", fontsize=9)
    fig.suptitle(f"Jail MH 2: PR-k on validation {date}  (cohort N={n_all}, positives={pos_all})",
                 fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print("saved", out)


def get_engine():
    import sqlalchemy, yaml
    with open(Path.home() / "database.yaml") as fd:
        cfg = yaml.safe_load(fd)
    url = sqlalchemy.engine.url.URL.create(
        "postgresql+psycopg2", host=cfg["host"], username=cfg["user"],
        database=DATABASE, password=cfg["pass"], port=cfg["port"])
    return sqlalchemy.create_engine(url)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--date", default="2018-06-01")
    p.add_argument("--experiment-hash", default=EXPERIMENT_HASH)
    p.add_argument("--model-ids", default=None, help="comma-separated, overrides auto-detect")
    p.add_argument("--out", default="prk_3panel.png")
    args = p.parse_args()

    from sqlalchemy import text
    eng = get_engine()
    with eng.connect() as c:
        if args.model_ids:
            ids = [int(x) for x in args.model_ids.split(",")]
            models = pd.read_sql(text(
                "SELECT model_id, model_group_id, model_type FROM triage_metadata.models "
                "WHERE model_id = ANY(:ids)"), c, params={"ids": ids})
        else:
            models = pd.read_sql(text(
                "SELECT m.model_id, m.model_group_id, m.model_type "
                "FROM triage_metadata.models m "
                "JOIN triage_metadata.experiment_models em ON em.model_hash = m.model_hash "
                "WHERE em.experiment_hash = :h"), c, params={"h": args.experiment_hash})
        if models.empty:
            raise SystemExit("No models found. Pass --model-ids from the DBeaver query.")
        print(models.to_string(index=False))

        cols = set(pd.read_sql(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='test_results' AND table_name='predictions'"), c)["column_name"])
        rank_col = next((r for r in ("rank_abs_no_ties", "rank_abs") if r in cols), None)
        print("rank column:", rank_col)

        data = []
        for suffix, title in PANELS:
            hit = models[models.model_type.str.endswith(suffix)]
            if hit.empty:
                print(f"!! no {suffix} model found; skipping that panel")
                continue
            mid, gid = int(hit.iloc[0].model_id), int(hit.iloc[0].model_group_id)
            rank_sql = rank_col if rank_col else "NULL"
            df = pd.read_sql(text(
                f"SELECT entity_id, score, label_value AS label, {rank_sql} AS rk "
                "FROM test_results.predictions "
                "WHERE model_id = :m AND as_of_date = CAST(:d AS timestamp)"),
                c, params={"m": mid, "d": args.date})
            if df.empty:
                print(f"!! model {mid} has no predictions on {args.date}; skipping")
                continue
            if df.rk.isna().all():                     # fall back to score order
                df["rk"] = df.score.rank(ascending=False, method="first")
            df = df.dropna(subset=["label"])
            top = df.sort_values("rk").head(100)
            print(f"{suffix:28s} model {mid:>5} group {gid:>3}  N={len(df)}  "
                  f"precision@100 = {top['label'].mean():.3f}")
            data.append((title, df))
    if not data:
        raise SystemExit("Nothing to plot.")
    plot_panels(data, args.date, args.out)


if __name__ == "__main__":
    main()
