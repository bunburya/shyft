from typing import List, Tuple

import plotly.express as px
import plotly.graph_objects as go
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.development.base_component import Component

from shyft.app.view.dash_components.base import BaseDashComponentFactory
from shyft.logger import get_logger

_logger = get_logger(__name__)


class OverviewComponentFactory(BaseDashComponentFactory):
    """A class for generating Dash components used in an overview of
    multiple activities.
    """

    def page_heading(self) -> Component:
        return html.H1(f'Activity overview for {self.config.user_name}')

    def weekday_count(self) -> Component:
        _logger.debug('Generating weekday count graph.')
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
        return dcc.Graph(id='weekday_count', figure=fig)

    def _axis_labels(self, data_name: str) -> Tuple[str, str]:
        """
        Get appropriate DataFrame column name and readable axis label. 

        :param data_name: Describes what data we want to display. See docs for `main_scatter_fig` and `main_time_fig`
            methods for permitted values.
        :return: A 2-tuple containing the name of the relevant column in the `summary` DataFrame as the first element,
            and the axis label to display to the user as the second element.
        """

        # Single activity attributes (column name must be present in summary dataframe)
        if data_name == 'distance':
            if self.config.distance_unit == 'km':
                return 'distance_2d_km', 'Distance (km)'
            elif self.config.distance_unit == 'mile':
                return 'distance_2d_mile', 'Distance (miles)'
        elif data_name == 'duration':
            return 'duration', 'Duration (minutes)'

        # These can be used for either single activities (summary dataframe) or aggregates (time series dataframe)
        elif data_name == 'mean_speed':
            if self.config.distance_unit == 'km':
                return 'mean_kmph', 'Average speed (km/hour)'
            elif self.config.distance_unit == 'mile':
                return 'mean_mph', 'Average speed (miles/hour)'
        elif data_name == 'mean_hr':
            return 'mean_hr', 'Average heart rate (beats/minute)'

        # Aggregate attributes (column name must be present in time series dataframe)
        elif data_name == 'total_distance':
            if self.config.distance_unit == 'km':
                return 'total_distance_2d_km', 'Total distance (km)'
            elif self.config.distance_unit == 'mile':
                return 'total_distance_2d_mile', 'Total distance (miles)'
        elif data_name == 'total_duration':
            return 'total_duration', 'Total duration (minutes)'
        elif data_name == 'activity_count':
            return 'activity_count', 'Number of activities'

        else:
            raise ValueError(f'Bad value for `data_name`: "{data_name}".')


    def main_scatter_fig(self, x: str, y: str) -> go.Figure:
        """
        Generate the main scatter plot figure.

        :param x: What to display on the x axis. Should be one of `distance`, `mean_speed`, `duration` or `mean_hr`.
        :param y: What to display on the y axis. Has the same permitted values as `x`.
        :return: A go.Figure object representing the scatter plot.
        """
        x_col, x_label = self._axis_labels(x)
        y_col, y_label = self._axis_labels(y)
        fig = px.scatter(
            self.summary,
            x=x_col,
            y=y_col,
            labels={
                x_col: x_label,
                y_col: y_label,
                'activity_type': 'Activity type'
            },
            color='activity_type',
            custom_data=['activity_id']
        )
        fig.update_layout(clickmode='event+select')
        return fig


    def main_scatterplot(self) -> Component:
        """
        A configurable scatterplot of all activities.
        """
        _logger.debug('Generating main scatterplot.')

        x_dropdown = dcc.Dropdown(id='overview_main_scatterplot_x_dropdown', options=[
            {'label': 'Distance', 'value': 'distance'},
            {'label': 'Average speed', 'value': 'mean_speed'},
            {'label': 'Average heart rate', 'value': 'mean_hr'},
            {'label': 'Duration', 'value': 'duration'}
        ], value='distance')
        y_dropdown = dcc.Dropdown(id='overview_main_scatterplot_y_dropdown', options=[
            {'label': 'Distance', 'value': 'distance'},
            {'label': 'Average speed', 'value': 'mean_speed'},
            {'label': 'Average heart rate', 'value': 'mean_hr'},
            {'label': 'Duration', 'value': 'duration'}
        ], value='mean_speed')

        button = dbc.Button('View selected activities', id='overview_main_scatterplot_button')
        link = html.A(button, href='/activities', id='overview_main_scatterplot_link', target='_blank')

        config_row = dbc.Row([
            dbc.Col(html.Div(['x axis:', x_dropdown])),
            dbc.Col(html.Div(['y axis:', y_dropdown])),
            dbc.Col(link, width='auto')
        ], justify='center')

        graph = dcc.Graph(
            id='overview_main_scatterplot',
            figure=self.main_scatter_fig('distance', 'mean_speed')
        )

        return html.Div([
            html.H2('Scatter plot'), config_row, graph
        ])

    _TIME_CHART_TYPES = {
        'mean_speed': px.line,
        'total_distance': px.bar,
        'total_duration': px.bar,
        'mean_hr': px.line,
        'activity_count': px.bar
    }

    def main_time_fig(self, freq: str, y: str) -> go.Figure:
        """
        Generate the chart figure for the main time plot.

        :param freq: What frequency to use for the plot. Should be one
        of "weekly" or "monthly".
        :param y: Value to display on the y axis. Should be one of
        "mean_speed", "total_distance", "total_duration",
        "mean_hr" or "activity_count".
        :return: A go.Figure object representing the appropriate chart.
        The type of the chart will depend on the type of data to be
        displayed on the y axis.
        """
        if freq == 'weekly':
            df = self.activity_manager.metadata_weekly_time_series()
            date_label = 'Week of'
        elif freq == 'monthly':
            df = self.activity_manager.metadata_monthly_time_series()
            date_label = 'Month of'
        else:
            raise ValueError(f'`freq` must be one of "weekly" or "monthly", not "{freq}".')

        if y == 'total_duration':
            # Need to convert timedelta to number of minutes
            df[y] = df[y].dt.total_seconds() / 60

        y_col, y_label = self._axis_labels(y)
        return self._TIME_CHART_TYPES[y](
            df,
            y=y_col,
            labels={
                'date': date_label,
                y_col: y_label
            },
        )

    def main_time_chart(self) -> Component:
        """
        A line chart plotting some selected value over time.
        """
        _logger.debug('Generating time graph.')
        df = self.activity_manager.metadata_weekly_time_series(activity_type='run')

        freq_dropdown = dcc.Dropdown(id='overview_main_time_chart_freq_dropdown', options=[
            {'label': 'Weekly', 'value': 'weekly'},
            {'label': 'Monthly', 'value': 'monthly'}
        ], value='monthly')

        y_dropdown = dcc.Dropdown(id='overview_main_time_chart_y_dropdown', options=[
            {'label': 'Average speed', 'value': 'mean_speed'},
            {'label': 'Total distance', 'value': 'total_distance'},
            {'label': 'Total duration', 'value': 'total_duration'},
            {'label': 'Average heart rate', 'value': 'mean_hr'},
            {'label': 'Number of activities', 'value': 'activity_count'}
        ], value='activity_count')

        graph = dcc.Graph(
            id='overview_main_time_chart',
            figure=self.main_time_fig('weekly', 'activity_count')
        )
        return html.Div([
            html.H2('Progress over time'),
            dbc.Row([
                dbc.Col(html.Div(['Frequency:', freq_dropdown])),
                dbc.Col(html.Div(['y axis:', y_dropdown]))
            ]),
            graph
        ])

    def custom_graphs(self) -> List[Component]:
        """Generate all graphs based on the contents of config.overview_graphs
        (which is in turn generated based on the contents of test_overview_graphs.json).

        See docs/graphs.rst for help on how test_overview_graphs.json is interpreted.
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

    def graphs_or_no_activity_msg(self, markdown: str = 'No recent activities found. Upload some!') -> Component:
        if self.activity_manager.activity_ids:
            _logger.debug('Activities found; generating graphs.')
            return html.Div([
                html.H2('Analysis'),
                self.weekday_count(),
                self.main_scatterplot(),
                self.main_time_chart(),
                *self.custom_graphs(),
            ])
        else:
            _logger.debug('No activities found; returning markdown.')
            return dcc.Markdown(markdown)
