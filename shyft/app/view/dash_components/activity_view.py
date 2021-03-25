from typing import Optional, List, Dict, Any, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_table as dt
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc

from shyft.app.view.dash_components.base import BaseDashComponentFactory
from shyft.logger import get_logger
from shyft.activity import ActivityMetaData, Activity

logger = get_logger(__name__)

class ActivityViewComponentFactory(BaseDashComponentFactory):
    """A class for generating Dash components used to view a single
    activity.
    """

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
                logger.warning(f'Could not create graph from file "{source}".', exc_info=True)
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