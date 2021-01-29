"""A number of helper functions for generating dashboards.

Most of these are implemented as factory methods which return Dash
objects, which can be included in the layout of the Dash app.
"""

from typing import Optional, Iterable, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_table as dt
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from pyft.config import Config
from pyft.multi_activity import ActivityManager
from pyft.single_activity import ActivityMetaData, Activity


class BaseDashComponentFactory:
    """A base for classes that generate Dash various components
    depending on the configuration and the given activity data.

    This base class contains methods and data which are expected to be
    common to all such factory classes.
    """

    # The basic columns to display in an activity table.
    # These may be supplemented in the activities_table method.
    ACTIVITY_TABLE_BASIC_COLS = [
        {'id': 'thumb', 'name': '', 'presentation': 'markdown'},
        {'id': 'name', 'name': 'Activity', 'presentation': 'markdown'}
    ]

    COMMON_DATATABLE_OPTIONS = {
        'style_cell': {
            'textAlign': 'left',
            'fontSize': 20
        },
        'style_data_conditional': [
            {
                # Disable highlighting of selected cells
                'if': {'state': 'active'},
                'backgroundColor': 'transparent',
                'border': '1px solid rgb(211, 211, 211)'
            },
            {
                # Fix size of thumbnail column
                'if': {'column_id': 'thumb'},
                'width': '37px'
            }
        ],
    }

    def __init__(self, config: Config, activity_manager: ActivityManager):
        self.config = config
        self.activity_manager = activity_manager
        self.summary = activity_manager.summarize_activity_data()

    def activity_name(self, metadata: ActivityMetaData) -> str:
        """Return an activity's name or, if the activity has no name,
        generate one using the activity's other metadata.
        """
        name = metadata.name
        if name is None:
            name = self.config.default_activity_name_format.format(**vars(metadata))
        return name

    def activity_row(self, metadata: ActivityMetaData, base_id: str) -> dbc.Row:
        """A generic function to return a Row containing a thumbnail,
        description and link in respect of a particular activity.
        """
        # TODO:  Is this used?
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
                        [f'{self.activity_name(metadata)}'],  # TODO:  Get default name
                        id=f'{base_id}_link_{metadata.activity_id}',
                        href='TODO'  # TODO:  Get relative link to display activity
                    )
                ],
                width=10
            )
        ])

    def activities_table(self, metadata_list: Iterable[ActivityMetaData], options_col: bool = False,
                         **kwargs) -> dt.DataTable:
        """A generic function to return a DataTable containing a list of activities."""
        cols = self.ACTIVITY_TABLE_BASIC_COLS[:]
        data = [{
            'thumb': f'![{md.activity_id}]({self.thumbnail_link(md)})',
            'name': f'[{self.activity_name(md)}]({self.activity_link(md)})',
        } for md in metadata_list]
        if options_col:
            cols.append(
                {'id': 'options', 'name': 'Options', 'presentation': 'markdown'}
            )
            for md, row in zip(metadata_list, data):
                # TODO: Make this open in same tab (not sure if possible)
                row['options'] = f'[Delete]({self.delete_link(md)})'
        return dt.DataTable(
            columns=cols,
            data=data,
            **self.COMMON_DATATABLE_OPTIONS,
            **kwargs
        )

    def activity_link(self, metadata: ActivityMetaData) -> str:
        """Returns a (relative) link to the given activity."""
        return f'/activity/{metadata.activity_id}'

    def thumbnail_link(self, metadata: ActivityMetaData) -> str:
        """Returns a (relative) link to to the thumbnail image of the
        given activity.
        """
        # NOTE:  Not currently used; we just pull metadata.thumbnail_file.
        return f'/thumbnails/{metadata.activity_id}.png'

    def gpx_file_link(self, metadata: ActivityMetaData) -> str:
        """Returns a (relative) link to the GPX file associated with the
        given activity.
        """
        return f'/gpx_files/{metadata.activity_id}'

    def source_file_link(self, metadata: ActivityMetaData) -> str:
        """Returns a (relative) link to the source file associated with
         the given activity (ie, the original data file from which the
         Activity was created).
         """
        return f'/source_files/{metadata.activity_id}'

    def delete_link(self, metadata: ActivityMetaData) -> str:
        """Returns a (relative) link to delete the relevant activity."""
        return f'/delete/{metadata.activity_id}'

    def graph(self, data: pd.DataFrame, graph_type: str, **kwargs) -> go.Figure:
        """A generic function to create a graph object in respect of an Activity.

        graph_type should correspond to the name of a factory function in
        plotly.express.

        Any additional keyword arguments will be passed to the relevant factory
        function.
        """

        func = getattr(px, graph_type)
        for k in kwargs:
            if kwargs[k] is None:
                kwargs[k] = data.index
        return func(data_frame=data, **kwargs)


