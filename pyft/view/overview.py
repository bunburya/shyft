import dash

import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Output, Input, State
from pyft.config import Config
from pyft.multi_activity import ActivityManager
from pyft.view.dash_utils import OverviewComponentFactory


def get_dash_app(activity_manager: ActivityManager, config: Config, *dash_args, **dash_kwargs) -> dash.Dash:
    dc_factory = OverviewComponentFactory(config)