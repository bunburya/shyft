import os
import shutil

import flask
import dash_bootstrap_components as dbc
from pyft.config import Config
from pyft.multi_activity import ActivityManager
from pyft.view import view_activity

### FOR TESTING ONLY

import sys

TEST_DATA_DIR = 'test/test_data'

TEST_GPX_FILES = [
    os.path.join(TEST_DATA_DIR, 'GNR_2019.gpx'),
    os.path.join(TEST_DATA_DIR, 'Morning_Run_Miami.gpx'),
    os.path.join(TEST_DATA_DIR, 'Evening_Run_9k_counterclockwise.gpx'),
    os.path.join(TEST_DATA_DIR, 'Evening_Run_9k_counterclockwise_2.gpx'),
    # os.path.join(TEST_DATA_DIR, 'Afternoon_Run_7.22k_clockwise.gpx'),
    # os.path.join(TEST_DATA_DIR, 'Afternoon_Run_7.23k_counterclockwise.gpx'),
    # os.path.join(TEST_DATA_DIR, 'Morning_Run_7k_counterclockwise.gpx'),
]
TEST_RUN_DATA_DIR = os.path.join(TEST_DATA_DIR, 'dash_run')
if os.path.exists(TEST_RUN_DATA_DIR):
    shutil.rmtree(TEST_RUN_DATA_DIR)

TEST_DB_FILE = os.path.join(TEST_RUN_DATA_DIR, 'dash_test.db')
TEST_CONFIG_FILE = os.path.join(TEST_DATA_DIR, 'test_config.ini')

TEST_CONFIG = Config(
    TEST_CONFIG_FILE,
    data_dir=TEST_RUN_DATA_DIR,
    db_file=TEST_DB_FILE
)

am = ActivityManager(TEST_CONFIG)
for fpath in TEST_GPX_FILES:
    am.add_activity_from_gpx_file(fpath)

activity = am.get_activity_by_id(0)

### /TESTING

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css', dbc.themes.BOOTSTRAP]

server = flask.Flask(__name__)

app = view_activity.get_dash_app(am, TEST_CONFIG,
                                 __name__,
                                 server=server,
                                 external_stylesheets=external_stylesheets,
                                 routes_pathname_prefix='/activity/')

if __name__ == '__main__':
    from sys import argv

    debug = '--debug' in argv
    server.run(host='0.0.0.0', debug=debug, port=8080)
