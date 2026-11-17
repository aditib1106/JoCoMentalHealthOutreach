#!/usr/bin/env python
"""
Results over time for the medium-grid run: precision@100 on every validation date, one thin line
per model group (coloured by model type), the base rate (Dummy), the 4 rule baselines, and a dashed
"best case" envelope. Writes results_over_time.png.

Run (repo root, jail_mh2 env):
    pyenv shell jail_mh2
    python step3_triage/plot_over_time.py
    python step3_triage/plot_over_time.py --run 24        # built_in_triage_run id (Afaq's U6 run)
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

DATABASE = "johnson_county_ddj_jail_mh2"
COLORS = {"ScaledLogisticRegression": "#9467bd", "RandomForestClassifier": "#ff7f0e",
          "DecisionTreeClassifier": "#2ca02c", "ExtraTreesClassifier": "#8c564b",
          "AdaBoostClassifier": "#e377c2"}


def plot(df, out):
    """df columns: model_group_id, type, d (date), prec100. Pure function (no DB)."""
    df = df.copy()
    df["d"] = pd.to_datetime(df["d"])
    fig, ax = plt.subplots(figsize=(11, 6))
    seen = set()
    for (g, t), sub in df.groupby(["model_group_id", "type"]):
        if t in COLORS:
            sub = sub.sort_values("d")
            lab = t if t not in seen else None
            seen.add(t)
            ax.plot(sub["d"], sub["prec100"], color=COLORS[t], lw=0.6, alpha=0.35, label=lab)
    ml = df[df["type"].isin(COLORS)]
    best = ml.groupby("d")["prec100"].max()
    ax.plot(best.index, best.values, "k--", lw=1.5, label="Best case (max over models)")
    dummy = df[df["type"] == "DummyClassifier"].groupby("d")["prec100"].mean()
    ax.plot(dummy.index, dummy.values, color="#1f77b4", lw=2.5, label="Base rate (Dummy)")
    base = df[df["type"] == "BaselineRankMultiFeature"]
    for i, (g, sub) in enumerate(sorted(base.groupby("model_group_id"))):
        sub = sub.sort_values("d")
        ax.plot(sub["d"], sub["prec100"], color="#d62728", lw=1.8, alpha=0.5 + 0.12 * i,
                label="Rule baselines" if i == 0 else None)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Validation as-of date")
    ax.set_ylabel("Precision at top 100")
    ax.set_title("Precision@100 over time: all model groups, base rate and baselines")
    ax.grid(alpha=0.3)
    ax.legend(loc="lower left", fontsize=9, ncol=2)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    print("saved", out)


def main():
    import sqlalchemy as sa
    import yaml
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=int, default=24, help="built_in_triage_run id")
    ap.add_argument("--out", default="results_over_time.png")
    a = ap.parse_args()
    with open(Path.home() / "database.yaml") as fd:
        cfg = yaml.safe_load(fd)
    url = sa.engine.url.URL.create("postgresql+psycopg2", host=cfg["host"], username=cfg["user"],
                                   password=cfg["pass"], port=cfg["port"], database=DATABASE)
    eng = sa.create_engine(url)
    q = sa.text("""
        SELECT m.model_group_id, split_part(m.model_type, '.', -1) AS type,
               e.evaluation_start_time::date AS d, e.stochastic_value AS prec100
        FROM test_results.evaluations e
        JOIN triage_metadata.models m USING (model_id)
        WHERE m.built_in_triage_run = :run
          AND e.metric = 'precision@' AND e.parameter = '100_abs'""")
    with eng.connect() as c:
        df = pd.read_sql(q, c, params={"run": a.run})
    print(df.groupby("type").model_group_id.nunique())
    plot(df, a.out)


if __name__ == "__main__":
    main()
