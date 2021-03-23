"""A number of helper functions and classes for generating dashboards.

Most of these are implemented as factory methods which return Dash
objects, which can be included in the layout of the Dash app.
"""
import logging
from typing import Optional, Iterable, List, Dict, Any, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_table as dt
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash import dash
from dash.development.base_component import Component

from shyft.logger import get_logger
from shyft.config import Config
from shyft.activity_manager import ActivityManager
from shyft.activity import ActivityMetaData, Activity
import shyft.message as msg
from shyft.metadata import APP_NAME, VERSION, URL

logger = get_logger(__name__)


class BasicDashComponentFactory:
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

    def __init__(self, dash_app: dash.Dash, activity_manager: ActivityManager, config: Config, msg_bus: msg.MessageBus):
        self.dash_app = dash_app
        self.config = config
        self.activity_manager = activity_manager
        self.msg_bus = msg_bus

    @property
    def summary(self) -> pd.DataFrame:
        return self.activity_manager.summarize_metadata()

    def activity_name(self, metadata: ActivityMetaData) -> str:
        """Return an activity's name or, if the activity has no name,
        generate one using the activity's other metadata.
        """

        return metadata.name_or_default

    def activities_table(self, metadata_list: Iterable[ActivityMetaData], select: bool = False,
                         **kwargs) -> dt.DataTable:
        """A generic function to return a DataTable containing a list of activities."""
        cols = self.ACTIVITY_TABLE_BASIC_COLS[:]
        data = [{
            'thumb': f'![{md.activity_id}]({self.thumbnail_link(md)})',
            'name': f'[{self.activity_name(md)}]({self.activity_link(md)})',
            'id': md.activity_id
        } for md in metadata_list]
        if select:
            row_selectable = 'multi'
        else:
            row_selectable = False
        return dt.DataTable(
            columns=cols,
            data=data,
            cell_selectable=False,
            row_selectable=row_selectable,
            selected_rows=[],
            markdown_options={'link_target': '_self'},
            **self.COMMON_DATATABLE_OPTIONS,
            **kwargs
        )

    def activities_table_with_actions(self, index: str, metadata_list: List[ActivityMetaData], location_id: str,
                                      **table_kwargs) -> List[Component]:
        """A generic function to create an activities table with a
        "Select all" button, an "Unselect all" button and a dropdown
        menu with options to export activities.

        `index` should be unique and will be used to generate the id
        of each component.
        """
        table_id = {'type': 'activity_table', 'index': index}
        select_id = {'type': 'select_all_button', 'index': index}
        unselect_id = {'type': 'unselect_all_button', 'index': index}
        # A hidden div that stores the IDs of the activities to delete (to be send as POST request)
        delete_hidden_id = {'type': 'delete_hidden', 'index': index}
        delete_button_id = {'type': 'delete_button', 'index': index}
        delete_form_id = {'type': 'delete_form', 'index': index}
        dropdown_id = {'type': 'activity_table_dropdown', 'index': index}
        download_link_id = {'type': 'download_link', 'index': index}
        download_button_id = {'type': 'download_button', 'index': index}
        table = self.activities_table(metadata_list, id=table_id, select=True, **table_kwargs)
        dropdown = dcc.Dropdown(dropdown_id, options=[
            {'label': 'Download as...', 'value': 'select'},
            # The below values should correspond to the pathname to redirect to
            {'label': 'Export to GPX', 'value': 'gpx_files'},
            {'label': 'Export to TCX', 'value': 'tcx_files'},
            {'label': 'Download source', 'value': 'source_files'}
        ], value='select')
        select_all_button = dbc.Button('Select all', id=select_id, n_clicks=0, style={'width': '100%'})
        unselect_all_button = dbc.Button('Unselect all', id=unselect_id, n_clicks=0, style={'width': '100%'})
        delete_hidden = dcc.Input(id=delete_hidden_id, type='hidden', name='id', value='')
        delete_button = dbc.Button('Delete', id=delete_button_id, type='submit', style={'width': '100%'})
        delete_form = html.Form([delete_hidden, delete_button], id=delete_form_id, action='/delete', method='POST')
        download_button = dbc.Button('Download', id=download_button_id, disabled=True, style={'width': '100%'})
        download_link = dcc.Link(download_button, id=download_link_id, href='', target='_top')
        action_row = dbc.Row([
            dbc.Col(select_all_button, width=2),
            dbc.Col(unselect_all_button, width=2),
            dbc.Col(delete_form, width=2),
            dbc.Col(dropdown, width=2),
            dbc.Col(download_link, width=2)
        ])

        return [action_row, table]

    def activities_table_html(self, metadata_list: List[ActivityMetaData], select: bool = True) -> html.Table:
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


        table_rows = [html.Tr(header_row)]
        for md in metadata_list:
            data_cells = [
                html.Th(html.Img(src=self.thumbnail_link(md))),
                html.Th(dcc.Link(self.activity_name(md), href=self.activity_link(md)))
            ]
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
        return f'/gpx_files?id={metadata.activity_id}'

    def tcx_file_link(self, metadata: ActivityMetaData) -> str:
        """Returns a (relative) link to the TCX file associated with the
        given activity.
        """
        return f'/tcx_files?id={metadata.activity_id}'

    def source_file_link(self, metadata: ActivityMetaData) -> str:
        """Returns a (relative) link to the source file associated with
         the given activity (ie, the original data file from which the
         Activity was created).
         """
        return f'/source_files?id={metadata.activity_id}'

    def delete_link(self, metadata: ActivityMetaData) -> str:
        """Returns a (relative) link to delete the relevant activity."""
        return f'/delete?id={metadata.activity_id}'

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

    def title(self, page_title: str) -> html.Title:
        """Return a HTML title component which includes `page_title` and
        includes additional text to be included in all page titles.
        """
        return html.Title(f'{page_title} - {APP_NAME}')

    def _get_footer_data(self) -> Dict[str, Any]:
        return {
            'app_name': APP_NAME,
            'app_version': VERSION,
            'app_url': URL
        }

    def footer(self):
        """Return a footer element to be displayed at the bottom of
        the page.

        Because Dash does not have a way to directly render raw HTML,
        we can't just render the jinja template, but have to
        reconstruct an equivalent footer using Dash's html components.
        """
        app_metadata = self._get_footer_data()
        return html.Footer(html.Center([
            html.A(['Main page'], href='/'),
            ' | ',
            html.A(['{app_name} {app_version}'.format(**app_metadata)], href=app_metadata['app_url'])
        ]))


