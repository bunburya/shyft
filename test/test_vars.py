"""Variables describing where to find and save test data, for use by
test scripts.
"""

import os
import shutil
from shutil import copyfile

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')
TEST_GPX_FILES_DIR = os.path.join(TEST_DATA_DIR, 'gpx_files')
TEST_CONFIG_FILE_BASE = os.path.join(TEST_DATA_DIR, 'test_config.ini')
TEST_RUN_DATA_DIR_BASE = os.path.join(TEST_DATA_DIR, 'run')
TEST_ACTIVITY_GRAPHS_FILE = os.path.join(TEST_DATA_DIR, 'test_activity_graphs.json')
TEST_OVERVIEW_GRAPHS_FILE = os.path.join(TEST_DATA_DIR, 'test_overview_graphs.json')

# Test GPX files.
# Neither 0 nor 1 should loose- or tight-match any other activity.
# 2 and 3 should loose- and tight-match each other but not match any others.
# 4 and 5 should loose- but not tight-match each other.
# TBC if 6 should match 4 or 5.
TEST_GPX_FILES = [
    os.path.join(TEST_GPX_FILES_DIR, 'GNR_2019.gpx'),                   # 0     2019-09-08
    os.path.join(TEST_GPX_FILES_DIR, 'Morning_Run_Miami.gpx'),          # 1     2019-10-30
    os.path.join(TEST_GPX_FILES_DIR, '2020_08_05_pp_9k_ccw.gpx'),       # 2     2020-08-05
    os.path.join(TEST_GPX_FILES_DIR, '2020_08_04_pp_9k_ccw.gpx'),       # 3     2020-08-04
    os.path.join(TEST_GPX_FILES_DIR, '2020_03_20_pp_7.22k_cw.gpx'),     # 4     2020-03-20
    os.path.join(TEST_GPX_FILES_DIR, '2020_06_18_pp_7.23k_ccw.gpx'),    # 5     2020-06-18
    os.path.join(TEST_GPX_FILES_DIR, '2019_07_08_pp_7k_ccw.gpx'),       # 6     2019-07-08
    os.path.join(TEST_GPX_FILES_DIR, 'Calcutta_Run_10k_2019.gpx'),      # 7     2019
    os.path.join(TEST_GPX_FILES_DIR, 'cuilcagh_walk_2019.gpx'),         # 8     2019
    os.path.join(TEST_GPX_FILES_DIR, 'fermanagh_walk_2019.gpx'),        # 9     2019
    os.path.join(TEST_GPX_FILES_DIR, 'Frank_Duffy_10_Mile_2019.gpx'),   # 10    2019
    os.path.join(TEST_GPX_FILES_DIR, 'Great_Ireland_Run_2019.gpx'),     # 11    2019
    os.path.join(TEST_GPX_FILES_DIR, 'howth_walk_2019.gpx'),            # 12    2019
    os.path.join(TEST_GPX_FILES_DIR, 'Irish_Runner_10_Mile_2019.gpx'),  # 13    2019
    os.path.join(TEST_GPX_FILES_DIR, 'run_in_the_dark_10k_2019.gpx'),   # 14    2019
    os.path.join(TEST_GPX_FILES_DIR, 'path_of_gods_walk_2020.gpx'),     # 15    2020-10-11
    os.path.join(TEST_GPX_FILES_DIR, 'amalfi_ironworks_walk_2020.gpx')  # 16    2020-10-13
]

# ints here are index values in TEST_GPX_FILES
LOOSE_MATCH = (
    (2, 3),
    (4, 5)
)

TIGHT_MATCH = (
    (2, 3),
)

UNIQUE = (0, 1, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16)

ACTIVITIES_2019 = (0, 1, 6, 7, 8, 9, 10, 11, 12, 13, 14)
ACTIVITIES_2020 = (2, 3, 4, 5, 15, 16)
ACTIVITIES_2020_08 = (2, 3)

def run_data_dir(name: str, replace: bool = False) -> str:
    data_dir = os.path.join(TEST_RUN_DATA_DIR_BASE, name)
    if replace and os.path.exists(data_dir):
        shutil.rmtree(data_dir)
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

def config_file(run_dir: str) -> str:
    config_fpath = os.path.join(run_dir, 'config.ini')
    copyfile(TEST_CONFIG_FILE_BASE, config_fpath)
    return config_fpath
