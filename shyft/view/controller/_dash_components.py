"""A number of helper functions and classes for generating dashboards.

Most of these are implemented as factory methods which return Dash
objects, which can be included in the layout of the Dash app.
"""
import logging
from typing import Optional, Iterable, List, Dict, Callable, Any, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_table as dt
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc

from shyft.config import Config
from shyft.activity_manager import ActivityManager
from shyft.activity import ActivityMetaData, Activity
import shyft.message as msg
from shyft.view.flask_controller import get_footer_rendering_data


class _BaseDashComponentFactory:
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

    MSG_FG_COLORS = {
        msg.CRITICAL: '#FF0000',
        msg.ERROR: '#FF0000',
        msg.INFO: '#000000',
        msg.DEBUG: '#808080',
        msg.NOTSET: '#808080'
    }

    def __init__(self, config: Config, activity_manager: ActivityManager, msg_bus: msg.MessageBus):
        self.config = config
        self.activity_manager = activity_manager
        self.msg_bus = msg_bus
        self.summary = activity_manager.summarize_activity_data()

    def activity_name(self, metadata: ActivityMetaData) -> str:
        """Return an activity's name or, if the activity has no name,
        generate one using the activity's other metadata.
        """
        name = metadata.name
        if name is None:
            name = self.config.default_activity_name_format.format(**vars(metadata))
        return name

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
                row['options'] = f'[Delete]({self.delete_link(md)})'
        return dt.DataTable(
            columns=cols,
            data=data,
            markdown_options={'link_target': '_self'},
            **self.COMMON_DATATABLE_OPTIONS,
            **kwargs
        )

    def activities_table_html(self, metadata_list: List[ActivityMetaData], options_col: bool = False) -> html.Table:
        """An experimental alternative to activities_table, which
        returns a HTML table rather than a Dash DataTable. This means
        we can use dcc.Link for links, which would allow us to use
        Dash's faster in-app loading, rather than conventional links
        which reload the page (https://dash-docs.herokuapp.com/urls).

        Not sure there is actually much of a speed gain, so for the
        moment we're using activities_table to take advantage of the
        extra features offered by the DataTable.
        """
        header_row = [
            html.Th('', scope='col'),  # thumbnails
            html.Th('Activity', scope='col')  # activity name
        ]
        if options_col:
            header_row.append(html.Th('Options', scope='col'))  # options column

        table_rows = [html.Tr(header_row)]
        for md in metadata_list:
            data_cells = [
                html.Th(html.Img(src=self.thumbnail_link(md))),
                html.Th(dcc.Link(self.activity_name(md), href=self.activity_link(md)))
            ]
            if options_col:
                data_cells.append(html.Th(dcc.Link('Delete', href=self.delete_link(md))))
            table_rows.append(html.Tr(data_cells))
        return html.Table(table_rows)

    def activity_link(self, metadata: ActivityMetaData) -> str:
        """Returns a (relative) link to the given activity."""
        return f'/activity/{metadata.activity_id}'

    def thumbnail_link(self, metadata: ActivityMetaData) -> str:
        """Returns a (relative) link to to the thumbnail image of the
        given activity.
        """
        return f'/thumbnails/{metadata.activity_id}.png'

    def gpx_file_link(self, metadata: ActivityMetaData) -> str:
        """Returns a (relative) link to the GPX file associated with the
        given activity.
        """
        return f'/gpx_files/{metadata.activity_id}'

    def tcx_file_link(self, metadata: ActivityMetaData) -> str:
        """Returns a (relative) link to the TCX file associated with the
        given activity.
        """
        return f'/tcx_files/{metadata.activity_id}'

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

    def display_message(self, message: msg.Message) -> dcc.Markdown:
        if message.severity >= msg.ERROR:
            prefix = 'ERROR: '
        elif message.severity <= msg.DEBUG:
            prefix = 'DEBUG: '
        else:
            prefix = ''
        return dcc.Markdown(f'*{prefix}{message.text}*', style={'color': self.MSG_FG_COLORS[message.severity]})

    def display_all_messages(self, severity: int = msg.INFO, view: Optional[str] = None) -> List[dcc.Markdown]:
        return [self.display_message(msg) for msg in self.msg_bus.get_messages(severity, view)]

    def footer(self):
        """Return a footer element to be displayed at the bottom of
        the page.

        Because Dash does not have a way to directly render raw HTML,
        we can't just render the jinja template, but have to
        reconstruct an equivalent footer using Dash's html components.
        """
        app_metadata = get_footer_rendering_data()
        return html.Footer([
            html.A(['Main page'], href='/'),
            ' | ',
            html.A(['{app_name} {app_version}'.format(**app_metadata)], href=app_metadata['app_url'])
        ])


