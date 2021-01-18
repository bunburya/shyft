import os
import unittest

from pyft.config import Config
from pyft.serialize.parse import parser_factory, GPXParser, FITParser
from test.test_common import *

RUN_DIR_BASE = 'serialize'

# Generate run data directories and config files, etc, for different ActivityManagers
# - one ActivityManager loads Activities from the Strava GPX files,
# - one loads Activities from the Garmin .FIT files, and
# - one loads Activities from the Pyft GPX files.

RUN_DIR_STRAVAGPX = run_data_dir(RUN_DIR_BASE + '_StravaGPX', replace=True)  # For StravaGPX-generated activities
CONFIG_STRAVAGPX = get_config(RUN_DIR_STRAVAGPX)

RUN_DIR_FIT = run_data_dir(RUN_DIR_BASE + '_FIT', replace=True)  # For .FIT-generated activities
CONFIG_FIT = get_config(RUN_DIR_FIT)

RUN_DIR_PYFTGPX = run_data_dir(RUN_DIR_BASE + '_PyftGPX', replace=True)  # For PyftGPX-generated activities
CONFIG_PYFTGPX = get_config(RUN_DIR_PYFTGPX)


NEW_GPX_DIR = os.path.join(RUN_DIR_PYFTGPX, 'generated_gpx')
if not os.path.exists(NEW_GPX_DIR):
    os.makedirs(NEW_GPX_DIR)

class SerializeTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.manager_stravagpx = cls.get_manager(CONFIG_STRAVAGPX, files=TEST_GPX_FILES_2)
        print(cls.manager_stravagpx.activity_ids)

    #@classmethod
    #def tearDownClass(cls):
    #    if os.path.exists(RUN_DIR):
    #        shutil.rmtree(RUN_DIR)

    def test_01_parser_factory(self):
        """Test that the parser factory returns the correct type of
        parser. Also tests that the parser is basically capable of
        initialising and parsing a file.
        """
        for gpx_file in TEST_GPX_FILES_2:
            parser = parser_factory(gpx_file, CONFIG_STRAVAGPX)
            self.assertIsInstance(parser, GPXParser)
        for fit_file in TEST_FIT_FILES:
            parser = parser_factory(os.path.join(TEST_FIT_FILES_DIR, fit_file), CONFIG_FIT)
            self.assertIsInstance(parser, FITParser)

    def test_02_create_gpx(self):
        manager_pyftgpx = self.get_manager(CONFIG_PYFTGPX)
        for activity in self.manager_stravagpx:
            activity_id = activity.metadata.activity_id
            #print(f'activity: {activity_id}')
            fpath = os.path.join(NEW_GPX_DIR, f'{activity_id}.gpx')
            activity.to_gpx_file(fpath)
            manager_pyftgpx.add_activity_from_file(fpath)
        self._assert_managers_equal(self.manager_stravagpx, manager_pyftgpx)

    def test_03_fit_gpx_parser_equal(self):
        """Test that the Activity generated from the GPX file and the
        FIT file are equivalent.
        """
        _id = 0
        for g, f in zip(TEST_GPX_FILES_2, TEST_FIT_FILES):
            print(f'Testing {g} against {f}.')
            gpx_activity = Activity.from_file(g, CONFIG_STRAVAGPX, activity_id=_id)
            fit_activity = Activity.from_file(f, CONFIG_FIT, activity_id=_id)
            #gpx_activity.points.to_csv(g+'.csv')
            #fit_activity.points.to_csv(f+'.csv')
            self._assert_activities_equal(
                gpx_activity,
                fit_activity,
                almost=True,
                check_data_files=False
            )
            _id += 1

    def test_04_source_save(self):
        """Test that source files are properly saved."""
        for activity, gpx_file in zip(self.manager_stravagpx, TEST_GPX_FILES_2):
            self._assert_files_equal(activity.metadata.source_file, gpx_file)
        manager_fit = self.get_manager(CONFIG_FIT, TEST_FIT_FILES)
        for activity, fit_file in zip(manager_fit, TEST_FIT_FILES):
            self._assert_files_equal(activity.metadata.source_file, fit_file)

if __name__ == '__main__':
    unittest.main()
