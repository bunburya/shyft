import logging
from typing import Callable, Any, Dict

from flask import Flask, url_for, render_template, redirect, send_file, flash, request, g
import dash_bootstrap_components as dbc
import shyft.message as msg
from shyft.metadata import APP_NAME, VERSION, URL
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

DATA_DIR = CONFIG.data_dir
TMP_UPLOAD_FOLDER = os.path.join(DATA_DIR, 'tmp_uploads')
if not os.path.exists(TMP_UPLOAD_FOLDER):
    os.makedirs(TMP_UPLOAD_FOLDER)

SUPPORTED_EXTENSIONS = PARSERS

stylesheets_nondash = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
stylesheets_dash = stylesheets_nondash + [dbc.themes.BOOTSTRAP]

server = Flask(__name__, template_folder='templates')
server.secret_key = 'TEST_KEY'

context = {}

msg_bus = msg.MessageBus()

overview = Overview(am, msg_bus, CONFIG, __name__, server=server, external_stylesheets=stylesheets_dash)

activity_view = ActivityView(am, msg_bus, CONFIG, __name__, server=server, external_stylesheets=stylesheets_dash,
                             routes_pathname_prefix='/activity/')


def id_str_to_int(id: str) -> int:
    """Convert a string activity id to an integer, performing some
    basic verification and raising a ValueError is the given id is
    not valid.
    """
    try:
        activity_id = int(id)
    except (ValueError, TypeError):
        activity_id = None
    if activity_id is None:
        raise ValueError(f'Bad activity id: "{id}".')
    return activity_id


def is_allowed_file(fname: str) -> bool:
    return os.path.splitext(fname)[1].lower() in SUPPORTED_EXTENSIONS


MIMETYPES = {
    '.gpx': 'application/gpx+xml',
    '.fit': 'application/vnd.ant.fit',
    '.tcx': 'application/vnd.garmin.tcx+xml'
}
MIMETYPE_FALLBACK = 'application/octet-stream'


def serve_file(id: str, fpath_getter: Callable[[ActivityMetaData], str], not_found_msg: str = 'File not found.'):
    """A generic function to serve a file.

    `fpath_getter` should be a function that takes an ActivityMetaData
    instance and returns the path to the file to be served.

    `not_found_msg` is the message that will be displayed to the user
    if the relevant file is not found. It can reference the provided
    ID using Python's string formatting (ie, '{id}').
    """
    try:
        activity_id = id_str_to_int(id)
    except ValueError:
        return abort(404, f'Invalid activity ID specified: "{id}".')
    metadata = am.get_metadata_by_id(activity_id)
    if metadata is not None:
        fpath = fpath_getter(metadata)
    else:
        fpath = None
    if fpath:
        _, ext = os.path.splitext(fpath)
        mimetype = MIMETYPES.get(ext, MIMETYPE_FALLBACK)
        return send_file(fpath, mimetype=mimetype, as_attachment=True,
                         attachment_filename=os.path.basename(fpath))
    else:
        abort(404, not_found_msg.format(id=id))


def get_title(page_name: str) -> str:
    """Return the title to be displayed for a page."""
    return f'{page_name} - {APP_NAME}'


def get_footer_rendering_data() -> Dict[str, Any]:
    return {
        'app_name': APP_NAME,
        'app_version': VERSION,
        'app_url': URL
    }


def get_flask_rendering_data(page_name: str) -> Dict[str, Any]:
    """Returns a dict containing the data we need to provide as
    arguments to the jinja render function (ignoring any
    page-specific data).
    """
    return {
        'title': get_title(page_name),
        'stylesheets': stylesheets_nondash,
        'messages': msg_bus.get_messages(),
        **get_footer_rendering_data()
    }


@server.route('/thumbnails/<id>.png')
def get_thumbnail(id: str):
    # TODO:  Probably better if we just statically serve the thumbnails.
    try:
        activity_id = id_str_to_int(id)
    except ValueError:
        return abort(404, description=f'Invalid activity ID specified: "{id}".')
    # print(f'Activity with ID {activity_id}: {am.get_metadata_by_id(activity_id)}')
    metadata = am.get_metadata_by_id(activity_id)
    return send_file(metadata.thumbnail_file, mimetype='image/png')


@server.route('/gpx_files/<id>')
def get_gpx_file(id: str):
    return serve_file(id, lambda md: md.gpx_file, 'No GPX file found for activity ID {id}.')


@server.route('/tcx_files/<id>')
def get_tcx_file(id: str):
    return serve_file(id, lambda md: md.tcx_file, 'No TCX file found for activity ID {id}.')


@server.route('/source_files/<id>')
def get_source_file(id: str):
    return serve_file(id, lambda md: md.source_file, 'No source file found for activity ID {id}.')


@server.route('/config', methods=['GET', 'POST'])
def config():
    # https://hackersandslackers.com/flask-wtforms-forms/
    raw_config = CONFIG.raw()
    form = ConfigForm(obj=raw_config)
    if form.validate_on_submit():
        form.populate_obj(raw_config)
        raw_config.to_file(TEST_CONFIG_FILE)
        # Have to load again to get the interpolation working right
        CONFIG.load(TEST_CONFIG_FILE)
        overview.update_layout()
        # return redirect(url_for('save_config'))
        msg_bus.add_message('Configuration saved.')
    return render_template('config.html.jinja', form=form, **get_flask_rendering_data('Configure'))


@server.route('/upload', methods=['GET', 'POST'])
def upload_file():
    # if request.method == 'POST':  # POST means something is being uploaded (ie, user has clicked Upload)
    #     # check if the post request has the file part
    #     if 'file' not in request.files:
    #         flash('No file part')
    #         return redirect(request.url)
    #     file = request.files['file']
    #     # if user does not select file, browser also submits an empty part without filename
    #     if file.filename == '':
    #         flash('No selected file')
    #         return redirect(request.url)
    #     if file and is_allowed_file(file.filename):
    #         filename = secure_filename(file.filename)
    #         fpath = os.path.join(TMP_UPLOAD_FOLDER, filename)
    #         file.save(fpath)
    #         id = am.add_activity_from_file(fpath)
    #         overview.update_layout()
    #         return redirect(f'/activity/{id}')

    form = UploadForm()
    if form.validate_on_submit():
        f = form.upload_file.data
        filename = secure_filename(f.filename)
        fpath = os.path.join(TMP_UPLOAD_FOLDER, filename)
        f.save(fpath)
        id = am.add_activity_from_file(fpath)
        overview.update_layout()
        return redirect(f'/activity/{id}')
    return render_template('upload.html.jinja', form=form, **get_flask_rendering_data('Upload'))


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
