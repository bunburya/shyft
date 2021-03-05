from logging import ERROR
from typing import List, Dict, Any, Optional, Tuple, Callable

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from all_activities import AllActivitiesController
from dash.development.base_component import Component
from dash.dependencies import Input, Output

from shyft.activity import ActivityMetaData, Activity
from shyft.activity_manager import ActivityManager
from shyft.config import Config
from shyft.logger import get_logger
from shyft.message import MessageBus
from shyft.view.controller.activity import ActivityController
from shyft.view.controller.config import ConfigController
from shyft.view.controller.overview import OverviewController
from shyft.view.controller.upload import UploadController

logger = get_logger(__name__)


def id_str_to_int(id: str) -> int:
    """Convert a string activity id to an integer, performing some
    basic verification and raising a ValueError is the given id is
    not valid (ie, the string cannot be converted to a valid integer;
    the returned integer is not necessarily the id of an actual
    Activity).
    """
    try:
        activity_id = int(id)
    except (ValueError, TypeError):
        activity_id = None
    if activity_id is None:
        raise ValueError(f'Bad activity id: "{id}".')
    return activity_id

class DashController:
    """A main controller class for use with our Dash app. This will
    hold instances of the other, page-specific controller classes.
    """

    def __init__(self, dash_app: dash.Dash, config: Config, activity_manager: Optional[ActivityManager] = None):
        logger.debug('Initialising DashController.')
        self.dash_app = dash_app
        # Stop Dash complaining if not all components are present when callbacks are registered
        # https://dash.plotly.com/callback-gotchas
        dash_app.config.suppress_callback_exceptions = True
        if activity_manager is None:
            self.activity_manager = ActivityManager(config)
        else:
            self.activity_manager = activity_manager
        self.config = config
        self.config_fpath = config.ini_fpath
        self.msg_bus = MessageBus()

        self.overview_controller = OverviewController(self)
        self.activity_controller = ActivityController(self)
        self.upload_controller = UploadController(self)
        self.config_controller = ConfigController(self)
        self.all_activities_controller = AllActivitiesController(self)

        self.register_callbacks()
        # Initialise with empty layout; content will be added by callbacks.
        self.dash_app.layout = self.layout()

    def layout(self, content: Optional[List[Component]] = None) -> html.Div:
        logger.debug('Setting page layout.')
        return html.Div(
            id='layout',
            children=[
                # Because Dash only allows each component property (such as the "pathname" property of a dcc.Location)
                # to be associated with one Output, each part of the app needs to update a separate dcc.Location when
                # it wants to redirect the user, and the relevant callback needs to fire upon any of those components
                # being updated. And we need to create all relevant dcc.Location instances at the beginning (ie, here).
                dcc.Location(id='upload_location', refresh=False),
                #dcc.Location(id='all_')
                #html.Div('dummy', hidden=True),
                #html.Div('redirect', hidden=True)
                html.Div(id='page_content', children=content or [])
            ]
        )

    def _id_str_to_metadata(self, id: str) -> Optional[ActivityMetaData]:
        return self.activity_manager.get_metadata_by_id(id_str_to_int(id))

    def _id_str_to_activity(self, id: str) -> Optional[Activity]:
        return self.activity_manager.get_activity_by_id(id_str_to_int(id))

    def _resolve_pathname(self, path) -> List[Component]:
        """Resolve the URL pathname and return the appropriate page
        content.
        """
        logger.info(f'Resolving pathname "{path}" for page content.')
        tokens = path.split('/')[1:]

        if tokens[0] == 'activity':
            try:
                return self.activity_controller.page_content(self._id_str_to_activity(tokens[1]))
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
        elif tokens[0] == 'all':
            return self.all_activities_controller.page_content()

        return self.overview_controller.page_content()

    def register_callbacks(self):
        logger.debug('Registering app-level callbacks.')

        @self.dash_app.callback(
            Output('page_content', 'children'),
            #Input('url', 'pathname'),
            Input('upload_location', 'pathname')
        )
        def update_page(*args) -> List[Component]:
            """Display different page on url update."""
            ctx = dash.callback_context
            trig = ctx.triggered[0]
            prop_id = trig['prop_id']
            value = trig['value']
            logger.debug(f'update_page called from {prop_id} with value "{value}".')
            return self._resolve_pathname(value)

        # Unfortunately this seems to be the only way to dynamically set the title in Dash.
        # FIXME: Doesn't work...
        self.dash_app.clientside_callback(
            """
            function(pathname) {
                console.log('Callback called with %s', pathname);
                token = pathname.split('/')[1];
                if (token === 'activity') {
                    document.title = 'View activity - Shyft'
                } else if (token === 'config') {
                    document.title = 'Configure - Shyft'
                } else if (token === 'upload') {
                    document.title = 'Upload - Shyft'
                } else {
                    document.title == 'Overview - Shyft'
                }
            }
            """,
            Output('dummy', 'children'),
            Input('url', 'pathname')
        )

