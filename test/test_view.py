import logging

from dash import dash
from flask import Flask, redirect, send_file
import dash_bootstrap_components as dbc
import shyft.message as msg
from shyft.logger import get_logger
from shyft.view.controller.main import DashController
from shyft.view.controller.flask_controller import id_str_to_int, FlaskController

### FOR TESTING ONLY

from test.test_common import *

from werkzeug.exceptions import abort

TEST_DATA_DIR = 'test/test_data'

TEST_RUN_DATA_DIR = run_data_dir('view', replace=True)
TEST_CONFIG_FILE = config_file(TEST_RUN_DATA_DIR)

CONFIG = Config(
    TEST_CONFIG_FILE,
    TEST_ACTIVITY_GRAPHS_FILE,
    TEST_OVERVIEW_GRAPHS_FILE,
    data_dir=TEST_RUN_DATA_DIR
)

am = ActivityManager(CONFIG)
for fpath in TEST_GPX_FILES:
    am.add_activity_from_file(fpath)

# logging.getLogger().setLevel(logging.INFO)

### /TESTING
logger = get_logger(file_level=logging.DEBUG, console_level=logging.DEBUG, config=CONFIG)

DATA_DIR = CONFIG.data_dir
TMP_UPLOAD_FOLDER = os.path.join(DATA_DIR, 'tmp_uploads')
if not os.path.exists(TMP_UPLOAD_FOLDER):
    os.makedirs(TMP_UPLOAD_FOLDER)

stylesheets_nondash = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
stylesheets_dash = stylesheets_nondash + [dbc.themes.BOOTSTRAP]

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
dash_controller = DashController(dash_app, CONFIG, am)


@server.route('/thumbnails/<id>.png')
def get_thumbnail(id: str):
    try:
        activity_id = id_str_to_int(id)
    except ValueError:
        return abort(404, description=f'Invalid activity ID specified: "{id}".')
    # print(f'Activity with ID {activity_id}: {am.get_metadata_by_id(activity_id)}')
    metadata = am.get_metadata_by_id(activity_id)
    return send_file(metadata.thumbnail_file, mimetype='image/png')


@server.route('/gpx_files/<id>')
def get_gpx_file(id: str):
    return flask_controller.serve_file(id, lambda md: md.gpx_file, 'No GPX file found for activity ID {id}.')


@server.route('/tcx_files/<id>')
def get_tcx_file(id: str):
    return flask_controller.serve_file(id, lambda md: md.tcx_file, 'No TCX file found for activity ID {id}.')


@server.route('/source_files/<id>')
def get_source_file(id: str):
    return flask_controller.serve_file(id, lambda md: md.source_file, 'No source file found for activity ID {id}.')


@server.route('/delete/<id>')
def delete(id: str):
    try:
        activity_id = id_str_to_int(id)
        am.delete_activity(activity_id)
        msg_bus.add_message(f'Deleted activity with ID {activity_id}.')
        return redirect('/')
    except ValueError:
        # This should catch ValueErrors raise by either id_str_to_int or am.delete_activity
        return abort(404, f'No activity found with ID {id} (or there was some other error).')


if __name__ == '__main__':
    dash_app.run_server(debug=True, port=8080, use_reloader=False)
