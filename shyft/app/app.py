import logging
import os
from typing import Tuple
from urllib.parse import urlparse

from shyft.app.controllers.main import MainController
from dash import Dash
import dash_bootstrap_components as dbc
from flask import Flask, redirect, send_file, request, Response, render_template, g, send_from_directory
from werkzeug.exceptions import abort

import shyft.message as msg
from shyft.config import Config
from shyft.metadata import APP_NAME
from shyft.logger import get_logger
from shyft.app.utils import id_str_to_ints

_logger = get_logger(__name__)

STYLESHEETS = [dbc.themes.SANDSTONE]

CONTENT_DIR = os.path.join('app', 'content')


def get_apps(config: Config) -> Tuple[Flask, Dash]:
    """Initialise and return the Flask and Dash apps."""

    flask_app = Flask('shyft', template_folder=os.path.join(CONTENT_DIR, 'templates'),
                      static_folder=os.path.join(CONTENT_DIR, 'static'))
    _logger.debug(f'static: {flask_app.static_folder}')

    # Prevent caching of files (such as thumbnails)
    # NOTE: We may actually want to cache when not debugging, as there shouldn't be different activities loaded with the
    # same ID in normal usage.
    flask_app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    dash_app = Dash(__name__, server=flask_app, external_stylesheets=STYLESHEETS, title='Shyft')

    controller = MainController(dash_app, config)

    @flask_app.route('/thumbnails/<id>.png')
    def get_thumbnail(id: str):
        try:
            activity_id = id_str_to_ints(id)[0]
        except ValueError:
            return abort(404, description=f'Invalid activity ID specified: "{id}".')
        # print(f'Activity with ID {activity_id}: {am.get_metadata_by_id(activity_id)}')
        metadata = controller.activity_manager.get_metadata_by_id(activity_id)
        return send_file(metadata.thumbnail_file, mimetype='image/png')

    @flask_app.route('/gpx_files')
    def get_gpx_file():
        _logger.debug(f'gpx_files endpoint reached with GET params: "{request.args}".')
        return controller.serve_files_from_get_params(request.args, lambda md: md.gpx_file,
                                                      f'{APP_NAME}_gpx_files.zip',
                                                      'No GPX files found for selected activities.')

    @flask_app.route('/tcx_files')
    def get_tcx_file():
        _logger.debug(f'tcx_files endpoint reached with GET params: "{request.args}".')
        return controller.serve_files_from_get_params(request.args, lambda md: md.tcx_file,
                                                      f'{APP_NAME}_tcx_files.zip',
                                                      'No TCX files found for selected activities.')

    @flask_app.route('/source_files')
    def get_source_file():
        _logger.debug(f'source_files endpoint reached with GET params: "{request.args}".')
        return controller.serve_files_from_get_params(request.args, lambda md: md.source_file,
                                                      f'{APP_NAME}_source_files.zip',
                                                      'No source files found for selected activities.')

    @flask_app.route('/delete', methods=['POST', 'GET'])
    def delete():
        _logger.debug(f'/delete endpoint reached with args: {request.form}')
        if not request.form:
            _logger.warning('delete function received empty request.form. Not deleting anything.')
        else:
            try:
                activity_ids = [md.activity_id for md in
                                controller.url_params_to_metadata(request.form)]
            except ValueError:
                return abort(404, f'Bad query. Check logs for details.')
            for i in activity_ids:
                try:
                    controller.activity_manager.delete_activity(i)
                except ValueError:
                    controller.msg_bus.add_message(
                        f'Could not delete activity with ID {i}. It may not exist.',
                        logging.ERROR
                    )
            if len(activity_ids) == 1:
                controller.msg_bus.add_message(f'Deleted activity with ID {activity_ids[0]}.')
            else:
                controller.msg_bus.add_message(f'Deleted {len(activity_ids)} activities.')
        if send_to := request.args.get('redirect'):
            return redirect(send_to)
        else:
            return redirect('/')

    @flask_app.route('/_calendar')
    def calendar():
        return render_template('calendar.html', query=urlparse(request.url).query, stylesheets=STYLESHEETS)

    @flask_app.route('/json/calendar_data')
    def metadata_json():
        return Response(controller.url_params_to_calendar_data(request.args),
                        mimetype='application/vnd.api+json')


    return flask_app, dash_app
