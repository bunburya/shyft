from typing import List

import dash_core_components as dcc
import dash_html_components as html
from dash import dash
from dash.development.base_component import Component

from shyft.config import Config
from shyft.activity_manager import ActivityManager
from shyft.logger import get_logger
from shyft.message import MessageBus
from shyft.metadata import APP_NAME
from shyft.view.controller._base import _BaseController
from shyft.view.controller._dash_components import OverviewComponentFactory

logger = get_logger(__name__)

class OverviewController(_BaseController):
    """Controller for the overview page."""

    DC_FACTORY = OverviewComponentFactory

    def page_content(self) -> List[Component]:
        """Generate page content based on the current configuration and
        activities.
        """
        logger.info('Generating page content for overview.')
        return [
            self.dc_factory.title('Overview'),
            *self.dc_factory.display_all_messages(),
            html.H1(f'Activity overview for {self.config.user_name}'),
            dcc.Markdown('[Configure](/config)'),
            dcc.Markdown('[Upload](/upload)'),
            html.H2('Recent activities'),
            self.dc_factory.recent_activities(),
            html.H2('Analysis'),
            self.dc_factory.weekday_count(),
            self.dc_factory.distance_pace(),
            *self.dc_factory.custom_graphs(),
            self.dc_factory.footer()
        ]

