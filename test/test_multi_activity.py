import os
import unittest
from os.path import exists

import numpy as np
import pandas as pd
import gpxpy
from pyft.multi_activity import ActivityManager
from pyft.single_activity import Activity, ActivityMetaData
from pyft.config import Config

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')

# Test GPX files.
# Neither 0 nor 1 should loose- or tight-match any other activity.
# 2 and 3 should loose- and tight-match each other but not match any others.
# 4 and 5 should loose- but not tight-match each other.
# TBC if 6 should match 4 or 5.
TEST_GPX_FILES = [
    os.path.join(TEST_DATA_DIR, 'GNR_2019.gpx'),
    os.path.join(TEST_DATA_DIR, 'Morning_Run_Miami.gpx'),
    os.path.join(TEST_DATA_DIR, 'Evening_Run_9k_counterclockwise.gpx'),
    os.path.join(TEST_DATA_DIR, 'Evening_Run_9k_counterclockwise_2.gpx'),
    os.path.join(TEST_DATA_DIR, 'Afternoon_Run_7.22k_clockwise.gpx'),
    os.path.join(TEST_DATA_DIR, 'Afternoon_Run_7.23k_counterclockwise.gpx'),
    os.path.join(TEST_DATA_DIR, 'Morning_Run_7k_counterclockwise.gpx'),
]

# ints here are index values in TEST_GPX_FILES
LOOSE_MATCH = (
    (2, 3),
    (4, 5)
)

TIGHT_MATCH = (
    (2, 3),
)

UNIQUE = (0, 1)

TEST_CONFIG_1 = Config(
    db_file='/home/alan/bin/PycharmProjects/pyft/test/test1.db'
)

TEST_CONFIG_2 = Config(
    db_file='/home/alan/bin/PycharmProjects/pyft/test/test2.db'
)


class ActivityManagerTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        if exists(TEST_CONFIG_1.db_file):
            os.remove(TEST_CONFIG_1.db_file)
        if exists(TEST_CONFIG_2.db_file):
            os.remove(TEST_CONFIG_2.db_file)

        cls.gpx = []
        cls.activities = []
        for fpath in TEST_GPX_FILES:
            with open(fpath) as f:
                cls.gpx.append(gpxpy.parse(f))
            cls.activities.append(Activity.from_gpx_file(fpath))
        cls.proto_ids = {}
        cls.fpath_ids = {}
        cls.manager_1 = ActivityManager(TEST_CONFIG_1)  # Add Activities directly
        cls.manager_2 = ActivityManager(TEST_CONFIG_2)  # Add Activities from filepaths



    @classmethod
    def tearDownClass(cls):
        if exists(TEST_CONFIG_1.db_file):
            os.remove(TEST_CONFIG_1.db_file)
        if exists(TEST_CONFIG_2.db_file):
            os.remove(TEST_CONFIG_2.db_file)

    def _assert_metadata_equal(self, md1: ActivityMetaData, md2: ActivityMetaData):
        self.assertEqual(md1.activity_id, md2.activity_id)
        self.assertEqual(md1.activity_type, md2.activity_type)
        self.assertEqual(md1.activity_id, md2.activity_id)
        self.assertEqual(md1.date_time, md2.date_time)
        self.assertEqual(md1.distance_2d, md2.distance_2d)
        np.testing.assert_array_equal(md1.center, md2.center)
        self.assertEqual(md1.prototype_id, md2.prototype_id)
        self.assertEqual(md1.name, md2.name)
        self.assertEqual(md1.description, md2.description)
        self.assertEqual(md1.data_file, md2.data_file)

    def _assert_activities_equal(self, a1: Activity, a2: Activity):
        self._assert_metadata_equal(a1.metadata, a2.metadata)
        pd.testing.assert_frame_equal(a1.points, a2.points, check_like=True)

    def test_1_setup(self):
        """Perform some basic checks to ensure the test is set up properly."""

        self.assertEqual(len(TEST_GPX_FILES), len(self.activities))
        self.assertEqual(len(TEST_GPX_FILES), len(self.gpx))
        db1 = self.manager_1.db
        db1.cursor.execute('SELECT name from sqlite_master where type= "table"')
        tables = set(db1.cursor.fetchall())
        self.assertSetEqual(tables, {('prototypes',), ('activities',), ('points',)})
        db2 = self.manager_2.db
        db2.cursor.execute('SELECT name from sqlite_master where type= "table"')
        self.assertSetEqual(set(db2.cursor.fetchall()), tables)

    def test_2_add_activity(self):
        """Test basic adding of activities."""

        for a in self.activities:
            self.assertIsNone(a.metadata.activity_id)
            self.assertIsNone(a.metadata.prototype_id)
            self.manager_1.add_activity(a)
            self.assertIsNotNone(a.metadata.activity_id)
            self.assertIsNotNone(a.metadata.prototype_id)
            self.proto_ids[a.metadata.activity_id] = a.metadata.prototype_id
            self._assert_activities_equal(a, self.manager_1.get_activity_by_id(a.metadata.activity_id))

    def test_3_add_activity_from_file(self):
        """Test basic adding of activities from filepaths, including
        that the results are the same as adding activities directly.
        """

        for fpath in TEST_GPX_FILES:
            _id = self.manager_2.add_activity_from_gpx_file(fpath)
            self.fpath_ids[fpath] = _id

        for a1, a2 in zip(self.manager_1.activities, self.manager_2.activities):
            self._assert_activities_equal(a1, a2)

        self.assertSequenceEqual(self.manager_1.prototypes, self.manager_2.prototypes)

    def test_4_test_loose_matching(self):

        for i1, i2 in LOOSE_MATCH:
            id1 = self.fpath_ids[TEST_GPX_FILES[i1]]
            id2 = self.fpath_ids[TEST_GPX_FILES[i2]]
            a1 = self.manager_1.get_activity_by_id(id1)
            a2 = self.manager_1.get_activity_by_id(id2)
            self.assertTrue(self.manager_1.loose_match_routes(a1, a2),
                            msg=f'{os.path.basename(TEST_GPX_FILES[i1])} and {os.path.basename(TEST_GPX_FILES[i2])}'
                                ' do not loose match.')

    def test_5_test_tight_matching(self):

        for i1, i2 in TIGHT_MATCH:
            id1 = self.fpath_ids[TEST_GPX_FILES[i1]]
            id2 = self.fpath_ids[TEST_GPX_FILES[i2]]
            a1 = self.manager_1.get_activity_by_id(id1)
            a2 = self.manager_1.get_activity_by_id(id2)
            self.assertTrue(self.manager_1.tight_match_routes(a1, a2))

        for i1, i2 in LOOSE_MATCH:
            if (i1, i2) in TIGHT_MATCH:
                continue
            id1 = self.fpath_ids[TEST_GPX_FILES[i1]]
            id2 = self.fpath_ids[TEST_GPX_FILES[i2]]
            a1 = self.manager_1.get_activity_by_id(id1)
            a2 = self.manager_1.get_activity_by_id(id2)
            self.assertFalse(self.manager_1.tight_match_routes(a1, a2)[0])

    def test_6_unique_matching(self):
        for i in UNIQUE:
            fpath1 = TEST_GPX_FILES[i]
            id1 = self.fpath_ids[fpath1]
            a1 = self.manager_1.get_activity_by_id(id1)
            for fpath2 in TEST_GPX_FILES:
                id2 = self.fpath_ids[fpath2]
                a2 = self.manager_1.get_activity_by_id(id2)
                if fpath1 == fpath2:
                    self.assertTrue(self.manager_1.loose_match_routes(a1, a2),
                                    msg=f'{fpath1} is not loose matching itself.')
                    self.assertTrue(self.manager_1.tight_match_routes(a1, a2)[0],
                                    msg=f'{fpath1} is not tight matching itself.')
                else:
                    self.assertFalse(self.manager_1.loose_match_routes(a1, a2),
                                     msg=f'{os.path.basename(fpath1)} is loose matching {os.path.basename(fpath2)}.')
                    self.assertFalse(self.manager_1.tight_match_routes(a1, a2)[0],
                                     msg=f'{os.path.basename(fpath1)} is tight matching {os.path.basename(fpath2)}.')

    def test_7_prototypes(self):
        for i in UNIQUE:
            fpath1 = TEST_GPX_FILES[i]
            a1 = self.manager_1.get_activity_by_id(self.fpath_ids[fpath1])
            self.assertEqual(a1.metadata.activity_id, a1.metadata.prototype_id)
            for fpath2 in TEST_GPX_FILES:
                a2 = self.manager_1.get_activity_by_id(self.fpath_ids[fpath2])
                if fpath1 == fpath2:
                    self.assertEqual(a1.metadata.prototype_id, a2.metadata.prototype_id)
                else:
                    self.assertNotEqual(a1.metadata.prototype_id, a2.metadata.prototype_id)

        for i1, i2 in TIGHT_MATCH:
            id1 = self.fpath_ids[TEST_GPX_FILES[i1]]
            id2 = self.fpath_ids[TEST_GPX_FILES[i2]]
            a1 = self.manager_1.get_activity_by_id(id1)
            a2 = self.manager_1.get_activity_by_id(id2)
            self.assertEqual(a1.metadata.prototype_id, a2.metadata.prototype_id)

        for a in self.manager_1.activities:
            p = self.manager_1.get_activity_by_id(a.metadata.prototype_id)
            self.assertTrue(self.manager_1.tight_match_routes(a, p))


if __name__ == '__main__':
    unittest.main()
