import shutil

from pyft.multi_activity import ActivityManager
from pyft.config import Config
from test.test_data_vars import *

"""Set up a basic test environment, so that running `python -i test_env.py`
allows us to explore the data and objects interactively.
"""

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')
TEST_CONFIG_FILE = os.path.join(TEST_DATA_DIR, 'test_config.ini')
TEST_RUN_DATA_DIR = run_data_dir('env')

if os.path.exists(TEST_RUN_DATA_DIR):
    shutil.rmtree(TEST_RUN_DATA_DIR)
os.makedirs(TEST_RUN_DATA_DIR)

TEST_CONFIG = Config(
    TEST_CONFIG_FILE,
    TEST_ACTIVITY_GRAPHS_FILE,
    TEST_OVERVIEW_GRAPHS_FILE,
    data_dir=TEST_RUN_DATA_DIR,
)

activity_manager = ActivityManager(TEST_CONFIG)
for fpath in TEST_GPX_FILES:
    activity_manager.add_activity_from_gpx_file(fpath)