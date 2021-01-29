import shutil

from pyft.activity_manager import ActivityManager
from pyft.config import Config
from test import test_common
from test.test_common import *

"""Set up a basic test environment, so that running `python -i test_env.py`
allows us to explore the data and objects interactively.
"""

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')
TEST_RUN_DATA_DIR = run_data_dir('env', replace=True)
TEST_CONFIG_FILE = config_file(TEST_RUN_DATA_DIR)

TEST_CONFIG = Config(
    TEST_CONFIG_FILE,
    TEST_ACTIVITY_GRAPHS_FILE,
    TEST_OVERVIEW_GRAPHS_FILE,
    data_dir=TEST_RUN_DATA_DIR,
)

activity_manager = ActivityManager(TEST_CONFIG)
for fpath in TEST_GPX_FILES:
    activity_manager.add_activity_from_file(fpath)