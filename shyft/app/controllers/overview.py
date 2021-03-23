from typing import List, Tuple, Any, Dict

import plotly.graph_objects as go
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Output, Input, State
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate

from shyft.logger import get_logger
from shyft.app.controllers._base import _BaseDashController
from shyft.app.view.dash_components.overview import OverviewComponentFactory

logger = get_logger(__name__)

class OverviewController(_BaseDashController):
    """Controller for the overview page."""

    DC_FACTORY = OverviewComponentFactory

    def page_content(self) -> List[Component]:
        """Generate page content based on the current configuration and
        activities.
        """
        logger.info('Generating page content for overview.')
        return [
            *self.dc_factory.display_all_messages(),
            self.dc_factory.page_heading(),
            self.dc_factory.graphs_or_no_activity_msg(),
            self.dc_factory.footer()
        ]

    def register_callbacks(self):

        # Scatterplot callbacks

        @self.dash_app.callback(
            Output('overview_main_scatterplot', 'figure'),
            Input('overview_main_scatterplot_x_dropdown', 'value'),
            Input('overview_main_scatterplot_y_dropdown', 'value'),
        )
        def update_main_scatter(x: str, y: str) -> go.Figure:
            return self.dc_factory.main_scatter_fig(x, y)


        @self.dash_app.callback(
            Output('overview_main_scatterplot_link', 'href'),
            Output('overview_main_scatterplot_button', 'disabled'),
            Input('overview_main_scatterplot', 'selectedData')
        )
        def update_main_scatter_link(selected_data: Dict[str, Any]) -> Tuple[str, bool]:
            if not selected_data:
                raise PreventUpdate
            points = selected_data['points']
            if not points:
                return '', True
            elif len(points) == 1:
                href = f'/activity/{points[0]["customdata"][0]}'
            else:
                href = f'/activities?id={",".join([str(p["customdata"][0]) for p in points])}'
            return href, False
