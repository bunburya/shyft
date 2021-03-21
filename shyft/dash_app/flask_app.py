import logging
import os
from urllib.parse import urlparse

from dash import dash
import dash_bootstrap_components as dbc
from flask import Flask, redirect, send_file, request, Response, render_template, g
from werkzeug.exceptions import abort

import shyft.message as msg
from shyft.metadata import APP_NAME
from shyft.logger import get_logger
from shyft.dash_app.view.controller.main import MainController, id_str_to_ints

logger = get_logger(__name__)


stylesheets_nondash = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
# stylesheets_dash = stylesheets_nondash + [dbc.themes.BOOTSTRAP]
stylesheets_dash = stylesheets_nondash + [dbc.themes.SANDSTONE]

server = Flask('shyft', template_folder='shyft/content/templates')

# Prevent caching of files (such as thumbnails)
# NOTE: We may actually want to cache when not debugging, as there shouldn't be different activities loaded with the
# same ID in normal usage.
server.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

msg_bus = msg.MessageBus()

dash_app = dash.Dash(__name__, server=server, external_stylesheets=stylesheets_dash, title='Shyft')
#logger.info('Initialised Dash app.')

@server.route('/thumbnails/<id>.png')
def get_thumbnail(id: str):
    try:
        activity_id = id_str_to_ints(id)[0]
    except ValueError:
        return abort(404, description=f'Invalid activity ID specified: "{id}".')
    # print(f'Activity with ID {activity_id}: {am.get_metadata_by_id(activity_id)}')
    metadata = g.main_controller.activity_manager.get_metadata_by_id(activity_id)
    return send_file(metadata.thumbnail_file, mimetype='image/png')


@server.route('/gpx_files')
def get_gpx_file():
    logger.debug(f'gpx_files endpoint reached with GET params: "{request.args}".')
    return g.main_controller.serve_files_from_get_params(request.args, lambda md: md.gpx_file,
                                                       f'{APP_NAME}_gpx_files.zip',
                                                       'No GPX files found for selected activities.')

@server.route('/tcx_files')
def get_tcx_file():
    logger.debug(f'tcx_files endpoint reached with GET params: "{request.args}".')
    return g.main_controller.serve_files_from_get_params(request.args, lambda md: md.tcx_file,
                                                       f'{APP_NAME}_tcx_files.zip',
                                                       'No TCX files found for selected activities.')


@server.route('/source_files')
def get_source_file():
    logger.debug(f'source_files endpoint reached with GET params: "{id}".')
    return g.main_controller.serve_files_from_get_params(request.args, lambda md: md.source_file,
                                                       f'{APP_NAME}_source_files.zip',
                                                       'No source files found for selected activities.')


@server.route('/delete', methods=['POST', 'GET'])
def delete():
    logger.debug(f'/delete endpoint reached with args: {request.form}')
    if not request.form:
        logger.warning('delete function received empty request.form. Not deleting anything.')
    else:
        try:
            activity_ids = [md.activity_id for md in g.main_controller.get_params_to_metadata(request.form)]
        except ValueError:
            return abort(404, f'Bad query. Check logs for details.')
        for i in activity_ids:
            try:
                g.main_controller.activity_manager.delete_activity(i)
            except ValueError:
                msg_bus.add_message(f'Could not delete activity with ID {i}. It may not exist.', logging.ERROR)
        if len(activity_ids) == 1:
            msg_bus.add_message(f'Deleted activity with ID {activity_ids[0]}.')
        else:
            msg_bus.add_message(f'Deleted {len(activity_ids)} activities.')
    if (send_to := request.args.get('redirect')):
        return redirect(send_to)
    else:
        return redirect('/')


@server.route('/calendar')
def calendar():
    return render_template('calendar.html', query=urlparse(request.url).query)


@server.route('/json/metadata')
def metadata_json():
    return Response(g.main_controller.get_params_to_metadata_json(request.args), mimetype='application/vnd.api+json')


if __name__ == '__main__':
    dash_app.run_server(debug=True, port=8080, use_reloader=False)
