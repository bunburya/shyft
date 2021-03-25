import dataclasses
import json
import os
from io import BytesIO
from logging import ERROR
from typing import List, Dict, Optional, Tuple, Callable
from urllib.parse import urlparse, parse_qs
from zipfile import ZipFile

import flask
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash import callback_context
from dash.development.base_component import Component
from dash.dependencies import Input, Output, ALL, MATCH, State
from dash.exceptions import PreventUpdate
from shyft.app.controllers.calendar import CalendarController
from shyft.app.controllers.landing import LandingPageController

from werkzeug.exceptions import abort
import dateutil.parser as dp

from shyft.activity import ActivityMetaData, Activity
from shyft.activity_manager import ActivityManager
from shyft.config import Config
from shyft.logger import get_logger
from shyft.message import MessageBus
from shyft.json_utils import ShyftJSONEncoder
from shyft.app.controllers.activity import ActivityController
from shyft.app.controllers.config import ConfigController
from shyft.app.controllers.overview import OverviewController
from shyft.app.controllers.upload import UploadController
from shyft.app.controllers.view_activities import ViewActivitiesController
from shyft.app.controllers.markdown import MarkdownController
from shyft.app.utils import id_str_to_ints

logger = get_logger(__name__)

MIMETYPES = {
    '.gpx': 'application/gpx+xml',
    '.fit': 'application/vnd.ant.fit',
    '.tcx': 'application/vnd.garmin.tcx+xml'
}
MIMETYPE_FALLBACK = 'application/octet-stream'


