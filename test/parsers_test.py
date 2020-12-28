import os
import unittest

from pyft.config import Config
from pyft.parse.parsers import parser_factory, GPXParser, FITParser
from test.test_base import *

RUN_DIR = run_data_dir('parsers', True)
CONFIG_FILE = config_file(RUN_DIR)
CONFIG = Config(CONFIG_FILE)

class ParsersTestCase(BaseTestCase):

    def test_01_parser_factory(self):
        """Test that the parser factory returns the correct type of
        parser. Also tests that the parser is basically capable of
        initialising and parsing a file.
        """
        for gpx_file in TEST_GPX_FILES_2:
            parser = parser_factory(gpx_file, CONFIG)
            self.assertIsInstance(parser, GPXParser)
        for fit_file in TEST_FIT_FILES:
            parser = parser_factory(os.path.join(TEST_FIT_FILES_DIR, fit_file), CONFIG)
            self.assertIsInstance(parser, FITParser)

    def test_02_equal(self):
        """Test that the Activity generated from the GPX file and the
        FIT file are equivalent.
        """
        _id = 0
        for g, f in zip(TEST_GPX_FILES_2, TEST_FIT_FILES):
            print(f'Testing {g} against {f}.')
            gpx_activity = Activity.from_file(g, CONFIG, activity_id=_id)
            fit_activity = Activity.from_file(f, CONFIG, activity_id=_id)
            gpx_activity.points.to_csv(g+'.csv')
            fit_activity.points.to_csv(f+'.csv')
            self._assert_activities_equal(
                gpx_activity,
                fit_activity,
                almost=True,
                check_data_files=False
            )
            _id += 1

if __name__ == '__main__':
    unittest.main()
