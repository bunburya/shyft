import logging

from dash import dash
from flask import Flask, redirect, send_file
import dash_bootstrap_components as dbc
import shyft.message as msg
from metadata import APP_NAME
from shyft.logger import get_logger
from shyft.view.controller.main import DashController
from shyft.view.controller.flask_controller import id_str_to_ints, FlaskController

### FOR TESTING ONLY

from test.test_common import *

from werkzeug.exceptions import abort

TEST_DATA_DIR = 'test/test_data'

TEST_RUN_DATA_DIR = run_data_dir('view', replace=False)
TEST_CONFIG_FILE = config_file(TEST_RUN_DATA_DIR)

CONFIG = Config(
    TEST_CONFIG_FILE,
    TEST_ACTIVITY_GRAPHS_FILE,
    TEST_OVERVIEW_GRAPHS_FILE,
    data_dir=TEST_RUN_DATA_DIR
)

am = ActivityManager(CONFIG)
#for fpath in TEST_GPX_FILES:
#    am.add_activity_from_file(fpath)

# logging.getLogger().setLevel(logging.INFO)

### /TESTING
logger = get_logger(file_level=logging.DEBUG, console_level=logging.DEBUG, config=CONFIG)

DATA_DIR = CONFIG.data_dir
TMP_UPLOAD_FOLDER = os.path.join(DATA_DIR, 'tmp_uploads')
if not os.path.exists(TMP_UPLOAD_FOLDER):
    os.makedirs(TMP_UPLOAD_FOLDER)

stylesheets_nondash = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
# stylesheets_dash = stylesheets_nondash + [dbc.themes.BOOTSTRAP]
stylesheets_dash = stylesheets_nondash + [dbc.themes.SANDSTONE]

server = Flask(__name__, template_folder='templates')

# Prevent caching of files (such as thumbnails)
# NOTE: We may actually want to cache when not debugging, as there shouldn't be different activities loaded with the
# same ID in normal usage.
server.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

context = {}

msg_bus = msg.MessageBus()

dash_app = dash.Dash(__name__, server=server, external_stylesheets=stylesheets_dash, title='Shyft')
logger.info('Initialised Dash app.')

flask_controller = FlaskController(am, msg_bus, stylesheets_nondash)
dash_controller = DashController(dash_app, CONFIG, msg_bus, am)


@server.route('/thumbnails/<id>.png')
def get_thumbnail(id: str):
    try:
        activity_id = id_str_to_ints(id)[0]
    except ValueError:
        return abort(404, description=f'Invalid activity ID specified: "{id}".')
    # print(f'Activity with ID {activity_id}: {am.get_metadata_by_id(activity_id)}')
    metadata = am.get_metadata_by_id(activity_id)
    return send_file(metadata.thumbnail_file, mimetype='image/png')


@server.route('/gpx_files/<id>')
def get_gpx_file(id: str):
    logger.debug(f'gpx_files endpoint reached with id "{id}".')
    return flask_controller.serve_files_from_str(id, lambda md: md.gpx_file,
                                                 f'{APP_NAME}_gpx_files.zip',
                                                 'No GPX file found for activity ID {id}.')


@server.route('/tcx_files/<id>')
def get_tcx_file(id: str):
    logger.debug(f'tcx_files endpoint reached with id "{id}".')
    return flask_controller.serve_files_from_str(id, lambda md: md.tcx_file,
                                                 f'{APP_NAME}_tcx_files.zip',
                                                 'No TCX file found for activity ID {id}.')


@server.route('/source_files/<id>')
def get_source_file(id: str):
    logger.debug(f'source_files endpoint reached with id "{id}".')
    return flask_controller.serve_files_from_str(id, lambda md: md.source_file,
                                                 f'{APP_NAME}_source_files.zip',
                                                 'No source file found for activity ID {id}.')


@server.route('/delete/<id>')
def delete(id: str):

    try:
        activity_ids = id_str_to_ints(id)
    except ValueError:
        return abort(404, f'Query contains bad activity IDs.')
    for i in activity_ids:
        try:
            am.delete_activity(i)
        except ValueError:
            msg_bus.add_message(f'Could not delete activity with ID {i}. It may not exist.', logging.ERROR)
    if len(activity_ids) == 1:
        msg_bus.add_message(f'Deleted activity with ID {i}.')
    else:
        msg_bus.add_message(f'Deleted {len(activity_ids)} activities.')
    return redirect('/')

if __name__ == '__main__':
    dash_app.run_server(debug=True, port=8080, use_reloader=False)