class MainController:
    """A main controllers class for use with our Dash app. This will
    hold instances of the other, page-specific controllers classes.
    """

    def __init__(self, dash_app: dash.Dash, config: Config, msg_bus: Optional[MessageBus] = None,
                 activity_manager: Optional[ActivityManager] = None):
        logger.debug('Initialising MainController.')
        self.dash_app = dash_app
        # Stop Dash complaining if not all components are present when callbacks are registered
        # https://dash.plotly.com/callback-gotchas
        dash_app.config.suppress_callback_exceptions = True
        if msg_bus is None:
            logger.debug('No value provided for msg_bus: Creating new MessageBus.')
            self.msg_bus = MessageBus()
            logger.debug(f'msg_bus: {self.msg_bus}')
        else:
            self.msg_bus = msg_bus
        if activity_manager is None:
            logger.debug('No value provided for activity_manager: Creating new ActivityManager.')
            self.activity_manager = ActivityManager(config)
        else:
            self.activity_manager = activity_manager
        self.config = config
        self.config_fpath = config.ini_fpath

        self.landing_controller = LandingPageController(self)
        self.overview_controller = OverviewController(self)
        self.activity_controller = ActivityController(self)
        self.upload_controller = UploadController(self)
        self.config_controller = ConfigController(self)
        self.view_activities_controller = ViewActivitiesController(self)
        self.markdown_controller = MarkdownController(self)
        self.calendar_controller = CalendarController(self)
        # self.locations = self.init_locations()
        self.register_callbacks()

        # Initialise with empty layout; content will be added by callbacks.
        self.dash_app.layout = self.layout()

    def parse_url_query(self, query: str) -> Dict[str, str]:
        """Parse a string representing the query portion of a URL.

        Returns a dict representing the parameters that can be used by
        other methods such as get_params_to_metadata.

        Assumes that the query is validly formed and each parameter is
        specified at most once.
        """
        parsed = parse_qs(query)
        params = {}
        for k in parsed:
            if len(parsed[k]) > 1:
                raise ValueError(
                    f'Parameter "{k}" passed more than once. Each parameter should be passed at most once.')
            params[k] = parsed[k][0]
        return params

    def url_params_to_metadata(self, params: Dict[str, str]) -> List[ActivityMetaData]:
        """Takes a dict representing parameters of a query and returns
        a list of ActivityMetaData objects that fit the given search
        criteria.
        """
        if (from_date := params.get('from_date')) is not None:
            from_date = dp.parse(from_date).date()
        if (to_date := params.get('to_date')) is not None:
            to_date = dp.parse(to_date).date()
        if (prototype := params.get('prototype')) is not None:
            prototype = int(prototype)
        activity_type = params.get('type')
        if (ids := params.get('id')) is not None:
            ids = id_str_to_ints(ids)

        return self.activity_manager.search_metadata(from_date=from_date, to_date=to_date, prototype=prototype,
                                                     activity_type=activity_type, ids=ids)

    def url_params_to_metadata_json(self, params: Dict[str, str], exclude_filepaths: bool = True,
                                    exclude_config: bool = True) -> str:
        """Takes a dict representing parameters of a query and returns
        a JSON string representing a list of ActivityMetaData objects
        that fit the given search criteria.
        """
        # TODO: Consider if we need this. We don't use it currently - might we need it in the future?
        metadata = self.url_params_to_metadata(params)
        data = []
        for m in metadata:
            d = dataclasses.asdict(m)
            if exclude_filepaths:
                for k in ('gpx_file', 'tcx_file', 'source_file', 'thumbnail_file'):
                    d.pop(k)
            if exclude_config:
                d.pop('config')
            data.append(d)
        return json.dumps(data, cls=ShyftJSONEncoder)

    def url_params_to_calendar_data(self, params: Dict[str, str]) -> str:
        """Takes a dict representing parameters of a query and returns
        a JSON string, usable by FullCalendar, representing the
        activities that fit the given search criteria.
        """
        metadata = self.url_params_to_metadata(params)
        data = [{
            'title': self.activity_controller.dc_factory.activity_name(m),
            'start': m.date_time,
            'end': m.date_time + m.duration,
            'url': f'/activity/{m.activity_id}'
        } for m in metadata]
        return json.dumps(data, cls=ShyftJSONEncoder)

    def layout(self, content: Optional[List[Component]] = None) -> html.Div:
        logger.debug('Setting page layout.')
        return html.Div(
            id='layout',
            children=[
                # *self.locations,
                dcc.Location('url', refresh=True),
                dbc.Container(content or [], id='page_content')
            ]
        )

    def render_markdown(self, fpath: str) -> List[Component]:
        pass

    def _id_str_to_metadata(self, ids: str) -> List[Optional[ActivityMetaData]]:
        return [self.activity_manager.get_metadata_by_id(i) for i in id_str_to_ints(ids)]

    def _id_str_to_activities(self, ids: str) -> List[Optional[Activity]]:
        return [self.activity_manager.get_activity_by_id(i) for i in id_str_to_ints(ids)]

    def _resolve_pathname(self, href: str) -> List[Component]:
        """Resolve the URL pathname and return the appropriate page
        content.
        """
        logger.info(f'Resolving URL "{href}" for page content.')

        if href is not None:
            parsed = urlparse(href)
            path = parsed.path
            params = self.parse_url_query(parsed.query)
            tokens = path.split('/')[1:]
            if tokens[0] == 'activity':
                try:
                    return self.activity_controller.page_content(self._id_str_to_activities(tokens[1])[0])
                except IndexError:
                    logger.error('Could not load activity view: No activity ID provided.')
                    self.msg_bus.add_message('Could not display activity. Check the logs for more details.',
                                             severity=ERROR)
                except ValueError:
                    logger.error(f'Could not load activity view: Bad activity ID "{tokens[1]}".')
                    self.msg_bus.add_message('Could not display activity. Check the logs for more details.',
                                             severity=ERROR)
            elif tokens[0] == 'upload':
                return self.upload_controller.page_content()
            elif tokens[0] == 'config':
                return self.config_controller.page_content()
            elif tokens[0] == 'activities':
                return self.view_activities_controller.page_content(params)
            elif tokens[0] == 'overview':
                return self.overview_controller.page_content()
            elif tokens[0] == 'calendar':
                return self.calendar_controller.page_content()
            elif tokens[0] == 'docs':
                return self.markdown_controller.page_content(tokens[1])
            elif tokens[0] in {'gpx_files', 'tcx_files', 'source_files'}:
                logger.debug(f'New pathname contains {tokens[0]}; not updating page content.')
                raise PreventUpdate
            elif tokens[0]:
                logger.warning(f'Received possibly unexpected pathname "{tokens[0]}".')

        return self.landing_controller.page_content()

    def register_callbacks(self):
        logger.debug('Registering app-level callbacks.')

        @self.dash_app.callback(
            Output('page_content', 'children'),
            Input('url', 'href'),
        )
        def update_page(href: str) -> List[Component]:
            """Display different page on url update."""
            logger.debug(f'URL change detected: new URL is "{href}".')
            return self._resolve_pathname(href)

        @self.dash_app.callback(
            Output('url', 'pathname'),
            Input({'type': 'redirect', 'context': ALL, 'index': ALL}, 'children')
        )
        def update_url(pathnames: List[str]) -> str:
            ctx = dash.callback_context
            trig = ctx.triggered[0]
            component, prop = trig['prop_id'].split('.')
            value = trig['value']
            logger.debug(f'update_url called from property "{prop}" of component "{component}" with value "{value}".')
            logger.debug(f'Updating URL pathname to "{value}".')
            return value

        # The below callbacks are used for manipulating activity tables. They are registered here in MainController
        # because it is contemplated that activity tables can be manipulated in multiple contexts.
        # TODO: We could probably move this to view_activities.py; I don't think we'll need it elsewhere.
        # TODO: Currently, trying to perform actions on large numbers of activities at once results in very long URLs.
        # With enough activities, this could cause issues in some browsers:
        # see https://stackoverflow.com/questions/417142/what-is-the-maximum-length-of-a-url-in-different-browsers
        # One solution could be to save the IDs locally and pass a special value, like "check_file" to the relevant
        # endpoint (eg, /tcx_files/check_file), which would cause the code at the endpoint to check that file for the
        # activity IDs to act upon.

        @self.dash_app.callback(
            Output({'type': 'delete_hidden', 'index': MATCH}, 'value'),
            Output({'type': 'delete_button', 'index': MATCH}, 'disabled'),
            Output({'type': 'delete_form', 'index': MATCH}, 'action'),
            Output({'type': 'download_link', 'index': MATCH}, 'href'),
            Output({'type': 'download_button', 'index': MATCH}, 'disabled'),
            Input({'type': 'activity_table_dropdown', 'index': MATCH}, 'value'),
            Input({'type': 'activity_table', 'index': MATCH}, 'selected_rows'),
            State({'type': 'activity_table', 'index': MATCH}, 'data'),
            State('url', 'pathname'),
        )
        def set_action_links(download: str, selected_rows: List[int], data: List,
                             pathname: str) -> Tuple[str, bool, str, str, bool]:
            """Triggered every time an activity is selected or
            unselected, or the download dropdown value is changed.
            Sets the link and disabled status of the "Download" button,
            and the disabled status, POST data and form action
            associated with the "Delete" button.
            """
            logger.debug(f'Value "{download}" selected from download dropdown.')
            # logger.debug(f'Selected rows: {selected_rows}')
            del_path = f'/delete?redirect={pathname}'
            if not selected_rows:
                return '', True, del_path, '', True
            ids = [str(data[i]['id']) for i in selected_rows]
            if not ids:
                raise PreventUpdate
            ids_str = ','.join(ids)
            if download == 'select':
                download_href = ''
                download_disabled = True
            else:
                download_href = f'/{download}?id={ids_str}'
                download_disabled = False
            logger.debug(f'Setting download link to "{download_href}".')
            return ids_str, False, del_path, download_href, download_disabled

        @self.dash_app.callback(
            Output({'type': 'activity_table', 'index': MATCH}, 'selected_rows'),
            Input({'type': 'select_all_button', 'index': MATCH}, 'n_clicks'),
            Input({'type': 'unselect_all_button', 'index': MATCH}, 'n_clicks'),
        )
        def un_select(*args) -> List[int]:
            trig = callback_context.triggered[0]
            component_str, prop = trig['prop_id'].split('.')
            if not component_str:
                raise PreventUpdate
            component = json.loads(component_str)
            logger.debug(f'un_select called with trigger "{trig["prop_id"]}".')
            if component['type'] == 'select_all_button':
                logger.debug('Select button clicked.')
                return list(range(len(self.activity_manager)))
            elif component['type'] == 'unselect_all_button':
                logger.debug('Unselect button clicked.')
                return []
            else:
                logger.error(f'Unexpected component: "{component}".')
                raise PreventUpdate

        # Unfortunately this seems to be the only way to dynamically set the title in Dash.
        # FIXME: Doesn't work...
        # self.app.clientside_callback(
        #     """
        #     function(pathname) {
        #         console.log('Callback called with %s', pathname);
        #         token = pathname.split('/')[1];
        #         if (token === 'activity') {
        #             document.title = 'View activity - Shyft'
        #         } else if (token === 'config') {
        #             document.title = 'Configure - Shyft'
        #         } else if (token === 'upload') {
        #             document.title = 'Upload - Shyft'
        #         } else {
        #             document.title == 'Overview - Shyft'
        #         }
        #     }
        #     """,
        #     Output('dummy', 'children'),
        #     Input('url', 'pathname')
        # )

    def serve_file(self, fpath: Optional[str], not_found_msg: str = 'File not found.'):
        """A generic function to serve a file."""

        if fpath:
            _, ext = os.path.splitext(fpath)
            mimetype = MIMETYPES.get(ext, MIMETYPE_FALLBACK)
            return flask.send_file(fpath, mimetype=mimetype, as_attachment=True,
                                   attachment_filename=os.path.basename(fpath))
        else:
            return abort(404, not_found_msg.format(id=id))

    def serve_files(self, fpaths: List[str], attachment_filename: str,
                    not_found_msg: str = 'One or more files could not be found.'):
        """A generic function to serve multiple files as a zip archive."""
        zip_bytes = BytesIO()
        try:
            with ZipFile(zip_bytes, mode='w') as z:
                for f in fpaths:
                    logger.debug(f'Adding {f} to zip archive.')
                    z.write(f, os.path.basename(f))
        except FileNotFoundError:
            return abort(404, not_found_msg)
        zip_bytes.seek(0)
        return flask.send_file(zip_bytes, mimetype='application/zip', as_attachment=True,
                               attachment_filename=attachment_filename)

    def serve_files_from_get_params(self, params: Dict[str, str], fpath_getter: Callable[[ActivityMetaData], str],
                                    attachment_filename: str,
                                    not_found_msg: str = 'One or more files could not be found.'):
        """A generic function to serve a file, or multiple files as a
        zip archive, based on the parameters of a GET query (as a dict).

        `attachment_filename` should be the name of the zip archive to
        be served if multiple IDs are provided.

        `not_found_msg` is the message that will be displayed to the
        user if one or more relevant files is not found.
        """
        try:
            metadata = self.url_params_to_metadata(params)
        except ValueError:
            return abort(404, 'Bad query. Check logs for more details.')
        fpaths = [fpath_getter(md) for md in metadata]
        if len(fpaths) == 1:
            return self.serve_file(fpaths[0], not_found_msg)
        elif len(fpaths) > 1:
            return self.serve_files(fpaths, attachment_filename, not_found_msg)
        else:
            return abort(404, 'No activities found for query.')
