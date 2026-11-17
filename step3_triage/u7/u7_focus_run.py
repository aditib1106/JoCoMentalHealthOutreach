"""Focused U7 refit: single split, champion models, save_predictions=True.
Overlays feature_aggregations from the U6 config so matrix hashes match
(=> matrices get reused, run completes in ~minutes)."""
import os, getpass, yaml
from datetime import datetime
from sqlalchemy.engine.url import URL
from triage.util.db import create_engine
from triage.experiments import MultiCoreExperiment

HERE = os.path.dirname(os.path.abspath(__file__))
U7_CONFIG = os.path.join(HERE, 'u7_focus_config.yaml')
U6_CONFIG = os.path.join(HERE, '..', 'mcrt_triage_config.yaml')  # for feature_aggregations
DB_CONFIG_PATH = os.path.expanduser('~/database.yaml')
GROUP_OUTPUT_ROOT = '/class/groups/jail_mh2/triage_runs_v2'

def main():
    os.umask(0o007)
    with open(DB_CONFIG_PATH) as f:
        db = yaml.safe_load(f)
    with open(U7_CONFIG) as f:
        config = yaml.safe_load(f)
    # Pull feature_aggregations from the U6 config so matrices match exactly.
    with open(U6_CONFIG) as f:
        u6 = yaml.safe_load(f)
    config['feature_aggregations'] = u6['feature_aggregations']

    url = URL.create(
        'postgresql+psycopg2',
        host=db['host'], username=db['user'], password=db['pass'],
        port=db['port'], database='johnson_county_ddj_jail_mh2',
    )
    engine = create_engine(url, connect_args={'options': '-c enable_nestloop=off'})

    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = os.path.join(GROUP_OUTPUT_ROOT, f'{stamp}_{getpass.getuser()}_u7focus')
    os.makedirs(run_dir, exist_ok=True)

    experiment = MultiCoreExperiment(
        config=config, db_engine=engine, project_path=run_dir,
        n_processes=2, n_bigtrain_processes=1, n_db_processes=2,
        replace=False,
        save_predictions=True,   # ← the whole point of this focused run
    )
    experiment.validate()
    experiment.run()
    print("DONE", run_dir)

if __name__ == '__main__':
    main()
