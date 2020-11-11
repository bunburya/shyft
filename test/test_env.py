import filecmp
import os
import shutil
import unittest
from datetime import datetime, timedelta
from os.path import exists

import numpy as np
import pandas as pd
import gpxpy
from pyft.multi_activity import ActivityManager
from pyft.single_activity import Activity, ActivityMetaData
from pyft.config import Config

"""Set up a basic test environment, so that running `python -i test_env.py`
allows us to explore the data and objects interactively.
"""

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')
TEST_CONFIG_FILE = os.path.join(TEST_DATA_DIR, 'test_config.ini')
TEST_RUN_DATA_DIR = os.path.join(TEST_DATA_DIR, 'run_env')

if os.path.exists(TEST_RUN_DATA_DIR):
    shutil.rmtree(TEST_RUN_DATA_DIR)
os.makedirs(TEST_RUN_DATA_DIR)

TEST_GPX_FILES = [
    os.path.join(TEST_DATA_DIR, 'GNR_2019.gpx'),                    # 0     2019-09-08
    os.path.join(TEST_DATA_DIR, 'Morning_Run_Miami.gpx'),           # 1     2019-10-30
    os.path.join(TEST_DATA_DIR, '2020_08_05_pp_9k_ccw.gpx'),        # 2     2020-08-05
    os.path.join(TEST_DATA_DIR, '2020_08_04_pp_9k_ccw.gpx'),        # 3     2020-08-04
    os.path.join(TEST_DATA_DIR, '2020_03_20_pp_7.22k_cw.gpx'),      # 4     2020-03-20
    os.path.join(TEST_DATA_DIR, '2020_06_18_pp_7.23k_ccw.gpx'),     # 5     2020-06-18
    os.path.join(TEST_DATA_DIR, '2019_07_08_pp_7k_ccw.gpx'),        # 6     2019-07-08
    os.path.join(TEST_DATA_DIR, 'Calcutta_Run_10k_2019.gpx'),       # 7     2019
    os.path.join(TEST_DATA_DIR, 'cuilcagh_walk_2019.gpx'),          # 8     2019
    os.path.join(TEST_DATA_DIR, 'fermanagh_walk_2019.gpx'),         # 9     2019
    os.path.join(TEST_DATA_DIR, 'Frank_Duffy_10_Mile_2019.gpx'),    # 10    2019
    os.path.join(TEST_DATA_DIR, 'Great_Ireland_Run_2019.gpx'),      # 11    2019
    os.path.join(TEST_DATA_DIR, 'howth_walk_2019.gpx'),             # 12    2019
    os.path.join(TEST_DATA_DIR, 'Irish_Runner_10_Mile_2019.gpx'),   # 13    2019
    os.path.join(TEST_DATA_DIR, 'run_in_the_dark_10k_2019.gpx'),    # 14    2019
]

TEST_DB_FILE = os.path.join(TEST_RUN_DATA_DIR, 'dash_test.db')
TEST_CONFIG_FILE = os.path.join(TEST_DATA_DIR, 'test_config.ini')
TEST_ACTIVITY_GRAPHS_FILE = os.path.join(TEST_DATA_DIR, 'test_activity_graphs.json')
TEST_OVERVIEW_GRAPHS_FILE = os.path.join(TEST_DATA_DIR, 'test_overview_graphs.json')

TEST_CONFIG = Config(
    TEST_CONFIG_FILE,
    TEST_ACTIVITY_GRAPHS_FILE,
    TEST_OVERVIEW_GRAPHS_FILE,
    data_dir=TEST_RUN_DATA_DIR,
    db_file=TEST_DB_FILE
)

activity_manager = ActivityManager(TEST_CONFIG)
for fpath in TEST_GPX_FILES:
    activity_manager.add_activity_from_gpx_file(fpath)