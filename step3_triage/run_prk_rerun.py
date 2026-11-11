#!/usr/bin/env python
"""
Focused rerun that SAVES PREDICTIONS for: Baseline 4, logistic regression (group 15),
random forest (group 19), so we can draw PR-k curves for all three.

Why a separate script: step3_triage/run.py has no CLI (it ignores --help and launches the
main experiment) and hardcodes save_predictions=False.

Usage (repo root, jail_mh2 env):
    pyenv shell jail_mh2
    python step3_triage/run_prk_rerun.py --validate-only
    python step3_triage/run_prk_rerun.py
"""
import argparse
import getpass
import logging
import os
from pathlib import Path

import sqlalchemy
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DATABASE = "johnson_county_ddj_jail_mh2"      # same hardcoded db as run.py


def get_engine():
    with open(Path.home() / "database.yaml") as fd:
        cfg = yaml.safe_load(fd)
    from triage import create_engine      # Triage's wrapper (has get_inspector); same as run.py
    url = sqlalchemy.engine.url.URL.create(
        "postgresql", host=cfg["host"], username=cfg["user"],
        database=DATABASE, password=cfg["pass"], port=cfg["port"])
    return create_engine(url.render_as_string(hide_password=False))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default=str(SCRIPT_DIR / "mcrt_mini_prk.yaml"))
    p.add_argument("--project-path", default=str(REPO_ROOT / "triage_output_prk"))
    p.add_argument("--validate-only", action="store_true")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    os.chdir(REPO_ROOT)

    with open(args.config) as f:
        config = yaml.full_load(f)

    # 1) Change the label-table hash so we do not collide with a teammate's table
    #    ("permission denied for table labels_new_arrest_12m_...").
    lc = config["label_config"]
    query = lc.get("query")
    if query is None:
        query = Path(lc.pop("filepath")).read_text()
    lc["query"] = f"-- prk rerun by {getpass.getuser()}\n" + query

    # 2) Add group 19 (random forest) by copying its block EXACTLY from the main config.
    #    A model group is identified by its hyperparameters (incl. random_state, criterion),
    #    so any difference would create a different group from the one on the slides.
    rf_key = "sklearn.ensemble.RandomForestClassifier"
    with open(SCRIPT_DIR / "mcrt_triage_config.yaml") as f:
        main_cfg = yaml.full_load(f)
    config["grid_config"][rf_key] = main_cfg["grid_config"][rf_key]
    logging.info("Random forest grid: %s", config["grid_config"][rf_key])

    from triage.experiments import SingleThreadedExperiment

    Path(args.project_path).mkdir(parents=True, exist_ok=True)
    exp = SingleThreadedExperiment(
        config=config,
        db_engine=get_engine(),
        project_path=args.project_path,
        replace=False,
        save_predictions=True,          # the whole point
    )
    exp.validate()
    logging.info("Config validated.")
    if args.validate_only:
        return
    exp.run()
    logging.info("Done. Predictions are in test_results.predictions.")


if __name__ == "__main__":
    main()
