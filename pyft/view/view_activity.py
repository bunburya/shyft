import os
import shutil
from typing import Sequence, List

import flask
import plotly.graph_objects as go
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table as dt
from dash.dependencies import Output, Input, State
from pyft.config import Config
from pyft.multi_activity import ActivityManager
from pyft.view.dash_utils import DashComponentFactory

### FOR TESTING ONLY

import sys

TEST_DATA_DIR = sys.argv[1]

TEST_GPX_FILES = [
    os.path.join(TEST_DATA_DIR, 'GNR_2019.gpx'),
    os.path.join(TEST_DATA_DIR, 'Morning_Run_Miami.gpx'),
    os.path.join(TEST_DATA_DIR, 'Evening_Run_9k_counterclockwise.gpx'),
    os.path.join(TEST_DATA_DIR, 'Evening_Run_9k_counterclockwise_2.gpx'),
    # os.path.join(TEST_DATA_DIR, 'Afternoon_Run_7.22k_clockwise.gpx'),
    # os.path.join(TEST_DATA_DIR, 'Afternoon_Run_7.23k_counterclockwise.gpx'),
    # os.path.join(TEST_DATA_DIR, 'Morning_Run_7k_counterclockwise.gpx'),
]
TEST_RUN_DATA_DIR = os.path.join(TEST_DATA_DIR, 'dash_run')
if os.path.exists(TEST_RUN_DATA_DIR):
    shutil.rmtree(TEST_RUN_DATA_DIR)

TEST_DB_FILE = os.path.join(TEST_RUN_DATA_DIR, 'dash_test.db')
TEST_CONFIG_FILE = os.path.join(TEST_DATA_DIR, 'test_config.ini')

TEST_CONFIG = Config(
    TEST_CONFIG_FILE,
    data_dir=TEST_RUN_DATA_DIR,
    db_file=TEST_DB_FILE
)

am = ActivityManager(TEST_CONFIG)
for fpath in TEST_GPX_FILES:
    am.add_activity_from_gpx_file(fpath)

activity = am.get_activity_by_id(0)
km_summary = activity.km_summary

### /TESTING

# external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css', dbc.themes.BOOTSTRAP]

app = flask.Flask(__name__)
dash_app = dash.Dash(__name__, server=app, external_stylesheets=external_stylesheets)

dc_factory = DashComponentFactory(TEST_CONFIG)

dash_app.layout = html.Div(id='main_layout', children=[
    html.H1(
        children=[f'View activity: {dc_factory.get_activity_name(activity.metadata)}']
    ),

    html.Div([dc_factory.get_activity_overview(activity.metadata)]),

    dbc.Row(
        children=[
            dbc.Col(
                dc_factory.get_splits_table(
                    id='km_summary',
                    splits_df=km_summary,
                ),
                width=4
            ),

            dbc.Col(
                dcc.Graph(
                    id='map',
                    figure=dc_factory.get_map_figure(activity.points)
                ),
                width=8
            )
        ],
        style={
            'height': 450
        },
        no_gutters=True
    ),

    dbc.Row([
        dbc.Col([
            dcc.Graph(
                id='graph',
                figure=dc_factory.get_activity_graph(activity)
            )
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dc_factory.get_activities_table(
                am.get_activity_matches(activity.metadata, number=5),
                id='test'
            )
        ])
    ])
])


@dash_app.callback(
    Output(component_id='map', component_property='figure'),
    [Input(component_id='km_summary', component_property='selected_rows')],
    [State(component_id='map', component_property='figure')]
)
def update_map(selected_rows: List[int], figure: go.Figure):
    # print(selected_rows)
    return dc_factory.get_map_figure(activity.points, figure=figure, highlight_col='km', highlight_vals=selected_rows)


if __name__ == '__main__':
    from sys import argv

    debug = '--debug' in argv
    app.run(host='0.0.0.0', debug=debug, port=8080)
