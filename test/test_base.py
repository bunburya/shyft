"""Base code for unit testing, including a base test class and variables
describing where to find and save test data, for use by test scripts.
"""
import filecmp
import os
import shutil
import unittest
from datetime import timedelta
from shutil import copyfile

import numpy as np
import pandas as pd

from pyft.single_activity import ActivityMetaData, Activity

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')
TEST_GPX_FILES_DIR = os.path.join(TEST_DATA_DIR, 'gpx_files')
TEST_FIT_FILES_DIR = os.path.join(TEST_DATA_DIR, 'fit_files')
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

# These have both .gpx and .fit files
FIT_AND_GPX = (
    '2020_10_03_pp_7k_ccw',
    '2020_11_01_pp_6.84k_ccw',
    '2020_11_07_pp_7.23k_cw',
    'amalfi_ironworks_walk_2020',
    '2020_10_24_pp_7.24k_ccw',
    '2020_11_03_pp_7k_ccw',
    '2020_11_09_pp_7k_ccw',
    'path_of_gods_walk_2020'
)

TEST_GPX_FILES_2 = [os.path.join(TEST_GPX_FILES_DIR, f'{fname}.gpx') for fname in FIT_AND_GPX]
TEST_FIT_FILES = [os.path.join(TEST_FIT_FILES_DIR, f'{fname}.fit') for fname in FIT_AND_GPX]

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

class BaseTestCase(unittest.TestCase):

    def _assert_timedeltas_almost_equal(self, td1: timedelta, td2: timedelta, places: int = 4):
        self.assertAlmostEqual(td1.total_seconds(), td2.total_seconds(), places)

    def _assert_files_equal(self, fpath1: str, fpath2: str):
        self.assertTrue(filecmp.cmp(fpath1, fpath2), f'{fpath1} is not equal to {fpath2}.')

    def _assert_metadata_equal(self, md1: ActivityMetaData, md2: ActivityMetaData,
                               almost: bool = False, check_data_files: bool = True):

        self.assertEqual(md1.activity_id, md2.activity_id,
                         msg=f'Activity IDs are not the same ({md1.activity_id} vs {md2.activity_id}).')
        self.assertEqual(md1.activity_type, md2.activity_type,
                         msg=f'Activity types are not the same ({md1.activity_type} vs {md2.activity_type}).')
        self.assertEqual(md1.date_time, md2.date_time,
                         msg=f'Activity times are not the same ({md1.date_time} vs {md2.date_time}).')
        if almost:
            self.assertAlmostEqual(md1.distance_2d_km, md2.distance_2d_km, 1,
                             msg=f'Activity distances are not the same ({md1.distance_2d_km} vs {md2.distance_2d_km}).')
            np.testing.assert_array_almost_equal(md1.center, md2.center, decimal=2)
            np.testing.assert_array_almost_equal(md1.points_std, md2.points_std, decimal=2)
        else:
            self.assertEqual(md1.distance_2d_km, md2.distance_2d_km,
                            msg=f'Activity distances are not the same ({md1.distance_2d_km} vs {md2.distance_2d_km}).')
            np.testing.assert_array_equal(md1.center, md2.center)
            np.testing.assert_array_equal(md1.points_std, md2.points_std)
        if almost:
            self._assert_timedeltas_almost_equal(md1.km_pace_mean, md2.km_pace_mean, -2)
            self._assert_timedeltas_almost_equal(md1.mile_pace_mean, md2.mile_pace_mean, -3)
            self._assert_timedeltas_almost_equal(md1.duration, md2.duration, -3)
        else:
            self._assert_timedeltas_almost_equal(md1.km_pace_mean, md2.km_pace_mean)
            self._assert_timedeltas_almost_equal(md1.mile_pace_mean, md2.mile_pace_mean)
            self._assert_timedeltas_almost_equal(md1.duration, md2.duration)
        self.assertEqual(md1.prototype_id, md2.prototype_id,
                         msg=f'Prototype IDs are not the same ({md1.prototype_id} vs {md2.prototype_id}).')
        self.assertEqual(md1.name, md2.name,
                         msg=f'Activity names are not the same ({md1.name} vs {md2.name}).')
        self.assertEqual(md1.description, md2.description,
                         msg=f'Activity descriptions are not the same ({md1.description} vs {md2.description}).')
        self._assert_files_equal(md1.thumbnail_file, md2.thumbnail_file)
        if check_data_files:
            self._assert_files_equal(md1.data_file, md2.data_file)

    def _assert_activities_equal(self, a1: Activity, a2: Activity, almost: bool = False, check_data_files: bool = True):
        self._assert_metadata_equal(a1.metadata, a2.metadata, almost, check_data_files)
        if almost:
            # Some columns can't really be compared for "almost" equality in the way that we want.
            # So we have to drop these.
            # TODO: Find other ways to compare the dropped columns.
            rtol = 5
            #print(a1.points[a1.points['mile'] != a2.points['mile']])
            #print(a1.points.iloc[421])
            #print(a2.points.iloc[421])
            pd.testing.assert_frame_equal(
                a1.points.drop(['km_pace', 'mile_pace', 'mile', 'km'], axis=1),
                a2.points.drop(['km_pace', 'mile_pace', 'mile', 'km'], axis=1),
                check_like=True, rtol=rtol
            )
        else:
            pd.testing.assert_frame_equal(a1.points, a2.points, check_like=True)