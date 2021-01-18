import logging
import os
import shutil
from typing import Callable

from flask import Flask, url_for, render_template, redirect, send_file, flash, request
import dash_bootstrap_components as dbc
from pyft.config import Config
from pyft.multi_activity import ActivityManager
from pyft.view import view_activity
from pyft.view.overview import Overview

from pyft.serialize.parse import PARSERS


### FOR TESTING ONLY

from test.test_common import *

from pyft.view.edit_config import ConfigForm
from pyft.view.view_activity import ActivityView
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

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css', dbc.themes.BOOTSTRAP]

server = Flask(__name__, template_folder='templates')
server.secret_key = 'TEST_KEY'

overview = Overview(am, CONFIG, __name__, server=server, external_stylesheets=external_stylesheets)

activity_view = ActivityView(am, CONFIG, __name__, server=server, external_stylesheets=external_stylesheets,
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

@server.route('/thumbnails/<id>.png')
def get_thumbnail(id: str):
    # TODO:  Probably better if we just statically serve the thumbnails.
    try:
        activity_id = id_str_to_int(id)
    except ValueError:
        return f'Invalid activity ID specified: "{id}".'
    # print(f'Activity with ID {activity_id}: {am.get_metadata_by_id(activity_id)}')
    metadata = am.get_metadata_by_id(activity_id)
    return send_file(metadata.thumbnail_file, mimetype='image/png')


@server.route('/gpx_files/<id>')
def get_gpx_file(id: str):
    try:
        activity_id = id_str_to_int(id)
    except ValueError:
        return f'Invalid activity ID specified: "{id}".'
    metadata = am.get_metadata_by_id(activity_id)
    data_file = metadata.data_file
    if data_file:
        return send_file(data_file, mimetype='application/gpx+xml', as_attachment=True,
                         attachment_filename=os.path.basename(data_file))
    else:
        return (f'No data file found for activity ID "{id}".')

MIMETYPES = {
    '.gpx': 'application/gpx+xml',
    '.fit': 'application/vnd.ant.fit'
}
MIMETYPE_FALLBACK = 'application/octet-stream'

@server.route('/source_files/<id>')
def get_source_file(id: str):
    try:
        activity_id = id_str_to_int(id)
    except ValueError:
        return f'Invalid activity ID specified: "{id}".'
    metadata = am.get_metadata_by_id(activity_id)
    source_file = metadata.source_file
    if source_file:
        _, ext = os.path.splitext(source_file)
        mimetype = MIMETYPES.get(ext, MIMETYPE_FALLBACK)
        return send_file(source_file, mimetype=mimetype, as_attachment=True,
                         attachment_filename=os.path.basename(source_file))
    else:
        return (f'No source file found for activity ID "{id}".')

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
        flash('Configuration saved.')
    return render_template('config.html', form=form)

@server.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and is_allowed_file(file.filename):
            filename = secure_filename(file.filename)
            fpath = os.path.join(TMP_UPLOAD_FOLDER, filename)
            file.save(fpath)
            id = am.add_activity_from_file(fpath)
            overview.update_layout()
            return redirect(f'/activity/{id}')
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''

@server.route('/delete/<id>')
def delete(id: str):
    try:
        activity_id = id_str_to_int(id)
        am.delete_activity(activity_id)
        overview.update_layout()
        # FIXME: We can't flash message using Dash. Maybe implement some kind of MessageBus
        # that the Overview and AcitivityView classes can use to display messages.
        flash(f'Deleted activity with ID {activity_id}.')
        return redirect('/')
    except ValueError:
        # This should catch ValueErrors raise by either id_str_to_int or am.delete_activity
        return f'Invalid activity ID specified: "{id}".'



if __name__ == '__main__':
    from sys import argv

    debug = '--debug' in argv
    server.run(host='0.0.0.0', debug=debug, port=8080)
