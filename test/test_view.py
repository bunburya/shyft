import os
import shutil

import flask
import dash_bootstrap_components as dbc
from pyft.config import Config
from pyft.multi_activity import ActivityManager
from pyft.view import view_activity, overview

### FOR TESTING ONLY

import sys

TEST_DATA_DIR = 'test/test_data'

TEST_GPX_FILES = [
    os.path.join(TEST_DATA_DIR, 'GNR_2019.gpx'),
    os.path.join(TEST_DATA_DIR, 'Morning_Run_Miami.gpx'),
    os.path.join(TEST_DATA_DIR, '2020_08_05_pp_9k_ccw.gpx'),
    os.path.join(TEST_DATA_DIR, '2020_08_04_pp_9k_ccw.gpx'),
    os.path.join(TEST_DATA_DIR, '2020_03_20_pp_7.22k_cw.gpx'),
    os.path.join(TEST_DATA_DIR, '2020_06_18_pp_7.23k_ccw.gpx'),
    os.path.join(TEST_DATA_DIR, '2019_07_08_pp_7k_ccw.gpx'),
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

overview_app = overview.get_dash_app(am, TEST_CONFIG,
                                     __name__,
                                     server=server,
                                     external_stylesheets=external_stylesheets)

view_activity_app = view_activity.get_dash_app(am, TEST_CONFIG,
                                               __name__,
                                               server=server,
                                               external_stylesheets=external_stylesheets,
                                               routes_pathname_prefix='/activity/')


@server.route('/thumbnails/<id>.png')
def get_thumbnail(id: str):
    # TODO:  Probably better if we just statically serve the thumbnails.
    try:
        activity_id = int(id)
    except (ValueError, TypeError):
        activity_id = None
    if activity_id is None:
        return f'Invalid activity ID specified: "{id}".'
    metadata = am.get_metadata_by_id(activity_id)
    return flask.send_file(metadata.thumbnail_file, mimetype='image/png')


if __name__ == '__main__':
    from sys import argv

    debug = '--debug' in argv
    server.run(host='0.0.0.0', debug=debug, port=8080)
