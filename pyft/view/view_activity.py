from typing import List, Optional
from urllib.parse import urlsplit

import plotly.graph_objects as go
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Output, Input, State
from pyft.config import Config
from pyft.multi_activity import ActivityManager
from pyft.single_activity import ActivityMetaData, Activity
from pyft.view.dash_utils import ActivityViewComponentFactory


def get_page_content(
        activity_manager: ActivityManager,
        dc_factory: ActivityViewComponentFactory,
        activity: Optional[Activity] = None
) -> list:

    if activity is None:
        return [dcc.Markdown('No activity specified, or no such activity exists.')]

    return [
        html.H1(f'View activity: {dc_factory.activity_name(activity.metadata)}'),
        html.H2('Activity overview'),
        html.Div([dc_factory.activity_overview(activity.metadata)]),
        html.H2('Route'),
        dbc.Row(
            children=[
                dbc.Col(
                    dc_factory.splits_table(
                        id='km_summary',
                        splits_df=activity.km_summary,
                    ),
                    width=4
                ),

                dbc.Col(
                    dcc.Graph(
                        id='map',
                        figure=dc_factory.map_figure(activity.points)
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
        dbc.Row([
            dbc.Col([
                dcc.Graph(
                    id='graph',
                    figure=dc_factory.activity_graph(activity)
                )
            ])
        ]),
        html.H2('Recent matched activities'),
        dbc.Row([
            dbc.Col([
                dc_factory.activities_table(
                    activity_manager.get_activity_matches(activity.metadata, number=5),
                    id='test'
                )
            ])
        ])
    ]


def get_layout(
        activity_manager: ActivityManager,
        dc_factory: ActivityViewComponentFactory,
        activity: Optional[Activity] = None,
        empty = True
) -> html.Div:

    if empty:
        page_content = []
    else:
        page_content = get_page_content(activity_manager, dc_factory, activity)

    return html.Div(id='main_layout', children=[
        dcc.Store(id='activity_id'),
        dcc.Location(id='url', refresh=False),
        html.Div(
            id='page_content',
            children=page_content
        )
    ])

def get_dash_app(activity_manager: ActivityManager, config: Config, *dash_args, **dash_kwargs) -> dash.Dash:
    dc_factory = ActivityViewComponentFactory(config)
    dash_app = dash.Dash(*dash_args, **dash_kwargs)

    dash_app.layout = get_layout(activity_manager, dc_factory, empty=True)

    @dash_app.callback(
        Output('map', 'figure'),
        [Input('km_summary', 'selected_rows')],
        [State('map', 'figure'), State('activity_id', 'data')]
    )
    def update_map(selected_rows: List[int], figure: go.Figure, activity_id: int):
        # print(selected_rows)
        #print(f'update_map called with selected rows {selected_rows}')
        activity = activity_manager.get_activity_by_id(activity_id)
        new_map = dc_factory.map_figure(activity.points, figure=figure, highlight_col='km',
                                        highlight_vals=selected_rows)
        #print(new_map.data)
        return new_map

    @dash_app.callback(
        Output('page_content', 'children'),
        [Input('activity_id', 'data')]
    )
    def display_page(activity_id: Optional[int]):
        if activity_id is None:
            activity = None
        else:
            #print(f'activity_id: {activity_id} (type {type(activity_id)}')
            activity = activity_manager.get_activity_by_id(activity_id)
        return get_page_content(activity_manager, dc_factory, activity)

    @dash_app.callback(
        Output('activity_id', 'data'),
        [Input('url', 'pathname')]
    )
    def update_activity(pathname: str):
        #print(f'display_page called with {pathname}')
        try:
            activity_id = int(urlsplit(pathname)[2].split('/')[-1])
        except (TypeError, ValueError):
            activity_id = None

        return activity_id

    return dash_app
