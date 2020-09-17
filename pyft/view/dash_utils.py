"""A number of helper functions for generating dashboards.

Most of these are implemented as factory functions which return Dash
objects, which can be included in the layout of the Dash app.
"""

import copy
from typing import Sequence, Any, Optional, Iterable, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_table as dt
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from pyft.config import Config
from pyft.single_activity import ActivityMetaData, Activity


class DashComponentFactory:

    ACTIVITY_TABLE_COLS = (
        {'id': 'thumb', 'name': '', 'presentation': 'markdown'},
        {'id': 'name', 'name': 'Activity', 'presentation': 'markdown'},
    )

    COMMON_DATATABLE_OPTIONS = {
        'style_cell': {
            'textAlign': 'left'
        },
        'style_data_conditional': [{
            # Disable highlighting of selected cells
            'if': {'state': 'active'},
            'backgroundColor': 'transparent',
            'border': '1px solid rgb(211, 211, 211)'
        }],
    }

    def __init__(self, config: Config):
        self.config = config

    def get_activity_name(self, metadata: ActivityMetaData) -> str:
        """Return an activity's name or, if the activity has no name,
        generate one using the activity's other metadata.
        """
        name = metadata.name
        if name is None:
            name = f'{metadata.distance_2d_km:0.1f}km {metadata.activity_type} on {metadata.date_time}'
        return name

    def get_splits_table(self, id: str, splits_df: pd.DataFrame, **kwargs) -> dt.DataTable:
        splits_df = splits_df['time'].reset_index()
        splits_df['km'] += 1
        # TODO:  Make this less awful
        splits_df['time'] = splits_df['time'].astype(str).str.split(' ').str[-1].str.split('.').str[:-1]
        cols = [{'name': i, 'id': i} for i in splits_df.columns]
        data = splits_df.to_dict('records')
        return dt.DataTable(
            id=id,
            columns=cols,
            data=data,
            cell_selectable=False,
            row_selectable='multi',
            selected_rows=[],
            style_table={
                'height': 450,
                'overflowY': 'scroll'
            },
            **self.COMMON_DATATABLE_OPTIONS,
            **kwargs
        )

    def get_map_figure(self, df: pd.DataFrame, highlight_col: Optional[str] = None,
                       highlight_vals: Optional[List[int]] = None, figure: Optional[go.Figure] = None,
                       **kwargs) -> go.Figure:
        # TODO:  More helpful hover text
        if figure:
            fig = go.Figure(figure)
        else:
            # TODO: Calculate zoom more intelligently
            fig = px.line_mapbox(df, lat="latitude", lon="longitude", zoom=11, **kwargs)
            fig.update_layout(
                mapbox_style="open-street-map",
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
                showlegend=False
            )
        if (highlight_col is not None) and (highlight_vals is not None):
            traces = [fig.data[0]]
            for trace in fig.data:
                try:
                    tn_int = int(trace.name)
                except (AttributeError, ValueError):
                    # Trace has no attribute name, or its name can't be converted to an int
                    continue
                if tn_int in highlight_vals:
                    traces.append(trace)
                    highlight_vals.remove(tn_int)
            fig.data = traces

            for v in highlight_vals:

                data = df[df[highlight_col] == v]
                fig.add_trace(go.Scattermapbox(
                    mode='lines',
                    lat=data['latitude'],
                    lon=data['longitude'],
                    marker={'color': 'red'},
                    name=v,
                    hoverinfo='text',
                    hovertext=data['time'].dt.strftime('%H:%M:%S')
                ))
        return fig


    def get_activity_graph(self, activity: Activity, **kwargs) -> go.Figure:

        fig = px.line(activity.points, x='time', y='kmph')
        return fig

    def get_activity_row(self, metadata: ActivityMetaData, base_id: str) -> dbc.Row:
        """A generic function to return a DataTable containing a list of activities."""
        return dbc.Row([
            dbc.Col(
                [
                    html.Img(
                        id=f'{base_id}_thumb_{metadata.activity_id}',
                        src='TODO'  # TODO:  Host thumbnails as static content
                    )
                ],
                width=2
            ),

            dbc.Col(
                [
                    html.A(
                        [f'{metadata.name}'],  # TODO:  Get default name
                        id=f'{base_id}_link_{metadata.activity_id}',
                        href='TODO'  # TODO:  Get relative link to display activity
                    )
                ],
                width=10
            )
        ])

    #def get_activities_table(self, metadata: Iterable[ActivityMetaData], base_id: str) -> html.Div:
    #    return html.Div([self.get_activity_row(a, base_id) for a in metadata])

    def get_activities_table(self, metadata_list: Iterable[ActivityMetaData], **kwargs) -> dt.DataTable:
        data = [{
            'thumb': f'![{md.activity_id}]({md.thumbnail_file})',
            'name': f'[{self.get_activity_name(md)}](http://TODO_LINK_TO_ACTIVITY)',
        } for md in metadata_list]
        return dt.DataTable(
            columns=self.ACTIVITY_TABLE_COLS,
            data=data,
            **self.COMMON_DATATABLE_OPTIONS,
            **kwargs
        )
