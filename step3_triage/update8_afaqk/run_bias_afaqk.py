"""Compute aequitas fairness metrics for the Update 7 RF run.

Reuses the already-trained pickles in the existing RF run directory
(no retraining) and re-evaluates with a bias_audit_config so triage
writes race/sex disparities to test_results.aequitas.
"""
import os
import yaml
from datetime import datetime
from sqlalchemy.engine.url import URL
from triage.util.db import create_engine
from triage.experiments import MultiCoreExperiment

CONFIG_PATH = '/class/groups/jail_mh2/step3_triage/mcrt_triage_config_afaqk.yaml'
DB_CONFIG_PATH = os.path.expanduser('~/database.yaml')

# Point at the EXISTING run directory that holds the 330 RF pickles + matrices.
# This is the fix: run_afaqk.py mints a new timestamped dir every run, which is
# why an audit launched through it retrains everything. Reuse the dir instead.
EXISTING_RUN_DIR = '/class/groups/jail_mh2/triage_runs_v2/20261118_191929_afaqk_rf'

# Demographics source, verified against the database:
#   semantic.bookings: entity_id, booking_date, race (W/B/A/I), sex (MALE/FEMALE)
# Reference groups are the majority value of each attribute.
BIAS_AUDIT_CONFIG = {
    'from_obj_table': 'semantic.bookings',
    'attribute_columns': ['race', 'sex'],
    'knowledge_date_column': 'booking_date',
    'entity_id_column': 'entity_id',
    'ref_groups_method': 'predefined',
    'ref_groups': {'race': 'W', 'sex': 'MALE'},
    'thresholds': {'top_n': [100]},
}


def main():
    os.umask(0o007)

    with open(DB_CONFIG_PATH) as f:
        db = yaml.safe_load(f)
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    config['bias_audit_config'] = BIAS_AUDIT_CONFIG

    url = URL.create(
        'postgresql+psycopg2',
        host=db['host'],
        username=db['user'],
        password=db['pass'],
        port=db['port'],
        database='johnson_county_ddj_jail_mh2',
    )
    # SET ROLE jail_mh2 so any tables triage creates (protected_groups_*, labels_*)
    # are owned by the team role and any teammate can use them.
    engine = create_engine(url, connect_args={
        'options': '-c enable_nestloop=off -c role=jail_mh2'})

    print(f'[{datetime.now():%H:%M:%S}] reusing run dir: {EXISTING_RUN_DIR}')
    experiment = MultiCoreExperiment(
        config=config,
        db_engine=engine,
        project_path=EXISTING_RUN_DIR,
        n_processes=4,
        n_bigtrain_processes=1,
        n_db_processes=2,
        replace=False,
        save_predictions=False,
    )
    experiment.validate()
    experiment.run()


if __name__ == '__main__':
    main()
