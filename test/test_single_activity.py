import os
import unittest
from datetime import timedelta
from os.path import exists

import pandas as pd
import numpy as np
import gpxpy
import pytz
from pyft.database import DatabaseManager
from pyft.single_activity import Activity, ActivityMetaData
from pyft.config import Config

# TODO:  Should probably merge this into test_multi_activity.
# Activities only really make sense within the context of an ActivityManager
# (to assign the activity_id) so there doesn't seem much point to test them separately.

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')

# Test GPX files.
# Neither 0 nor 1 should loose- or tight-match any other activity.
# 2 and 3 should loose- and tight-match each other but not match any others.
# 4 and 5 should loose- but not tight-match each other.
# TODO: TBC if 6 should match 4 or 5.
TEST_GPX_FILES = [
    os.path.join(TEST_DATA_DIR, 'GNR_2019.gpx'),
    os.path.join(TEST_DATA_DIR, 'Morning_Run_Miami.gpx'),
    os.path.join(TEST_DATA_DIR, '2020_08_05_pp_9k_ccw.gpx'),
    os.path.join(TEST_DATA_DIR, '2020_08_04_pp_9k_ccw.gpx'),
    os.path.join(TEST_DATA_DIR, '2020_03_20_pp_7.22k_cw.gpx'),
    os.path.join(TEST_DATA_DIR, '2020_06_18_pp_7.23k_ccw.gpx'),
    os.path.join(TEST_DATA_DIR, '2019_07_08_pp_7k_ccw.gpx'),
]

TEST_CONFIG = Config(
    db_file='/home/alan/bin/PycharmProjects/pyft/test/test.db'
)


class SingleActivityTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.gpx = []
        cls.activities = []
        for fpath in TEST_GPX_FILES:
            with open(fpath) as f:
                cls.gpx.append(gpxpy.parse(f))
            cls.activities.append(Activity.from_gpx_file(fpath))

        if exists(TEST_CONFIG.db_file):
            os.remove(TEST_CONFIG.db_file)

    @classmethod
    def tearDownClass(cls):
        if exists(TEST_CONFIG.db_file):
            os.remove(TEST_CONFIG.db_file)

    def test_1_setup(self):
        """Perform some basic checks to ensure the test is set up properly."""

        self.assertEqual(len(TEST_GPX_FILES), len(self.activities))
        self.assertEqual(len(TEST_GPX_FILES), len(self.gpx))

    def test_2_time(self):
        """Test that the GPX object and the associated Activity have the same time."""

        for a, g in zip(self.activities, self.gpx):
            self.assertEqual(a.metadata.date_time, g.time)

    def test_3_distance(self):
        """Test that the GPX object and the associated Activity have (almost) the same 2d length."""

        for a, g in zip(self.activities, self.gpx):
            self.assertAlmostEqual(a.metadata.distance_2d_km, g.length_2d())




if __name__ == '__main__':
    unittest.main()
