import os
import unittest

from pyft.config import Config
from pyft.serialize.parse import parser_factory, GPXParser, FITParser, TCXParser
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

RUN_DIR_GARMINTCX = run_data_dir(RUN_DIR_BASE + '_GarminTCX', replace=True)  # For Garmin TCX-generated activities
CONFIG_GARMINTCX = get_config(RUN_DIR_GARMINTCX)

RUN_DIR_PYFTGPX = run_data_dir(RUN_DIR_BASE + '_PyftGPX', replace=True)  # For PyftGPX-generated activities
CONFIG_PYFTGPX = get_config(RUN_DIR_PYFTGPX)


NEW_GPX_DIR = os.path.join(RUN_DIR_PYFTGPX, 'generated_gpx')
if not os.path.exists(NEW_GPX_DIR):
    os.makedirs(NEW_GPX_DIR)

class SerializeTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.manager_stravagpx = cls.get_manager(CONFIG_STRAVAGPX, files=TEST_GPX_FILES_2)
        cls.manager_fit = cls.get_manager(CONFIG_FIT, files=TEST_FIT_FILES)
        cls.manager_garmintcx = cls.get_manager(CONFIG_GARMINTCX, files=TEST_TCX_FILES)
        cls.strava_gpx = []
        for i, fpath in enumerate(TEST_GPX_FILES_2):
            with open(fpath) as f:
                cls.strava_gpx.append(gpxpy.parse(f))
        #print(cls.manager_stravagpx.activity_ids)

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
        for tcx_file in TEST_TCX_FILES:
            parser = parser_factory(os.path.join(TEST_TCX_FILES_DIR, tcx_file), CONFIG_GARMINTCX)
            self.assertIsInstance(parser, TCXParser)

    def test_02_create_gpx(self):
        """Test that we can create GPX files and load those files again."""
        manager_pyftgpx = self.get_manager(CONFIG_PYFTGPX)
        for activity in self.manager_stravagpx:
            activity_id = activity.metadata.activity_id
            #print(f'_activity_elem: {activity_id}')
            fpath = os.path.join(NEW_GPX_DIR, f'{activity_id}.gpx')
            activity.to_gpx_file(fpath)
            manager_pyftgpx.add_activity_from_file(fpath)
        self._assert_managers_equal(self.manager_stravagpx, manager_pyftgpx)

    def test_03_fit_gpx_parser_equal(self):
        """Test that the Activity generated from the GPX file and the
        FIT file are (roughly) equivalent.
        """
        _id = 0
        for g, f in zip(TEST_GPX_FILES_2, TEST_FIT_FILES):
            gpx_activity = Activity.from_file(g, CONFIG_STRAVAGPX, activity_id=_id)
            fit_activity = Activity.from_file(f, CONFIG_FIT, activity_id=_id)
            self._assert_activities_equal(
                gpx_activity,
                fit_activity,
                almost=True,
                check_data_files=False,
                check_laps=False
            )
            _id += 1

    def test_04_fit_tcx_parser_equal(self):
        """Test that the Activity generated from the TCX file and the
        FIT file are (roughly) equivalent.
        """
        #print('BEGINNING TCX TEST')
        for tcx_activity, fit_activity in zip(self.manager_garmintcx, self.manager_fit):
            if tcx_activity.metadata.activity_type == CONFIG_GARMINTCX.default_activity_type:
                # For some reason, Garmin-generated TCX files for non-running activities do not include cadence for me,
                # even though the associated FIT file does.
                ignore_points_cols = ['cadence']
            else:
                ignore_points_cols = []
            self._assert_activities_equal(
                tcx_activity,
                fit_activity,
                almost=True,
                check_data_files=False,
                check_types=False,
                ignore_points_cols=ignore_points_cols
            )

    def test_05_source_save(self):
        """Test that source files are properly saved."""
        for activity, gpx_file in zip(self.manager_stravagpx, TEST_GPX_FILES_2):
            self._assert_files_equal(activity.metadata.source_file, gpx_file)
        manager_fit = self.get_manager(CONFIG_FIT, TEST_FIT_FILES)
        for activity, fit_file in zip(manager_fit, TEST_FIT_FILES):
            self._assert_files_equal(activity.metadata.source_file, fit_file)

    def test_06_gpx_length(self):
        """Test that the length we calculate for activities generated
        from GPX files is the same as the length calculated by gpxpy.
        There is some tolerance of small discrepancies as there may be
        rounding differences.
        """
        for activity, gpx in zip(self.manager_stravagpx, self.strava_gpx):
            self.assertAlmostEqual(activity.metadata.distance_2d_km * 1000, gpx.length_2d(), places=3)

    def test_07_laps(self):
        """Test that laps have been created correctly."""
        for activity in self.manager_stravagpx:
            self.assertIsNone(activity.laps)
        for activity in self.manager_fit:
            laps = activity.laps
            self.assertIsInstance(laps, pd.DataFrame)
            self.assertAlmostEqual(laps['distance'].sum(), activity.metadata.distance_2d_km * 1000, places=3)
            self.assertAlmostEqual(laps['duration'].sum(), activity.metadata.duration)

if __name__ == '__main__':
    unittest.main()