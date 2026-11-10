#!/usr/bin/env python
"""
Audition for Jail MH 2, Project Update 5.

Produces the "results over time" plots for slide 16 (all model groups across every
validation split, for precision@100, with the base rate and baselines marked).

Adapted from the course notebook techhelp/models_over_time.ipynb, with four fixes
that are needed on the class server (see NOTES at the bottom).

Usage, from the repo root with the jail_mh2 env active:

    pyenv shell jail_mh2
    python step3_triage/run_audition.py --list-runs       # see available runs, pick one
    python step3_triage/run_audition.py --run-hash <hash>
    python step3_triage/run_audition.py                   # uses the most recent run

Writes: audition_over_time_1.png, audition_over_time_2.png (and more if audition
draws more figures) next to wherever you run it.
"""
import argparse
import getpass
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")          # headless: no display on the class server
import matplotlib.pyplot as plt
import sqlalchemy
import yaml

# ---------------------------------------------------------------- connection

def get_engine(db_config_path=None, database="johnson_county_ddj_jail_mh2", role=None):
    """Mirror step3_triage/run.py exactly.

    IMPORTANT: run.py reads ~/database.yaml for host/user/pass/port but HARDCODES
    database='johnson_county_ddj_jail_mh2' and ignores the file's `db:` key (which
    says group_students) and its `role:` key. Triage therefore wrote every result to
    johnson_county_ddj_jail_mh2. Connecting to group_students instead gives
    "permission denied for schema triage_metadata", which looks like a grant problem
    but is just the wrong database.
    """
    opts = "-c enable_nestloop=off"           # remote foreign tables have no stats
    if db_config_path and Path(db_config_path).exists():
        with open(db_config_path) as fd:
            cfg = yaml.safe_load(fd)          # FIX: safe_load, not yaml.load(fd)
        # role: if database.yaml names a shared team role, adopt it on connect so
        # objects a teammate created under that role are reachable.
        role = role or cfg.get("role")
        url = sqlalchemy.engine.url.URL.create(   # FIX: .create(), and 'postgresql'
            "postgresql+psycopg2",
            host=cfg["host"],
            username=cfg["user"],
            database=database,                # NOT cfg["db"] - see docstring
            password=cfg["pass"],
            port=cfg["port"],
        )
    else:
        user = os.environ.get("PGUSER") or getpass.getuser()
        host = os.environ.get("PGHOST", "database.mlpolicylab.dssg.io")
        port = os.environ.get("PGPORT", "5432")
        url = f"postgresql+psycopg2://{user}@{host}:{port}/{database}"
    if role:
        opts += f" -c role={role}"
    return sqlalchemy.create_engine(
        url, poolclass=sqlalchemy.pool.QueuePool, connect_args={"options": opts}
    )


def list_runs(engine):
    q = """
        SELECT run_hash, start_time, git_hash, experiment_class_path
        FROM triage_metadata.triage_runs
        ORDER BY start_time DESC
        LIMIT 15
    """
    with engine.connect() as c:
        for row in c.exec_driver_sql(q):
            print(row)


def latest_run_hash(engine):
    q = """
        SELECT run_hash FROM triage_metadata.triage_runs
        ORDER BY start_time DESC LIMIT 1
    """
    with engine.connect() as c:
        return c.exec_driver_sql(q).scalar()


