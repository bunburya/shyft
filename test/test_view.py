import logging
from typing import Callable, Any, Dict

from flask import Flask, url_for, render_template, redirect, send_file, flash, request, g
import dash_bootstrap_components as dbc
import shyft.message as msg
from shyft.logger import get_logger
from shyft.metadata import APP_NAME, VERSION, URL
from shyft.view.flask_controller import FlaskController, id_str_to_int
from shyft.view.overview import Overview

from shyft.serialize.parse import PARSERS

### FOR TESTING ONLY
from shyft.view.upload import UploadForm

from test.test_common import *

from shyft.view.edit_config import ConfigForm
from shyft.view.view_activity import ActivityView
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename

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

logging.getLogger().setLevel(logging.INFO)

### /TESTING
logger = get_logger(file_level=logging.DEBUG, console_level=logging.DEBUG, config=CONFIG)

DATA_DIR = CONFIG.data_dir
TMP_UPLOAD_FOLDER = os.path.join(DATA_DIR, 'tmp_uploads')
if not os.path.exists(TMP_UPLOAD_FOLDER):
    os.makedirs(TMP_UPLOAD_FOLDER)


stylesheets_nondash = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
stylesheets_dash = stylesheets_nondash + [dbc.themes.BOOTSTRAP]

server = Flask(__name__, template_folder='templates')
server.secret_key = 'TEST_KEY'

context = {}

msg_bus = msg.MessageBus()

overview = Overview(am, msg_bus, CONFIG, __name__, server=server, external_stylesheets=stylesheets_dash)

activity_view = ActivityView(am, msg_bus, CONFIG, __name__, server=server, external_stylesheets=stylesheets_dash,
                             routes_pathname_prefix='/activity/')

flask_controller = FlaskController(am, msg_bus, stylesheets_nondash)

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


@server.route('/config', methods=['GET', 'POST'])
def config():
    # https://hackersandslackers.com/flask-wtforms-forms/
    raw_config = CONFIG.raw()
    form = ConfigForm(obj=raw_config)
    if form.validate_on_submit():
        logging.info('Saving configuration data.')
        form.populate_obj(raw_config)
        raw_config.to_file(TEST_CONFIG_FILE)
        # Have to load again to get the interpolation working right
        CONFIG.load(TEST_CONFIG_FILE)
        overview.update_layout()
        # return redirect(url_for('save_config'))
        msg_bus.add_message('Configuration saved.')
    logging.info('Displaying configuration page.')
    return render_template('config.html.jinja', form=form, **flask_controller.get_flask_rendering_data('Configure'))


@server.route('/upload', methods=['GET', 'POST'])
def upload_file():
    form = UploadForm()
    if form.validate_on_submit():
        f = form.upload_file.data
        filename = secure_filename(f.filename)
        logger.info(f'Received file "{filename}"; attempting to add activity.')
        fpath = os.path.join(TMP_UPLOAD_FOLDER, filename)
        f.save(fpath)
        try:
            id = am.add_activity_from_file(fpath)
            overview.update_layout()
            logger.info(f'Added new activity with ID {id}.')
            return redirect(f'/activity/{id}')
        except Exception as e:
            logger.error(f'Could not add new activity.')
            msg_bus.add_message('Could not upload new activity. Check logs for details.')
    logger.info('Displaying file upload page.')
    return render_template('upload.html.jinja', form=form, **flask_controller.get_flask_rendering_data('Upload'))


@server.route('/delete/<id>')
def delete(id: str):
    try:
        activity_id = id_str_to_int(id)
        am.delete_activity(activity_id)
        msg_bus.add_message(f'Deleted activity with ID {activity_id}.')
        overview.update_layout()
        return redirect('/')
    except ValueError:
        # This should catch ValueErrors raise by either id_str_to_int or am.delete_activity
        return abort(404, f'No activity found with ID {id} (or there was some other error).')


if __name__ == '__main__':
    from sys import argv

    debug = '--debug' in argv
    server.run(host='0.0.0.0', debug=debug, port=8080)
