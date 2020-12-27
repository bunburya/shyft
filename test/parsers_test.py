import os
import unittest

from pyft.config import Config
from pyft.parse.parsers import parser_factory, GPXParser, FITParser
from test.test_vars import *

RUN_DIR = run_data_dir('parsers', True)
CONFIG_FILE = config_file(RUN_DIR)
CONFIG = Config(CONFIG_FILE)

class ParsersTestCase(unittest.TestCase):

    def test_01_parser_factory(self):
        """Test that the parser factory returns the correct type of
        parser. Also tests that the parser is basically capable of
        initialising and parsing a file.
        """
        for gpx_file in TEST_GPX_FILES:
            parser = parser_factory(gpx_file, CONFIG)
            self.assertIsInstance(parser, GPXParser)
        for fit_file in os.listdir(TEST_FIT_FILES_DIR):
            parser = parser_factory(os.path.join(TEST_FIT_FILES_DIR, fit_file), CONFIG)
            self.assertIsInstance(parser, FITParser)


if __name__ == '__main__':
    unittest.main()
