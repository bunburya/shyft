import logging
import os
import shutil

from flask import Flask, url_for, render_template, redirect, send_file, flash
import dash_bootstrap_components as dbc
from pyft.config import Config
from pyft.multi_activity import ActivityManager
from pyft.view import view_activity
from pyft.view.overview import Overview

### FOR TESTING ONLY

from test.test_vars import *

from pyft.view.edit_config import ConfigForm
from pyft.view.view_activity import ActivityView

TEST_DATA_DIR = 'test/test_data'


TEST_RUN_DATA_DIR = run_data_dir('view', replace=True)
TEST_CONFIG_FILE = config_file(TEST_RUN_DATA_DIR)

TEST_CONFIG = Config(
    TEST_CONFIG_FILE,
    TEST_ACTIVITY_GRAPHS_FILE,
    TEST_OVERVIEW_GRAPHS_FILE,
    data_dir=TEST_RUN_DATA_DIR
)

am = ActivityManager(TEST_CONFIG)
for fpath in TEST_GPX_FILES:
    am.add_activity_from_file(fpath)

logging.getLogger().setLevel(logging.INFO)

### /TESTING

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css', dbc.themes.BOOTSTRAP]

server = Flask(__name__, template_folder='templates')
server.secret_key = 'TEST_KEY'

overview = Overview(am, TEST_CONFIG, __name__, server=server, external_stylesheets=external_stylesheets)

activity_view = ActivityView(am, TEST_CONFIG, __name__, server=server, external_stylesheets=external_stylesheets,
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
    return send_file(metadata.thumbnail_file, mimetype='image/png')


@server.route('/gpx_files/<id>.gpx')
def get_gpx_file(id: str):
    try:
        activity_id = id_to_int(id)
    except ValueError:
        return f'Invalid activity ID specified: "{id}".'
    metadata = am.get_metadata_by_id(activity_id)
    return send_file(metadata.data_file, mimetype='application/gpx+xml')


@server.route('/config', methods=['GET', 'POST'])
def config():
    # https://hackersandslackers.com/flask-wtforms-forms/
    raw_config = TEST_CONFIG.raw()
    form = ConfigForm(obj=raw_config)
    if form.validate_on_submit():
        form.populate_obj(raw_config)
        raw_config.to_file(TEST_CONFIG_FILE)
        # Have to load again to get the interpolation working right
        TEST_CONFIG.load(TEST_CONFIG_FILE)
        overview.update_layout()
        # return redirect(url_for('save_config'))
        flash('Configuration saved.')
    return render_template('config.html', form=form)


if __name__ == '__main__':
    from sys import argv

    debug = '--debug' in argv
    server.run(host='0.0.0.0', debug=debug, port=8080)
