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
    os.path.join(TEST_DATA_DIR, 'GNR_2019.gpx'),                    # 0     2019-09-08
    os.path.join(TEST_DATA_DIR, 'Morning_Run_Miami.gpx'),           # 1     2019-10-30
    os.path.join(TEST_DATA_DIR, '2020_08_05_pp_9k_ccw.gpx'),        # 2     2020-08-05
    os.path.join(TEST_DATA_DIR, '2020_08_04_pp_9k_ccw.gpx'),        # 3     2020-08-04
    os.path.join(TEST_DATA_DIR, '2020_03_20_pp_7.22k_cw.gpx'),      # 4     2020-03-20
    os.path.join(TEST_DATA_DIR, '2020_06_18_pp_7.23k_ccw.gpx'),     # 5     2020-06-18
    os.path.join(TEST_DATA_DIR, '2019_07_08_pp_7k_ccw.gpx'),        # 6     2019-07-08
    os.path.join(TEST_DATA_DIR, 'Calcutta_Run_10k_2019.gpx'),       # 7     2019
    os.path.join(TEST_DATA_DIR, 'cuilcagh_walk_2019.gpx'),          # 8     2019
    os.path.join(TEST_DATA_DIR, 'fermanagh_walk_2019.gpx'),         # 9     2019
    os.path.join(TEST_DATA_DIR, 'Frank_Duffy_10_Mile_2019.gpx'),    # 10    2019
    os.path.join(TEST_DATA_DIR, 'Great_Ireland_Run_2019.gpx'),      # 11    2019
    os.path.join(TEST_DATA_DIR, 'howth_walk_2019.gpx'),             # 12    2019
    os.path.join(TEST_DATA_DIR, 'Irish_Runner_10_Mile_2019.gpx'),   # 13    2019
    os.path.join(TEST_DATA_DIR, 'run_in_the_dark_10k_2019.gpx'),    # 14    2019
]

TEST_RUN_DATA_DIR = os.path.join(TEST_DATA_DIR, 'dash_run')
if os.path.exists(TEST_RUN_DATA_DIR):
    shutil.rmtree(TEST_RUN_DATA_DIR)

TEST_DB_FILE = os.path.join(TEST_RUN_DATA_DIR, 'dash_test.db')
TEST_CONFIG_FILE = os.path.join(TEST_DATA_DIR, 'test_config.ini')
TEST_ACTIVITY_GRAPHS_FILE = os.path.join(TEST_DATA_DIR, 'test_activity_graphs.json')

TEST_CONFIG = Config(
    TEST_CONFIG_FILE,
    TEST_ACTIVITY_GRAPHS_FILE,
    data_dir=TEST_RUN_DATA_DIR,
    db_file=TEST_DB_FILE
)

am = ActivityManager(TEST_CONFIG)
for fpath in TEST_GPX_FILES:
    am.add_activity_from_gpx_file(fpath)

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


def id_to_int(id: str) -> int:
    """Convert a string activity id to an integer, performing some
    basic verification and raising a ValueError is the given id is
    note valid.
    """
    try:
        activity_id = int(id)
    except (ValueError, TypeError):
        activity_id = None
    if activity_id is None:
        raise ValueError(f'Bad activity id: "{id}".')
    return activity_id


@server.route('/thumbnails/<id>.png')
def get_thumbnail(id: str):
    # TODO:  Probably better if we just statically serve the thumbnails.
    try:
        activity_id = id_to_int(id)
    except ValueError:
        return f'Invalid activity ID specified: "{id}".'
    # print(f'Activity with ID {activity_id}: {am.get_metadata_by_id(activity_id)}')
    metadata = am.get_metadata_by_id(activity_id)
    return flask.send_file(metadata.thumbnail_file, mimetype='image/png')


@server.route('/gpx_files/<id>.gpx')
def get_gpx_file(id: str):
    try:
        activity_id = id_to_int(id)
    except ValueError:
        return f'Invalid activity ID specified: "{id}".'
    metadata = am.get_metadata_by_id(activity_id)
    return flask.send_file(metadata.data_file, mimetype='application/gpx+xml')


if __name__ == '__main__':
    from sys import argv

    debug = '--debug' in argv
    server.run(host='0.0.0.0', debug=debug, port=8080)
