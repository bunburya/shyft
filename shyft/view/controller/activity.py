from typing import List, Optional, Tuple, Dict, Any

import plotly.graph_objects as go
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Output, Input, State
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate

from shyft.config import Config
from shyft.activity_manager import ActivityManager
from shyft.activity import Activity
from shyft.logger import get_logger
from shyft.message import MessageBus
from shyft.view.controller._base import _BaseController
from shyft.view.controller._dash_components import ActivityViewComponentFactory

logger = get_logger(__name__)


class ActivityController(_BaseController):

    DC_FACTORY = ActivityViewComponentFactory

    def __init__(self, activity_manager: ActivityManager, config: Config, msg_bus: MessageBus,  dash_app: dash.Dash):
        super().__init__(activity_manager, config, msg_bus, dash_app)

    def page_content(self, activity: Optional[Activity] = None) -> List[Component]:
        if activity is None:
            raise ValueError('No activity specified, or no such activity exists.')

        return [
            *self.dc_factory.display_all_messages(),
            dcc.Store('activity_id', data=activity.metadata.activity_id),
            html.H1(f'View activity: {self.dc_factory.activity_name(activity.metadata)}'),
            html.H2('Activity overview'),
            html.Div([self.dc_factory.activity_overview(activity.metadata)]),
            html.H2('Route'),
            self.dc_factory.map_and_splits(activity),
            html.H2('Analysis'),
            *self.dc_factory.custom_graphs(activity),
            html.H2('Recent matched activities'),
            self.dc_factory.matched_activities(activity),
            self.dc_factory.footer()
        ]

    def register_callbacks(self):

        @self.dash_app.callback(
            Output('map', 'figure'),
            [Input(f'split_summary_table', 'selected_rows')],
            [State('map', 'figure'), State('activity_id', 'data')]
        )
        def update_map(selected_rows: List[int], figure: go.Figure, activity_id: int) -> go.Figure:
            """Update the map of the activity upon a change in the
            selected splits in the accompanying splits table.
            """
            logger.info('Updating map.')
            activity = self.activity_manager.get_activity_by_id(activity_id)
            new_map = self.dc_factory.map_figure(activity.points, figure=figure,
                                                 highlight_col=self.dc_factory.get_split_type(activity),
                                                 highlight_vals=selected_rows)
            return new_map

        @self.dash_app.callback(
            Output('split_summary_table', 'columns'),
            Output('split_summary_table', 'data'),
            Output('split_summary_table', 'selected_rows'),
            Input('split_type_dropdown', 'value'),
            State('activity_id', 'data')
        )
        def update_split_summary(split_type: str, activity_id: Optional[int]) -> Tuple[List[Dict[str, Any]],
                                                                                       Dict[str, Any],
                                                                                       List[int]]:
            """Update the splits table to reflect the user's choice of
            split type (eg, km, mile, lap). Also resets the
            `selected_rows` property of the splits table so that any
            highlighted splits are reset.
            """
            if activity_id is None:
                raise PreventUpdate
            activity = self.activity_manager.get_activity_by_id(activity_id)
            self.dc_factory.set_split_type(activity, split_type)
            cols, data = self.dc_factory.splits_table_data(activity)
            return cols, data, []

