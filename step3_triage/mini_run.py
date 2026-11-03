import os, getpass, yaml
from datetime import datetime
from sqlalchemy.engine.url import URL
from triage.util.db import create_engine
from triage.experiments import MultiCoreExperiment

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, 'mcrt_mini_prk.yaml')
DB_CONFIG_PATH = os.path.expanduser('~/database.yaml')
GROUP_OUTPUT_ROOT = '/class/groups/jail_mh2/triage_runs_v2'

def main():
    os.umask(0o007)
    with open(DB_CONFIG_PATH) as f: db = yaml.safe_load(f)
    with open(CONFIG_PATH) as f: config = yaml.safe_load(f)
    url = URL.create('postgresql+psycopg2', host=db['host'], username=db['user'],
                     password=db['pass'], port=db['port'],
                     database='johnson_county_ddj_jail_mh2')
    engine = create_engine(url, connect_args={'options': '-c enable_nestloop=off'})
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = os.path.join(GROUP_OUTPUT_ROOT, f'{stamp}_{getpass.getuser()}_minipr')
    os.makedirs(run_dir, exist_ok=True)
    exp = MultiCoreExperiment(
        config=config, db_engine=engine, project_path=run_dir,
        n_processes=2, n_bigtrain_processes=1, n_db_processes=2,
        replace=False,
        save_predictions=True,
    )
    exp.validate()
    exp.run()
    print("DONE", run_dir)

if __name__ == '__main__':
    main()