# ---------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db-config", default=str(Path.home() / "database.yaml"))
    p.add_argument("--database", default="johnson_county_ddj_jail_mh2",
                   help="same database run.py hardcodes; NOT the db: key in database.yaml")
    p.add_argument("--role", default=None,
                   help="postgres role to SET on connect; defaults to role: in database.yaml")
    p.add_argument("--no-role", action="store_true", help="ignore the role: key entirely")
    p.add_argument("--model-groups", default=None,
                   help="comma-separated model_group_ids, e.g. 9,10,11,12,13,14,15,16,17,19. "
                        "Use this when run_hash is not the key models are linked by.")
    p.add_argument("--run-hash", default=None, help="from triage_metadata.triage_runs")
    p.add_argument("--metric", default="precision@")
    p.add_argument("--parameter", default="100_abs", help="matches top_n 100 in scoring")
    p.add_argument("--list-runs", action="store_true")
    p.add_argument("--out-prefix", default="audition_over_time")
    # Audition CREATES this table. If a teammate already made one with the default
    # name, you get "permission denied", so namespace it per user by default.
    p.add_argument("--distance-table",
                   default=f"aud_best_dist_{os.environ.get('PGUSER') or getpass.getuser()}")
    args = p.parse_args()

    engine = get_engine(
        args.db_config,
        database=args.database,
        role=None if args.no_role else args.role,
    )
    print(f"database       = {args.database}")

    if args.list_runs:
        list_runs(engine)
        return

    run_hash = args.run_hash or latest_run_hash(engine)
    print(f"run_hash       = {run_hash}")
    print(f"distance_table = {args.distance_table}")

    from triage.component.audition import Auditioner

    BASELINE_TYPES = (
        "sklearn.dummy.DummyClassifier",
        "triage.component.catwalk.baselines.rankers.BaselineRankMultiFeature",
        "triage.component.catwalk.baselines.rankers.PercentileRankOneFeature",
        "triage.component.catwalk.baselines.thresholders.SimpleThresholder",
    )

    # PreAudition.get_model_groups_from_experiment() silently returns [] when the hash
    # it is given is not the key models are linked by (triage_runs.run_hash and
    # experiment_hash are not always the same), which then produces
    # "syntax error ... IN ()". Resolve the model groups ourselves instead, trying each
    # linkage this Triage version might use.
    candidates = [
        ("experiment_models join", """
            SELECT DISTINCT m.model_group_id, m.model_type
            FROM triage_metadata.models m
            JOIN triage_metadata.experiment_models em ON em.model_hash = m.model_hash
            WHERE em.experiment_hash = %(h)s
        """),
        ("models.built_by_experiment", """
            SELECT DISTINCT m.model_group_id, m.model_type
            FROM triage_metadata.models m
            WHERE m.built_by_experiment = %(h)s
        """),
        ("triage_run_id join", """
            SELECT DISTINCT m.model_group_id, m.model_type
            FROM triage_metadata.models m
            JOIN triage_metadata.triage_runs r ON r.id = m.built_in_triage_run
            WHERE r.run_hash = %(h)s
        """),
    ]

    rows = []
    if args.model_groups:
        ids = [int(x) for x in args.model_groups.split(",") if x.strip()]
        with engine.connect() as c:
            rows = list(c.exec_driver_sql(
                "SELECT DISTINCT model_group_id, model_type FROM triage_metadata.models "
                "WHERE model_group_id = ANY(%(g)s)", {"g": ids}))
        print(f"using model groups given on the command line: {ids}")
        missing = set(ids) - {r[0] for r in rows}
        if missing:
            print(f"!! these ids are not in the database: {sorted(missing)}")

    for label, sql in candidates if not rows else []:
        try:
            with engine.connect() as c:
                rows = list(c.exec_driver_sql(sql, {"h": run_hash}))
            if rows:
                print(f"resolved model groups via: {label}")
                break
        except Exception as exc:                 # column/table absent in this version
            print(f"  ({label} not usable: {type(exc).__name__})")

    if not rows:
        print("\n!! No models found for that hash by any linkage. What this database has:\n")
        with engine.connect() as c:
            for r in c.exec_driver_sql("""
                SELECT model_type, count(DISTINCT model_group_id) AS groups,
                       count(*) AS models,
                       min(train_end_time)::date AS first_split,
                       max(train_end_time)::date AS last_split
                FROM triage_metadata.models GROUP BY 1 ORDER BY 1
            """):
                print("   ", r)
        print("\nPick the right hash, or pass --model-groups with ids from above.\n")
        return

    ml_groups = sorted({r[0] for r in rows if r[1] not in BASELINE_TYPES})
    base_groups = sorted({r[0] for r in rows if r[1] in BASELINE_TYPES})

    with engine.connect() as c:
        end_times = [r[0] for r in c.exec_driver_sql(
            "SELECT DISTINCT train_end_time FROM triage_metadata.models "
            "WHERE model_group_id = ANY(%(g)s) ORDER BY train_end_time",
            {"g": ml_groups + base_groups})]

    print(f"candidate (ML) model groups : {len(ml_groups)} -> {ml_groups}")
    print(f"baseline model groups       : {len(base_groups)} -> {base_groups}")
    print(f"train_end_times             : {len(end_times)}")
    print(f"  from {end_times[0]} to {end_times[-1]}" if end_times else "  (none)")

    # Audition DROPS any model group that is missing a train_end_time, silently.
    # Show the coverage per group so a short one is visible before it vanishes.
    print("\n  group  n_splits  model_type")
    with engine.connect() as c:
        for r in c.exec_driver_sql("""
            SELECT model_group_id, count(DISTINCT train_end_time) AS n, min(model_type) AS t
            FROM triage_metadata.models WHERE model_group_id = ANY(%(g)s)
            GROUP BY 1 ORDER BY 2, 1
        """, {"g": ml_groups + base_groups}):
            flag = "" if r[1] == len(end_times) else "   <-- short, audition will drop it"
            print(f"  {r[0]:>5}  {r[1]:>8}  {r[2].split('.')[-1]}{flag}")
    print()

    if not base_groups:
        print("\n!! No baselines in this run. Slide 16 must show the base rate and the "
              "baselines, so check the hash before plotting.\n")
    if len(end_times) < 5:
        print(f"\n!! Only {len(end_times)} train_end_times. The assignment asks for the full "
              "set of validation splits (we have 30 monthly ones).\n")

    aud = Auditioner(
        db_engine=engine,
        model_group_ids=ml_groups,
        train_end_times=end_times,
        # Least restrictive filter: keep everything, so the plot shows the whole grid.
        initial_metric_filters=[{
            "metric": args.metric,
            "parameter": args.parameter,
            "max_from_best": 1.0,
            "threshold_value": 0.0,
        }],
        distance_table=args.distance_table,
        baseline_model_group_ids=base_groups,
    )

    aud.plot_model_groups()

    # plot_model_groups() draws to the current figures; save them all.
    nums = plt.get_fignums()
    if not nums:
        print("No figures produced - check that evaluations exist for this metric/parameter.")
    for n in nums:
        fig = plt.figure(n)
        out = f"{args.out_prefix}_{n}.png"
        fig.savefig(out, dpi=200, bbox_inches="tight")
        print("saved", out)

    ids = aud.thresholded_model_group_ids
    print(f"\nmodel groups surviving the filter: {len(ids)}")
    print(ids)


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# NOTES - four things in the course notebook that break on the class server:
#
# 1. pd.set_option('precision', 4)        -> removed in pandas 2.x; use
#                                            'display.precision'. Dropped here.
# 2. yaml.load(fd)                        -> needs a Loader in PyYAML 6; use safe_load.
# 3. sqlalchemy.engine.url.URL("postgres", ...)
#                                         -> SQLAlchemy 1.4+ makes URL immutable and
#                                            dropped the 'postgres' dialect name.
#                                            Use URL.create("postgresql", ...).
# 4. baseline_model_types                 -> the notebook lists PercentileRankOneFeature
#                                            and SimpleThresholder. We use
#                                            BaselineRankMultiFeature, so it must be added
#                                            or our baselines are mis-classified.
#
# Also note from the notebook: "model groups that don't have full train_end_time periods
# will be excluded from the analysis." If some models failed on some splits, they vanish
# from the plot silently. The counts printed above are the check for that.
# ---------------------------------------------------------------------------
