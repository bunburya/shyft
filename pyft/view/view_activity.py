import os
from typing import Sequence

import flask
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table as dt
from dash.dependencies import Output, Input
from pyft.config import Config
from pyft.multi_activity import ActivityManager
from pyft.view.figures import get_map_figure, get_splits_dt, get_activities_table

### FOR TESTING ONLY

import sys
TEST_DATA_DIR = sys.argv[1]

TEST_GPX_FILES = [
    os.path.join(TEST_DATA_DIR, 'GNR_2019.gpx'),
    os.path.join(TEST_DATA_DIR, 'Morning_Run_Miami.gpx'),
    os.path.join(TEST_DATA_DIR, 'Evening_Run_9k_counterclockwise.gpx'),
    os.path.join(TEST_DATA_DIR, 'Evening_Run_9k_counterclockwise_2.gpx'),
    os.path.join(TEST_DATA_DIR, 'Afternoon_Run_7.22k_clockwise.gpx'),
    os.path.join(TEST_DATA_DIR, 'Afternoon_Run_7.23k_counterclockwise.gpx'),
    os.path.join(TEST_DATA_DIR, 'Morning_Run_7k_counterclockwise.gpx'),
]

TEST_DB_FILE = os.path.join(TEST_DATA_DIR, 'dash_test.db')
if os.path.exists(TEST_DB_FILE):
    os.remove(TEST_DB_FILE)

TEST_CONFIG = Config(
    db_file=TEST_DB_FILE
)

am = ActivityManager(TEST_CONFIG)
for fpath in TEST_GPX_FILES:
    am.add_activity_from_gpx_file(fpath)

activity = am.get_activity_by_id(1)
km_summary = activity.km_summary

### /TESTING

#external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
external_stylesheets = [dbc.themes.BOOTSTRAP]

app = flask.Flask(__name__)
dash_app = dash.Dash(__name__, server=app, external_stylesheets=external_stylesheets)

dash_app.layout = html.Div(children=[
    html.H1(
        children='View activity'
    ),

    dbc.Row(
        children=[
            dbc.Col(
                get_splits_dt(
                    id='km_summary',
                    df=km_summary,
                    style_table={
                        'height': 450,
                        'overflowY': 'scroll'
                    },
                    style_cell={
                        'textAlign': 'left'
                    }
                ),
                width=4
            ),

            dbc.Col(
                dcc.Graph(
                    id='map',
                    figure=get_map_figure(activity.points)
                ),
                width=8
            )
        ],
        style={
            'height': 450
        },
        no_gutters=True
    ),

    dbc.Row(children=[
        get_activities_table(activities=am.activities)
    ])

])

@dash_app.callback(
    Output(component_id='map', component_property='figure'),
    [Input(component_id='km_summary', component_property='selected_rows')]
)
def update_map(selected_rows: Sequence[int]):
    #print(selected_rows)
    return get_map_figure(activity.points, highlight_col='km', highlight_vals=selected_rows)

if __name__ == '__main__':
    from sys import argv
    debug = '--debug' in argv
    app.run(host='0.0.0.0', debug=debug, port=8080)