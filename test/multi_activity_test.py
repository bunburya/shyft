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
from test.test_base import *


class ActivityManagerTestCase(BaseTestCase):

    def test_01_setup(self):
        """Perform some basic checks to ensure the test is set up properly."""

        self.assertEqual(len(TEST_GPX_FILES), len(self.activities))
        self.assertEqual(len(TEST_GPX_FILES), len(self.gpx))
        db1 = self.manager_1.dbm
        db1.cursor.execute('SELECT name from sqlite_master where type= "table"')
        tables = {i[0] for i in db1.cursor.fetchall()}
        self.assertSetEqual(tables, {'prototypes', 'activities', 'points'})
        db2 = self.manager_2.dbm
        db2.cursor.execute('SELECT name from sqlite_master where type= "table"')
        self.assertSetEqual({i[0] for i in db2.cursor.fetchall()}, tables)

    def test_02_add_activity(self):
        """Test basic adding of activities."""

        activities = []
        for i, fpath in enumerate(TEST_GPX_FILES):
            with open(fpath) as f:
                self.gpx.append(gpxpy.parse(f))
            activities.append(Activity.from_file(fpath, self.TEST_CONFIG_3, activity_id=i))


        for a in activities:
            # print(a.metadata.data_file, a.metadata.date_time)
            self.assertIsNotNone(a.metadata.activity_id)
            self.assertIsNone(a.metadata.prototype_id)
            self.manager_3.add_activity(a)
            self.assertIsNotNone(a.metadata.activity_id)
            self.assertIsNotNone(a.metadata.prototype_id)
            self.proto_ids[a.metadata.activity_id] = a.metadata.prototype_id
            self._assert_activities_equal(a, self.manager_3.get_activity_by_id(a.metadata.activity_id))

    def test_03_add_activity_from_file(self):
        """Test basic adding of activities from filepaths, including
        that the results are the same as adding activities directly.
        """

        for fpath in TEST_GPX_FILES:
            _id = self.manager_2.add_activity_from_file(fpath)
            self.fpath_ids[fpath] = _id

        for a1, a2 in zip(self.manager_1.activities, self.manager_2.activities):
            self._assert_activities_equal(a1, a2)

        self.assertSequenceEqual(self.manager_1.prototypes, self.manager_2.prototypes)

    def test_04_test_loose_matching(self):

        for i1, i2 in LOOSE_MATCH:
            id1 = self.fpath_ids[TEST_GPX_FILES[i1]]
            id2 = self.fpath_ids[TEST_GPX_FILES[i2]]
            a1 = self.manager_1.get_activity_by_id(id1)
            a2 = self.manager_1.get_activity_by_id(id2)
            self.assertTrue(self.manager_1.loose_match_routes(a1, a2),
                            msg=f'{os.path.basename(TEST_GPX_FILES[i1])} and {os.path.basename(TEST_GPX_FILES[i2])}'
                                ' do not loose match.')

    def test_05_test_tight_matching(self):

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

    def test_06_unique_matching(self):
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

    def test_07_prototypes(self):
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

    def test_08_search(self):
        # print(self.manager_1.get_activity_by_id(1))
        results = self.manager_1.search_activity_data(from_date=datetime(2019, 1, 1), to_date=datetime(2020, 1, 1))
        self.assertSetEqual({a.activity_id for a in results}, set(ACTIVITIES_2019))
        # print(results)
        results = self.manager_1.search_activity_data(prototype=2)
        self.assertSetEqual({a.activity_id for a in results}, {2, 3})
        # print(results)

    def test_09_thumbnails(self):
        for i in self.manager_1.activity_ids:
            benchmark = os.path.join(self.TEST_RUN_DATA_DIR_1, 'thumbnails', f'{i}.png')
            fpath = self.manager_1.get_activity_by_id(i).write_thumbnail()
            with open(fpath, 'rb') as f1, open(benchmark, 'rb') as f2:
                self.assertEqual(f1.read(), f2.read())

    def test_10_activity_ids(self):
        self.assertEqual(len(TEST_GPX_FILES), len(self.manager_1.activity_ids))
        for id in self.manager_1.activity_ids:
            a = self.manager_1.get_activity_by_id(id)
            self.assertEqual(id, a.metadata.activity_id)
            self._assert_activities_equal(a, self.manager_1.activities[id])

    def test_11_time(self):
        """Test that the GPX object and the associated Activity have the same time."""

        for a, g in zip(self.activities, self.gpx):
            self.assertEqual(a.metadata.date_time, g.time)

    def test_12_distance(self):
        """Test that the GPX object and the associated Activity have (almost) the same 2d length."""

        for a, g in zip(self.activities, self.gpx):
            self.assertAlmostEqual(a.metadata.distance_2d_km * 1000, g.length_2d(), places=2)

    def test_13_load_metadata(self):
        """Test searching for Activity metadata by activity_id.

        As well as checking that metadata is retrieved correctly, we
        run the searches multiple times to ensure that the
        DatabaseManager has no trouble with, eg, recursive cursors.
        """
        for _ in range(3):
            for _id, _activity in enumerate(self.activities):
                md = self.manager_1.get_activity_by_id(_id).metadata
                self._assert_metadata_equal(md, _activity.metadata)
                self.manager_1.get_activity_by_id(_id)

    def test_14_summarize_activities(self):

        df = self.manager_1.summarize_activity_data()
        #print(df)
        print(df.columns)
        print(df.shape)

    def test_15_config(self):
        """Test equality, loading and saving of configurations."""

        self.assertTrue(self.TEST_CONFIG_1 == self.TEST_CONFIG_1)
        self.assertFalse(self.TEST_CONFIG_1 == self.TEST_CONFIG_2)
        ini_fpath = os.path.join(self.TEST_RUN_DATA_DIR_1, 'test_config.ini')
        self.TEST_CONFIG_1.to_file(ini_fpath, generate_raw=True)
        self.assertEqual(self.TEST_CONFIG_1, Config(ini_fpath))
        raw1 = self.TEST_CONFIG_1.raw()
        raw1.distance_unit = 'test'
        raw1.default_activity_name_format = 'test {distance_2d_%(distance_unit)s}'
        raw1.to_file(ini_fpath)
        raw2 = self.TEST_CONFIG_1.raw()
        raw2.load(ini_fpath)
        interpolated = Config(ini_fpath)
        self.assertEqual(raw1, raw2)
        self.assertNotEqual(raw1, self.TEST_CONFIG_1)
        self.assertNotEqual(raw1, interpolated)
        self.assertEqual(interpolated.default_activity_name_format, 'test {distance_2d_test}')
        self.assertEqual(raw1.default_activity_name_format, 'test {distance_2d_%(distance_unit)s}')



if __name__ == '__main__':
    unittest.main()