class ActivityViewComponentFactory(BasicDashComponentFactory):
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
        # TODO: This needs to handle deletion as POST now.
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
                'height': 414,  # height of container (450) - height of dropdown (36)
                'overflowY': 'scroll',
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
            fig = px.line_mapbox(df, lat="latitude", lon="longitude", zoom=12, **kwargs)
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
        return dbc.Row([
            dbc.Col([
                dbc.Row(dbc.Col(
                    dcc.Dropdown(
                        id='split_type_dropdown',
                        options=[
                            {'label': 'km splits', 'value': 'km'},
                            {'label': 'mile splits', 'value': 'mile'},
                            {'label': 'laps', 'value': 'lap', 'disabled': activity.laps is None}
                        ],
                        value=self.get_split_type(activity)
                    ),
                    width=12
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
        #], style={'height': 450}, no_gutters=True)
        ], no_gutters=True, id='map_and_splits_row')

    def matched_activities(self, activity: Activity) -> dbc.Row:
        """Return a table listing the given activity's matched activities."""
        matched = self.activity_manager.get_activity_matches(activity.metadata,
                                                             number=self.config.matched_activities_count)
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

    def download_buttons(self, activity: Activity) -> List[dbc.Col]:
        source_download = html.A(dbc.Button('Download source file', style={'width': '100%'}),
                                 href=self.source_file_link(activity.metadata))
        gpx_download = html.A(dbc.Button('Download GPX file', style={'width': '100%'}),
                              href=self.gpx_file_link(activity.metadata))
        tcx_download = html.A(dbc.Button('Download TCX file', style={'width': '100%'}),
                              href=self.tcx_file_link(activity.metadata))
        return [
            dbc.Col(source_download),
            dbc.Col(gpx_download),
            dbc.Col(tcx_download)
        ]

    def delete_button(self, activity: Activity) -> html.Form:
        hidden = dcc.Input(type='hidden', name='id', value=activity.metadata.activity_id)
        button = dbc.Button('Delete', type='submit', style={'width': '100%'})
        return html.Form([hidden, button], action='/delete', method='POST')

    def actions_row(self, activity: Activity) -> dbc.Row:
        children = self.download_buttons(activity)
        children.append(dbc.Col(self.delete_button(activity)))
        return dbc.Row(children)


class OverviewComponentFactory(BasicDashComponentFactory):
    """Methods to generate Dash components used to in an overview of all
    a user's activities.
    """

    def intro(self) -> dcc.Markdown:
        return dcc.Markdown(f'# Activity overview for {self.config.user_name}')

    def weekday_count(self) -> dbc.Row:
        logger.debug('Generating weekday count graph.')
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
        logger.debug('Generating scatterplot of pace vs distance.')
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

    def recent_activities(self) -> dt.DataTable:
        """Return a table of the most recent activities."""
        logger.debug('Generating recent activity table.')
        # logger.debug('Getting metadata...')
        metadata = self.activity_manager.all_metadata
        # logger.debug('Sorting...')
        metadata.sort(key=lambda md: md.date_time, reverse=True)
        # logger.debug('Creating table...')
        return self.activities_table(metadata[:self.config.overview_activities_count], select=False)

    def hr_over_time(self) -> List[Component]:
        logger.debug('Generating graph of average heart rate over time.')
        df = self.activity_manager.metadata_monthly_time_series(activity_type='run')
        # logger.debug(df['mean_hr'])
        graph = dcc.Graph(
            id='hr_over_time',
            figure=px.line(df,
                           y='mean_hr')
        )
        return [graph]

    def graphs_or_no_activity_msg(self, markdown: str = 'No recent activities found. Upload some!') -> List[Component]:
        if self.activity_manager.activity_ids:
            logger.debug('Activities found; generating graphs.')
            return [
                html.H2('Recent activities'),
                self.recent_activities(),
                html.H2('Analysis'),
                self.weekday_count(),
                self.distance_pace(),
                *self.hr_over_time(),
                *self.custom_graphs(),
            ]
        else:
            logger.debug('No activities found; returning markdown.')
            return [dcc.Markdown(markdown)]
