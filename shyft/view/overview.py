import logging

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc

from dash.dependencies import Output, Input, State
from shyft.config import Config
from shyft.activity_manager import ActivityManager
from shyft.message import MessageBus
from shyft.view.dash_utils import OverviewComponentFactory

logger = logging.getLogger(__name__)

class Overview:

    def __init__(self, activity_manager: ActivityManager, msg_bus: MessageBus, config: Config,
                 *dash_args, **dash_kwargs):
        self.dash_app = dash.Dash(*dash_args, **dash_kwargs)
        self.dc_factory = OverviewComponentFactory(config, activity_manager, msg_bus)
        self.config = config
        self.activity_manager = activity_manager
        self.dash_app.layout = self.layout()

    def layout(self) -> html.Div:
        """Generate a layout based on the current configuration and activities."""

        logger.info('Loading overview layout.')
        return html.Div(
            id='overview_layout', children=[
                *self.dc_factory.display_all_messages(),
                html.H1(f'Activity overview for {self.config.user_name}'),
                dcc.Markdown('[Configure](/config)'),
                dcc.Markdown('[Upload](/upload)'),
                html.H2('Recent activities'),
                self.dc_factory.recent_activities(),
                html.H2('Analysis'),
                self.dc_factory.weekday_count(),
                self.dc_factory.distance_pace(),
                *self.dc_factory.custom_graphs()
            ]
        )

    def update_layout(self):
        self.dash_app.layout = self.layout()
