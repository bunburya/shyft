import logging
from datetime import datetime, date

from shyft.df_utils.schemas import metadata_time_series_schema
from shyft.logger import get_logger
from test.test_utils.test_common import *

logger = get_logger(file_level=logging.DEBUG, console_level=logging.WARN,
                    log_file=os.path.join(TEST_LOGS_DIR, 'multi_activity.log'))


class ActivityManagerTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls):

        cls.TEST_RUN_DATA_DIR_1 = run_data_dir('1', replace=True)
        cls.TEST_RUN_DATA_DIR_2 = run_data_dir('2', replace=True)
        cls.TEST_RUN_DATA_DIR_3 = run_data_dir('3', replace=True)

        cls.TEST_CONFIG_1 = get_config(cls.TEST_RUN_DATA_DIR_1)
        cls.TEST_CONFIG_2 = get_config(cls.TEST_RUN_DATA_DIR_2)
        cls.TEST_CONFIG_3 = get_config(cls.TEST_RUN_DATA_DIR_3)

        cls.gpx = []
        cls.activities = []
        for i, fpath in enumerate(TEST_GPX_FILES):
            with open(fpath) as f:
                cls.gpx.append(gpxpy.parse(f))
            cls.activities.append(Activity.from_file(fpath, cls.TEST_CONFIG_1, activity_id=i))
        cls.proto_ids = {}
        cls.fpath_ids = {}
        cls.manager_1 = get_manager(cls.TEST_CONFIG_1)  # Add Activities directly (populate in setUp and use as the
                                                            # base for most tests)
        cls.manager_2 = get_manager(cls.TEST_CONFIG_2)  # Add Activities from filepaths
        cls.manager_3 = get_manager(cls.TEST_CONFIG_3)  # Add Activities directly (just to test adding)

        for a in cls.activities:
            cls.manager_1.add_activity(a)

        # cls.manager_1.dbm.connection.set_trace_callback(print)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.TEST_RUN_DATA_DIR_1):
            shutil.rmtree(cls.TEST_RUN_DATA_DIR_1)
        if os.path.exists(cls.TEST_RUN_DATA_DIR_2):
            shutil.rmtree(cls.TEST_RUN_DATA_DIR_2)
        if os.path.exists(cls.TEST_RUN_DATA_DIR_3):
            shutil.rmtree(cls.TEST_RUN_DATA_DIR_3)

    def test_01_setup(self):
        """Perform some basic checks to ensure the test is set up properly."""

        print(self.manager_1.summarize_metadata()['month'])
        self.assert_manager_valid(self.manager_1)


        self.assertEqual(len(TEST_GPX_FILES), len(self.activities))
        self.assertEqual(len(TEST_GPX_FILES), len(self.gpx))
        db1 = self.manager_1.dbm
        db1.cursor.execute('SELECT name from sqlite_master where type= "table"')
        tables = {i[0] for i in db1.cursor.fetchall()}
        self.assertSetEqual(tables, {'prototypes', 'activities', 'points', 'laps'})
        db2 = self.manager_2.dbm
        db2.cursor.execute('SELECT name from sqlite_master where type= "table"')
        self.assertSetEqual({i[0] for i in db2.cursor.fetchall()}, tables)

        manager_copy = copy_manager(self.manager_1)
        self.assert_managers_equal(self.manager_1, manager_copy)

    def test_02_add_activity(self):
        """Test basic adding of activities."""

        activities = []
        for i, fpath in enumerate(TEST_GPX_FILES):
            with open(fpath) as f:
                self.gpx.append(gpxpy.parse(f))
            activities.append(Activity.from_file(fpath, self.TEST_CONFIG_3, activity_id=i))


        for a in activities:
            # print(a.metadata.gpx_file, a.metadata.date_time)
            self.assertIsNotNone(a.metadata.activity_id)
            self.assertIsNone(a.metadata.prototype_id)
            self.manager_3.add_activity(a)
            self.assertIsNotNone(a.metadata.activity_id)
            self.assertIsNotNone(a.metadata.prototype_id)
            self.proto_ids[a.metadata.activity_id] = a.metadata.prototype_id
            self.assert_activities_equal(a, self.manager_3.get_activity_by_id(a.metadata.activity_id))

    def test_03_add_activity_from_file(self):
        """Test basic adding of activities from filepaths, including
        that the results are the same as adding activities directly.
        """

        for fpath in TEST_GPX_FILES:
            _id = self.manager_2.add_activity_from_file(fpath)
            self.fpath_ids[fpath] = _id

        for a1, a2 in zip(self.manager_1, self.manager_2):
            #print(a1, a2)
            self.assert_activities_equal(a1, a2)

        self.assertSequenceEqual(self.manager_1.prototypes, self.manager_2.prototypes)

    def test_04_test_loose_matching(self):

        print(self.fpath_ids)

        for i1, i2 in LOOSE_MATCH:
            id1 = self.fpath_ids[TEST_GPX_FILES[i1]]
            id2 = self.fpath_ids[TEST_GPX_FILES[i2]]
            a1 = self.manager_1.get_activity_by_id(id1)
            a2 = self.manager_1.get_activity_by_id(id2)
            print(f'a1 {i1} {self.fpath_ids[TEST_GPX_FILES[i1]]} {a1}')
            print(f'a2 {i2} {self.fpath_ids[TEST_GPX_FILES[i2]]} {a2}')
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
        """Test that we can determine whether an activity's route is
        unique (ie, does not match any other activity's route).
        """
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

        for a in self.manager_1:
            p = self.manager_1.get_activity_by_id(a.metadata.prototype_id)
            self.assertTrue(self.manager_1.tight_match_routes(a, p))

    def test_08_search(self):
        """Test searching for activities."""

        # Test time range matching
        results = self.manager_1.search_metadata(from_date=datetime(2019, 1, 1), to_date=datetime(2020, 1, 1))
        self.assertSetEqual({a.activity_id for a in results}, set(ACTIVITIES_2019))

        # Test prototype matching
        results = self.manager_1.search_metadata(prototype=2)
        self.assertSetEqual({a.activity_id for a in results}, {2, 3})

        # Test ID and time range matching
        results = self.manager_1.search_metadata(from_date=datetime(2019, 1, 1), to_date=datetime(2020, 1, 1),
                                                 ids=[6, 7, 8, 9, 15])
        self.assertSetEqual({a.activity_id for a in results}, {6, 7, 8, 9})

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
            self.assert_activities_equal(a, self.manager_1[id])

    def test_11_time(self):
        """Test that the GPX object and the associated Activity have the same time."""

        for a, g in zip(self.activities, self.gpx):
            self.assertEqual(a.metadata.date_time, g.time)

    def test_12_load_metadata(self):
        """Test searching for Activity metadata by activity_id.

        As well as checking that metadata is retrieved correctly, we
        run the searches multiple times to ensure that the
        DatabaseManager has no trouble with, eg, recursive cursors.
        """
        for _ in range(3):
            for _id, _activity in enumerate(self.activities):
                md = self.manager_1.get_activity_by_id(_id).metadata
                self.assert_metadata_equal(md, _activity.metadata)
                self.manager_1.get_activity_by_id(_id)

    def test_13_summarize_activities(self):

        df = self.manager_1.summarize_metadata()
        #print(df)
        print(df.columns)
        print(df.shape)

    def test_14_config(self):
        """Test equality, loading and saving of configurations."""

        self.assertTrue(self.TEST_CONFIG_1 == self.TEST_CONFIG_1)
        self.assertFalse(self.TEST_CONFIG_1 == self.TEST_CONFIG_2)
        ini_fpath = os.path.join(self.TEST_RUN_DATA_DIR_1, 'test_config.ini')
        self.TEST_CONFIG_1.to_file(ini_fpath)
        self.assertEqual(self.TEST_CONFIG_1, Config(ini_fpath))

    def test_15_iter(self):
        """Test iterating through ActivityManager."""
        self.assertEqual(len(self.manager_1), len(self.activities))
        count = 0
        for a1, a2 in zip(self.manager_1, self.activities):
            self.assertIsInstance(a1, Activity)
            self.assertEquals(a1.metadata.activity_id, a2.metadata.activity_id)
            count += 1
        self.assertEquals(count, len(self.manager_1))

    def test_16_delete(self):
        """Test deleting an activity."""

        # TODO: Operate on copy of manager_1, so that manager_1 is preserved for subsequent tests

        reduced_activities = self.activities[:]
        manager = copy_manager(self.manager_1)

        # Test assumptions
        self.assertEqual(manager[3].metadata.prototype_id, 2)
        self.assertIn(0, manager.prototypes)
        self.assertIn(2, manager.prototypes)

        # Remove Activity 2; Activity 3 should become its own prototype.
        reduced_activities.pop(2)
        manager.delete_activity(2)
        self.assertRaises(KeyError, lambda: manager[2])
        #print(self.manager_1[2])
        self.assertEqual(len(manager), len(reduced_activities))
        for a1, a2 in zip(manager, reduced_activities):
            self.assertEqual(a1.metadata.activity_id, a2.metadata.activity_id)
        self.assertEqual(manager[3].metadata.prototype_id, 3)
        self.assertNotIn(2, manager.prototypes)
        self.assertIn(3, manager.prototypes)

        # Remove Activity 0; it is already its own prototype (and there are no matches),
        # so it should cease to be a prototype.
        reduced_activities.pop(0)
        manager.delete_activity(0)
        self.assertRaises(KeyError, lambda: manager[0])
        self.assertEqual(len(manager), len(reduced_activities))
        for a1, a2 in zip(manager, reduced_activities):
            self.assertEqual(a1.metadata.activity_id, a2.metadata.activity_id)
        self.assertNotIn(0, manager.prototypes)

        # Try remove an Activity that is not present
        self.assertRaises(ValueError, lambda: self.manager_1.delete_activity(444))

        # Delete all activities.
        for i in manager.activity_ids:
            manager.delete_activity(i)
        self.assertListEqual(manager.activity_ids, [])
        self.assertListEqual(manager.all_metadata, [])
        self.assertListEqual(manager.prototypes, [])

    def test_17_get_week(self):
        """Test getting metadata for all activities in a given week."""

        start1 = datetime(2020, 8, 3)
        results1 = self.manager_1.get_metadata_by_week(start1)
        self.assert_metadata_iterable_equal(results1, [2, 3])
        start2 = datetime(2020, 10, 10)
        results2 = self.manager_1.get_metadata_by_week(start2)
        self.assert_metadata_iterable_equal(results2, [15, 16])
        start3 = datetime(2019, 9, 2)
        results3 = self.manager_1.get_metadata_by_week(start3)
        self.assert_metadata_iterable_equal(results3, [0])
        start4 = datetime(2018, 8, 8)
        results4 = self.manager_1.get_metadata_by_week(start4)
        self.assert_metadata_iterable_equal(results4, [])

    def test_18_get_month(self):
        """Test getting metadata for all activities in a given month."""
        results1 = self.manager_1.get_metadata_by_month(datetime(2020, 8, 1))
        self.assert_metadata_iterable_equal(results1, [2, 3])
        results2 = self.manager_1.get_metadata_by_month(datetime(2020, 8, 1), activity_type='walk')
        self.assert_metadata_iterable_equal(results2, [])
        results3 = self.manager_1.get_metadata_by_month(datetime(2020, 8, 1), activity_type='run')
        self.assert_metadata_iterable_equal(results3, [2, 3])

    def test_19_time_series(self):
        """Test generation of time series data."""
        weekly = self.manager_1.metadata_weekly_time_series(date(2019, 1, 1))
        self.assert_dataframe_valid(weekly, metadata_time_series_schema)
        weekly_runs = self.manager_1.metadata_weekly_time_series(date(2019, 1, 1), activity_type='run')
        self.assert_dataframe_valid(weekly_runs, metadata_time_series_schema)
        monthly = self.manager_1.metadata_monthly_time_series(date(2019, 1, 1))
        self.assert_dataframe_valid(monthly, metadata_time_series_schema)
        monthly_runs = self.manager_1.metadata_monthly_time_series(date(2019, 1, 1), activity_type='run')
        self.assert_dataframe_valid(monthly_runs, metadata_time_series_schema)

    def test_20_activity_types(self):
        """Test fetching all present activity types."""
        manager = copy_manager(self.manager_1)
        types = set()
        for a in manager:
            types.add(a.metadata.activity_type)
        self.assertTrue(types)
        self.assertSetEqual(types, manager.activity_types)
        for t in ('walk', 'run'):
            types.remove(t)
            for a in manager:
                if a.metadata.activity_type == t:
                    manager.delete_activity(a.metadata.activity_id)
            self.assertSetEqual(types, manager.activity_types)


if __name__ == '__main__':
    unittest.main()
