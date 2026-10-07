import os
import yaml
from sqlalchemy.engine.url import URL
from triage.util.db import create_engine
from triage.experiments import MultiCoreExperiment

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, 'mcrt_triage_config.yaml')
DB_CONFIG_PATH = os.path.expanduser('~/database.yaml')
OUTPUT_PATH = os.path.expanduser('~/triage_output_jail_mh2')

def main():
    with open(DB_CONFIG_PATH) as f:
        db = yaml.safe_load(f)
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)
    url = URL.create(
        'postgresql+psycopg2',
        host=db['host'],
        username=db['user'],
        password=db['pass'],
        port=db['port'],
        database='johnson_county_ddj_jail_mh2',
    )
    engine = create_engine(url, connect_args={'options': '-c enable_nestloop=off'})
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    experiment = MultiCoreExperiment(
        config=config,
        db_engine=engine,
        project_path=OUTPUT_PATH,
        n_processes=2,
        n_bigtrain_processes=1,
        n_db_processes=2,
        replace=False,
        save_predictions=False,
    )
    experiment.validate()
    experiment.run()

if __name__ == '__main__':
    main()
