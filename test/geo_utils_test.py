import unittest

import pandas as pd
import gpxpy
import numpy as np
from pyft.geo_utils import distance, naive_distance
from pyft.parse_gpx import distance_2d, _iter_points, INITIAL_COL_NAMES
from pyft.single_activity import Activity

TEST_GPX_FILE_1 = '/home/alan/bin/PycharmProjects/pyft/test/test_data/activity_4037789130.gpx'

class GeoUtilsTestCase(unittest.TestCase):

    def setUp(self):
        self.activity = Activity.from_gpx_file(TEST_GPX_FILE_1)
        with open(TEST_GPX_FILE_1) as f:
            self.gpx = gpxpy.parse(f)
        self.gpx_df = pd.DataFrame(_iter_points(self.gpx), columns=INITIAL_COL_NAMES)

    def test_1_distance(self):
        distance_normal = distance_2d(self.gpx_df['point'], self.gpx_df['point'].shift())
        distance_vector = distance(self.activity.points['latitude'], self.activity.points['longitude'],
                                   self.activity.points['latitude'].shift(), self.activity.points['longitude'].shift())
        np.testing.assert_array_almost_equal(distance_normal, distance_vector, 4)



if __name__ == '__main__':
    unittest.main()
