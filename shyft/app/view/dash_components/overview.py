from typing import List, Tuple

import plotly.express as px
import plotly.graph_objects as go
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.development.base_component import Component

from shyft.app.view.dash_components.base import BaseDashComponentFactory
from shyft.logger import get_logger

logger = get_logger(__name__)


class OverviewComponentFactory(BaseDashComponentFactory):
    """A class for generating Dash components used in an overview of
    multiple activities.
    """

    def page_heading(self) -> Component:
        return html.H1(f'Activity overview for {self.config.user_name}')

    def weekday_count(self) -> Component:
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
        return dcc.Graph(id='weekday_count', figure=fig)

    def _axis_labels_summary(self, data_name: str) -> Tuple[str, str]:
        """
        Get appropriate DataFrame column name and readable axis label. 

        :param data_name: Describes what data we want to display. See
        docs for `main_scatter_fig` method for permitted values.
        :return: A 2-tuple containing the name of the relevant column in
        the `summary` DataFrame as the first element, and the axis label
        to display to the user as the second element.
        """
        if data_name == 'distance':
            if self.config.distance_unit == 'km':
                return 'distance_2d_km', 'Distance (km)'
            elif self.config.distance_unit == 'mile':
                return 'distance_2d_mile', 'Distance(miles)'
        elif data_name == 'mean_speed':
            if self.config.distance_unit == 'km':
                return 'mean_kmph', 'Average speed (km/hour)'
            elif self.config.distance_unit == 'mile':
                return 'mean_mph', 'Average speed (miles/hour)'
        elif data_name == 'duration':
            return 'duration', 'Duration (minutes)'
        elif data_name == 'mean_hr':
            return 'mean_hr', 'Average heart rate (beats/minute)'

    def main_scatter_fig(self, x: str, y: str) -> go.Figure:
        """
        Generate the main scatter plot figure.

        :param x: What to display on the x axis. Should be one of
        `distance`, `mean_speed`, `duration` or `mean_hr`.
        :param y: What to display on the y axis. Has the same
        permitted values as `x`.
        :return: A Figure object representing the scatter plot.
        """
        x_col, x_label = self._axis_labels_summary(x)
        y_col, y_label = self._axis_labels_summary(y)
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
        """A configurable scatterplot of all activities.
        """
        logger.debug('Generating main scatterplot.')

        x_dropdown = dcc.Dropdown('overview_main_scatterplot_x_dropdown', options=[
            {'label': 'Distance', 'value': 'distance'},
            {'label': 'Average speed', 'value': 'mean_speed'},
            {'label': 'Average heart rate', 'value': 'mean_hr'},
            {'label': 'Duration', 'value': 'duration'}
        ], value='distance')
        y_dropdown = dcc.Dropdown('overview_main_scatterplot_y_dropdown', options=[
            {'label': 'Distance', 'value': 'distance'},
            {'label': 'Average speed', 'value': 'mean_speed'},
            {'label': 'Average heart rate', 'value': 'mean_hr'},
            {'label': 'Duration', 'value': 'duration'}
        ], value='mean_speed')

        button = dbc.Button('View selected', id='overview_main_scatterplot_button', disabled=True)
        link = html.A(button, href='', id='overview_main_scatterplot_link', target='_blank')

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

    def hr_over_time(self) -> Component:
        logger.debug('Generating graph of average heart rate over time.')
        df = self.activity_manager.metadata_weekly_time_series(activity_type='run')
        graph = dcc.Graph(
            id='hr_over_time',
            figure=px.line(
                df,
                y='mean_hr',
                labels={
                    'date': 'Date',
                    'mean_hr': 'Average heart rate (beats/minute)'
                },
            )
        )
        return html.Div([
            html.H2('Change over time'),
            graph
        ])

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

    def graphs_or_no_activity_msg(self, markdown: str = 'No recent activities found. Upload some!') -> Component:
        if self.activity_manager.activity_ids:
            logger.debug('Activities found; generating graphs.')
            return html.Div([
                html.H2('Analysis'),
                self.weekday_count(),
                self.main_scatterplot(),
                self.hr_over_time(),
                *self.custom_graphs(),
            ])
        else:
            logger.debug('No activities found; returning markdown.')
            return dcc.Markdown(markdown)
