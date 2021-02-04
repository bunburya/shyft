from typing import List, Optional
from urllib.parse import urlsplit

import plotly.graph_objects as go
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Output, Input, State
from pyft.config import Config
from pyft.activity_manager import ActivityManager
from pyft.activity import Activity
from pyft.view.dash_utils import ActivityViewComponentFactory


class ActivityView:

    def __init__(self, activity_manager: ActivityManager, config: Config, *dash_args, **dash_kwargs):

        self.dash_app = dash.Dash(*dash_args, **dash_kwargs)
        self.activity_manager = activity_manager
        self.config = config
        self.dc_factory = ActivityViewComponentFactory(config, activity_manager)
        self.dash_app.layout = self.layout(empty=True)
        self.register_callbacks()

    def register_callbacks(self):

        @self.dash_app.callback(
            Output('map', 'figure'),
            [Input(f'{self.config.distance_unit}_summary', 'selected_rows')],
            [State('map', 'figure'), State('activity_id', 'data')]
        )
        def update_map(selected_rows: List[int], figure: go.Figure, activity_id: int):
            # print(selected_rows)
            # print(f'update_map called with selected rows {selected_rows}')
            activity = self.activity_manager.get_activity_by_id(activity_id)
            new_map = self.dc_factory.map_figure(activity.points, figure=figure,
                                                 highlight_col=self.config.distance_unit,
                                                 highlight_vals=selected_rows)
            # print(new_map.data)
            return new_map

        @self.dash_app.callback(
            Output('page_content', 'children'),
            [Input('activity_id', 'data')]
        )
        def display_page(activity_id: Optional[int]):
            if activity_id is None:
                activity = None
            else:
                # print(f'activity_id: {activity_id} (type {type(activity_id)}')
                activity = self.activity_manager.get_activity_by_id(activity_id)
            return self.page_content(activity)

        @self.dash_app.callback(
            Output('activity_id', 'data'),
            [Input('url', 'pathname')]
        )
        def update_activity(pathname: str):
            # print(f'display_page called with {pathname}')
            try:
                activity_id = int(urlsplit(pathname)[2].split('/')[-1])
            except (TypeError, ValueError):
                activity_id = None

            return activity_id

    def page_content(self, activity: Optional[Activity] = None) -> list:

        if activity is None:
            return [dcc.Markdown('No _activity_elem specified, or no such _activity_elem exists.')]

        return [
            html.H1(f'View _activity_elem: {self.dc_factory.activity_name(activity.metadata)}'),
            html.H2('Activity overview'),
            html.Div([self.dc_factory.activity_overview(activity.metadata)]),
            html.H2('Route'),
            dbc.Row(
                children=[
                    dbc.Col(
                        self.dc_factory.splits_table(
                            id=f'{self.config.distance_unit}_summary',
                            splits_df=activity.get_split_summary(self.config.distance_unit),
                        ),
                        width=4
                    ),

                    dbc.Col(
                        dcc.Graph(
                            id='map',
                            figure=self.dc_factory.map_figure(activity.points)
                        ),
                        width=8
                    )
                ],
                style={
                    'height': 450
                },
                no_gutters=True
            ),
            html.H2('Analysis'),
            *self.dc_factory.custom_graphs(activity),
            html.H2('Recent matched activities'),
            dbc.Row([
                dbc.Col([
                    self.dc_factory.activities_table(
                        self.activity_manager.get_activity_matches(activity.metadata, number=5),
                        id='test'
                    )
                ])
            ])
        ]

    def layout(self, activity: Optional[Activity] = None, empty: bool = True) -> html.Div:

        if empty:
            page_content = []
        else:
            page_content = self.page_content(activity)

        return html.Div(id='main_layout', children=[
            dcc.Store(id='activity_id'),
            dcc.Location(id='url', refresh=False),
            html.Div(
                id='page_content',
                children=page_content
            )
        ])
