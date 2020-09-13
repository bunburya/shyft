import os
import unittest

import pandas as pd
import gpxpy
import numpy as np
from pyft.geo_utils import distance, naive_distance
from pyft.parse_gpx import distance_2d, _iter_points, INITIAL_COL_NAMES
from pyft.single_activity import Activity

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')

TEST_GPX_FILES = [
    os.path.join(TEST_DATA_DIR, 'GNR_2019.gpx'),
    os.path.join(TEST_DATA_DIR, 'Morning_Run_Miami.gpx'),
    os.path.join(TEST_DATA_DIR, 'Evening_Run_9k_counterclockwise.gpx'),
    os.path.join(TEST_DATA_DIR, 'Evening_Run_9k_counterclockwise_2.gpx'),
    os.path.join(TEST_DATA_DIR, 'Afternoon_Run_7.22k_clockwise.gpx'),
    os.path.join(TEST_DATA_DIR, 'Afternoon_Run_7.23k_counterclockwise.gpx'),
    os.path.join(TEST_DATA_DIR, 'Morning_Run_7k_counterclockwise.gpx'),
]

class GeoUtilsTestCase(unittest.TestCase):

    def setUp(self):
        self.activities = [Activity.from_gpx_file(fpath) for fpath in TEST_GPX_FILES]
        self.gpx_df = []
        for fpath in TEST_GPX_FILES:
            with open(fpath) as f:
                gpx = gpxpy.parse(f)
            self.gpx_df.append(pd.DataFrame(_iter_points(gpx), columns=INITIAL_COL_NAMES))

    def test_1_distance(self):
        for a, gpx_df in zip(self.activities, self.gpx_df):
            distance_normal = distance_2d(gpx_df['point'], gpx_df['point'].shift())
            distance_vector = distance(a.points['latitude'], a.points['longitude'],
                                       a.points['latitude'].shift(), a.points['longitude'].shift())
            np.testing.assert_array_almost_equal(distance_normal, distance_vector, 4)



if __name__ == '__main__':
    unittest.main()
