from logging import ERROR
from typing import List, Dict, Any, Optional, Tuple, Callable

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.development.base_component import Component
from dash.dependencies import Input, Output

from shyft.activity import ActivityMetaData, Activity
from shyft.activity_manager import ActivityManager
from shyft.config import Config
from shyft.logger import get_logger
from shyft.message import MessageBus
from shyft.metadata import APP_NAME, VERSION, URL
from shyft.view.controller.activity import ActivityController
from shyft.view.controller.overview import OverviewController

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

    def __init__(self, dash_app: dash.Dash, activity_manager: ActivityManager, config: Config, msg_bus: MessageBus):
        logger.debug('Initialising DashController.')
        self.dash_app = dash_app
        # Stop Dash complaining if not all components are present when callbacks are registered
        # https://dash.plotly.com/callback-gotchas
        dash_app.config.suppress_callback_exceptions = True
        self.activity_manager = activity_manager
        self.config = config
        self.msg_bus = msg_bus
        self.overview_controller = OverviewController(activity_manager, msg_bus, config)
        self.activity_controller = ActivityController(activity_manager, msg_bus, config, dash_app)
        self._register_callbacks()
        # Initialise with empty layout; content will be added by callbacks.
        self.dash_app.layout = self.layout()

    def layout(self, content: Optional[List[Component]] = None) -> html.Div:
        logger.debug('Setting page layout.')
        return html.Div(
            id='layout',
            children=[
                dcc.Location(id='url', refresh=False),
                html.Div(id='page_content', children=content or [])
            ]
        )

    def _id_str_to_metadata(self, id: str) -> Optional[ActivityMetaData]:
        return self.activity_manager.get_metadata_by_id(id_str_to_int(id))

    def _id_str_to_activity(self, id: str) -> Optional[Activity]:
        return self.activity_manager.get_activity_by_id(id_str_to_int(id))

    def _resolve_pathname(self, path) -> List[Component]:
        """Resolve the URL pathname and return a tuple containing the
        appropriate page content and a function to register callbacks
        (which should be called after setting the page layout to the
        returned page content).
        """
        logger.info(f'Resolving pathname "{path}".')
        tokens = path.split('/')[1:]

        if tokens[0] == 'activity':
            try:
                self._register_func = self.activity_controller._register_callbacks
                return self.activity_controller.page_content(self._id_str_to_activity(tokens[1]))
            except IndexError:
                logger.error('Could not load activity view: No activity ID provided.')
                self.msg_bus.add_message('Could not display activity. Check the logs for more details.',
                                         severity=ERROR)
            except ValueError:
                logger.error(f'Could not load activity view: Bad activity ID "{tokens[1]}".')
                self.msg_bus.add_message('Could not display activity. Check the logs for more details.',
                                         severity=ERROR)

        return self.overview_controller.page_content()

    def _register_callbacks(self):

        logger.debug('Registering app-level callbacks.')

        @self.dash_app.callback(
            Output('page_content', 'children'),
            Input('url', 'pathname')
        )
        def update_activity(pathname: str) -> List[Component]:
            """Display different page on url update."""
            return self._resolve_pathname(pathname)