class ActivityViewComponentFactory(BaseDashComponentFactory):
    """Methods to generate Dash components used to view a single activity."""

    def activity_overview(self, metadata: ActivityMetaData) -> html.Div:
        """Return markdown containing a summary of some key metrics
        about the given activity.
        """
        if self.config.distance_unit == 'km':
            distance = metadata.distance_2d_km
            mean_pace = metadata.km_pace_mean
        elif self.config.distance_unit == 'mile':
            distance = metadata.distance_2d_mile
            mean_pace = metadata.mile_pace_mean
        else:
            raise ValueError(f'Invalid value for distance_unit: \"{self.config.distance_unit}\".')
        return html.Div(
            dcc.Markdown(f"""
                **Distance:**\t{distance} {self.config.distance_unit}

                **Duration:**\t{metadata.duration}

                **Average pace:**\t{mean_pace}

                [Export to GPX]({self.gpx_file_link(metadata)})

                [Download source file]({self.source_file_link(metadata)})

                [Delete]({self.delete_link(metadata)})
            """)
        )

    def splits_table(self, id: str, splits_df: pd.DataFrame, **kwargs) -> dt.DataTable:
        """Return a DataTable with information about an activity broken
        down by split.
        """
        split_col = self.config.distance_unit
        splits_df = splits_df['time'].reset_index()
        splits_df[split_col] += 1
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

    def activity_graph(self, activity: Activity, **kwargs) -> go.Figure:
        """Return a graph with various bits of information relating
        to the given activity.
        """
        fig = px.line(activity.points, x='time', y='kmph')
        return fig

    def custom_graphs(self, activity: Activity) -> List[dbc.Row]:
        """Generate all graphs based on the contents of config.overview_graphs
        (which is in turn generated based on the contents of activity_graphs.json).

        See docs/graphs.md for help on how activity_graphs.json is interpreted.
        """
        graphs = []
        for i, go_data in enumerate(self.config.activity_graphs):
            go_data = go_data.copy()
            source = go_data.pop('data_source')
            if source == 'points':
                data = activity.points
            elif source == 'km_splits':
                data = activity.km_summary
            elif source == 'mile_splits':
                data = activity.mile_summary
            else:
                raise ValueError(f'Bad value for source_data: "{source}".')
            graphs.append(
                dbc.Row(
                    dbc.Col(
                        dcc.Graph(
                            id=f'graph_{i}',
                            figure=self.graph(data, go_data.pop('graph_type'), **go_data)
                        )
                    )
                )
            )
        return graphs

    def map_figure(self, df: pd.DataFrame, highlight_col: Optional[str] = None,
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
                    # Trace has no attribute "name", or its name can't be converted to an int
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

    def matched_activities(self, activity: Activity) -> dbc.Row:
        """Return a table listing the given activity's matched activities."""
        return dbc.Row([
                dbc.Col([
                    self.activities_table(
                        self.activity_manager.get_activity_matches(activity.metadata,
                                                                   number=self.config.matched_activities_count),
                        id='test'
                    )
                ])
            ])


class OverviewComponentFactory(BaseDashComponentFactory):
    """Methods to generate Dash components used to in an overview of all
    a user's activities.
    """

    def intro(self) -> dcc.Markdown:
        return dcc.Markdown(f'# Activity overview for {self.config.user_name}')

    def weekday_count(self) -> dbc.Row:
        counts = self.summary.groupby(['activity_type', 'day']).count()['activity_id'].rename('count')
        for act_type in counts.index.levels[0]:
            for day in self.config.days_of_week:
                if day not in counts[act_type]:
                    counts.loc[act_type, day] = 0
        counts.sort_index(level=1, key=lambda i: i.map(self.config.days_of_week.index), inplace=True)
        bars = []
        for act_type in counts.index.levels[0]:
            bars.append(go.Bar(name=act_type, x=self.config.days_of_week, y=counts[act_type]))
        fig = go.Figure(data=bars)
        fig.update_layout(barmode='stack', title='Most active days of the week')
        return dbc.Row(
            dbc.Col(
                dcc.Graph(id='weekday_count', figure=fig)
            )
        )

    def distance_pace(self) -> dbc.Row:
        return dbc.Row(
            dbc.Col(
                dcc.Graph(
                    id='distance_pace',
                    figure=px.scatter(
                        self.summary,
                        x='distance_2d_km',
                        y='kmph_mean',
                        labels={
                            'distance_2d_km': 'Distance (km)',
                            'kmph_mean': 'Average speed (km/h)'
                        },
                        title='Average speed vs. distance'
                    )
                )
            )
        )

    def custom_graphs(self) -> List[dbc.Row]:
        """Generate all graphs based on the contents of config.overview_graphs
        (which is in turn generated based on the contents of test_overview_graphs.json).

        See docs/graphs.md for help on how test_overview_graphs.json is interpreted.
        """
        graphs = []
        # TODO: Figure this out
        for i, go_data in enumerate(self.config.overview_graphs):
            groupby = go_data.pop('groupby', None)
            agg = go_data.pop('agg', None)
            if groupby and agg:
                data = getattr(self.summary.groupby(groupby), agg)()
            else:
                data = self.summary
            graphs.append(
                dbc.Row(
                    dbc.Col(
                        dcc.Graph(
                            id=f'graph_{i}',
                            figure=self.graph(data, go_data.pop('graph_type'), **go_data)
                        )
                    )
                )
            )
        return graphs

    def recent_activities(self):
        """Return a table of the most recent activities."""
        metadata = [a.metadata for a in self.activity_manager]
        metadata.sort(key=lambda md: md.date_time, reverse=True)
        return self.activities_table(metadata[:self.config.overview_activities_count], options_col=True)