class ActivityViewComponentFactory(_BaseDashComponentFactory):
    """Methods to generate Dash components used to view a single activity."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.split_types: Dict[int, str] = {}

    def set_split_type(self, activity: Activity, split_type: Optional[str]):
        self.split_types[activity.metadata.activity_id] = split_type

    def get_split_type(self, activity: Activity, save: bool = False) -> Optional[str]:
        """Return a string representing the type split to be displayed
         to the user (one of "km", "mile", and "lap").`split_type`.

        Initially consults self.split_types[activity_id]; if that is
        None, then return "lap" if the Activity has lap data, otherwise
        the distance unit specified in the config.

        If `save` is true, save the calculated split type to
        self.split_type[activity_id].
        """
        id = activity.metadata.activity_id
        stored_type = self.split_types.get(id)
        if stored_type is not None:
            split_type = stored_type
        elif activity.laps is not None:
            split_type = 'lap'
        else:
            split_type = self.config.distance_unit

        if save:
            self.set_split_type(activity, split_type)

        return split_type

    def get_splits_df(self, activity: Activity, split_type: Optional[str] = None) -> pd.DataFrame:
        if split_type is None:
            split_type = self.get_split_type(activity)

        if split_type == 'lap':
            if activity.laps is not None:
                return activity.laps
            else:
                raise ValueError('split_type is "lap" but Activity has no laps data.')
        else:
            return activity.get_split_summary(split_type)

    def activity_overview(self, metadata: ActivityMetaData) -> html.Div:
        """Return markdown containing a summary of some key metrics
        about the given activity.
        """
        if self.config.distance_unit == 'km':
            distance = metadata.distance_2d_km
            mean_pace = metadata.mean_km_pace
        elif self.config.distance_unit == 'mile':
            distance = metadata.distance_2d_mile
            mean_pace = metadata.mean_mile_pace
        else:
            raise ValueError(f'Invalid value for distance_unit: \"{self.config.distance_unit}\".')
        return html.Div(
            dcc.Markdown(f"""
                **Distance:**\t{distance} {self.config.distance_unit}

                **Duration:**\t{metadata.duration}

                **Average pace:**\t{mean_pace}

                [Export to GPX]({self.gpx_file_link(metadata)})
                
                [Export to TCX]({self.tcx_file_link(metadata)})

                [Download source file]({self.source_file_link(metadata)})

                [Delete]({self.delete_link(metadata)})
            """)
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

        See user_docs/graphs.md for help on how activity_graphs.json is interpreted.
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
            try:
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
            except Exception as e:
                logging.warning(f'Could not create graph from file "{source}".', exc_info=True)
        return graphs

    def splits_table_data(self, activity: Activity,
                          split_type: Optional[str] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Return a tuple containing the columns and data to be included
        in the splits table. Used to create / update the splits table.
        """
        splits_df = self.get_splits_df(activity, split_type)
        splits_df = splits_df['duration'].reset_index()
        # TODO:  Make this less awful
        splits_df['duration'] = splits_df['duration'].astype(str).str.split(' ').str[-1].str.split('.').str[:-1]
        cols = [{'name': i, 'id': i} for i in splits_df.columns]
        data = splits_df.to_dict('records')
        return cols, data

    def splits_table(self, id: str, activity: Activity, **kwargs) -> dt.DataTable:
        """Return a DataTable with information about an activity broken
        down by split.
        """
        cols, data = self.splits_table_data(activity)
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

    def map_figure(self, df: pd.DataFrame, highlight_col: Optional[str] = None,
                   highlight_vals: Optional[List[int]] = None, figure: Optional[go.Figure] = None,
                   **kwargs) -> go.Figure:
        """Generate the map figure showing an activity's route, from
        the DataFrame containing its points data.

        `highlight_col` specifies what column in the DataFrame to refer
        to when highlighting certain parts of the route, and
        `highlight_vals` specifies what values of that column to
        highlight.
        """
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

    def map_and_splits(self, activity: Activity) -> dbc.Row:
        """Return a Row combining the map of the activity and the list
        of splits/laps.

        `splits` determines what we show in the splits table.
        If `splits` is None and the Activity has laps associated with
        it, show those laps.
        If `splits` is None and there are no laps, show the splits
        corresponding to the distance unit specified in the config.
        If `splits` is not None, it should be one of `lap`, `km` or
        `mile` and will display the corresponding splits.
        """
        return dbc.Row(
            children=[
                dbc.Col(children=[
                    dbc.Row(dbc.Col(
                        dcc.Dropdown(
                            id='split_type_dropdown',
                            options=[
                                {'label': 'km splits', 'value': 'km'},
                                {'label': 'mile splits', 'value': 'mile'},
                                {'label': 'laps', 'value': 'lap', 'disabled': activity.laps is None}
                            ],
                            value=self.get_split_type(activity)
                        )
                    )),
                    dbc.Row(dbc.Col(
                        self.splits_table(
                            id=f'split_summary_table',
                            activity=activity,
                        ),
                        width=12
                    )),
                ], width=4),

                dbc.Col(
                    dcc.Graph(
                        id='map',
                        figure=self.map_figure(activity.points)
                    ),
                    width=8
                )
            ],
            style={
                'height': 450
            },
            no_gutters=True
        )

    def matched_activities(self, activity: Activity) -> dbc.Row:
        """Return a table listing the given activity's matched activities."""
        matched = self.activity_manager.get_activity_matches(activity.metadata,
                                                             number=self.config.matched_activities_count)
        print(matched)
        if matched:
            return dbc.Row([
                dbc.Col([
                    self.activities_table(
                        self.activity_manager.get_activity_matches(activity.metadata,
                                                                   number=self.config.matched_activities_count),
                        id='test'
                    )
                ])
            ])
        else:
            return dcc.Markdown('No other activities match this route.')


class OverviewComponentFactory(_BaseDashComponentFactory):
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
                        y='mean_kmph',
                        labels={
                            'distance_2d_km': 'Distance (km)',
                            'mean_kmph': 'Average speed (km/h)'
                        },
                        title='Average speed vs. distance'
                    )
                )
            )
        )

    def custom_graphs(self) -> List[dbc.Row]:
        """Generate all graphs based on the contents of config.overview_graphs
        (which is in turn generated based on the contents of test_overview_graphs.json).

        See user_docs/graphs.md for help on how test_overview_graphs.json is interpreted.
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
