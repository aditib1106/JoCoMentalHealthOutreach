import os, yaml
from sqlalchemy.engine.url import URL
from triage.util.db import create_engine
from triage.experiments import MultiCoreExperiment

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, 'mcrt_triage_config.yaml')
DB_CONFIG_PATH = os.path.expanduser('~/database.yaml')

with open(DB_CONFIG_PATH) as f: db = yaml.safe_load(f)
with open(CONFIG_PATH) as f:    config = yaml.safe_load(f)

url = URL.create(
    'postgresql+psycopg2',
    host=db['host'], username=db['user'], password=db['pass'],
    port=db['port'], database='johnson_county_ddj_jail_mh2',
)
engine = create_engine(url, connect_args={'options': '-c enable_nestloop=off'})

# project_path must exist but no files get written during validate()
tmp_dir = '/tmp/jail_mh2_dry_run'
os.makedirs(tmp_dir, exist_ok=True)

experiment = MultiCoreExperiment(
    config=config, db_engine=engine, project_path=tmp_dir,
    n_processes=1, n_bigtrain_processes=1, n_db_processes=1,
    replace=False, save_predictions=False,
)
experiment.validate()
print("VALIDATE PASSED")
