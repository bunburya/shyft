import dash

import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Output, Input, State
from pyft.config import Config
from pyft.multi_activity import ActivityManager
from pyft.view.dash_utils import OverviewComponentFactory


class Overview:

    def __init__(self, activity_manager: ActivityManager, config: Config, *dash_args, **dash_kwargs):
        self.dash_app = dash.Dash(*dash_args, **dash_kwargs)
        self.dc_factory = OverviewComponentFactory(config, activity_manager)
        self.config = config
        self.activity_manager = activity_manager
        self.dash_app.layout = self.layout()

    def layout(self) -> html.Div:
        """Generate a layout based on the current configuration and activities."""

        return html.Div(
            id='overview_layout', children=[
                html.H1(f'Activity overview for {self.config.user_name}'),
                html.H2('Recent activities'),
                self.dc_factory.activities_table([a.metadata for a in self.activity_manager.activities]),
                html.H2('Analysis'),
                self.dc_factory.weekday_count(),
                self.dc_factory.distance_pace(),
                *self.dc_factory.custom_graphs()
            ]
        )

    def update_layout(self):
        self.dash_app.layout = self.layout()
