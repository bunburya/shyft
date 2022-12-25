import dash_core_components as dcc
import dash_html_components as html
from dash.development.base_component import Component

from shyft.app.view.dash_components.base import BaseDashComponentFactory
from shyft.logger import get_logger
from shyft.metadata import APP_NAME

_logger = get_logger(__name__)


class LandingViewComponentFactory(BaseDashComponentFactory):
    """A class for generating Dash components used to create the landing
    page (the first page the user sees when accessing the app).
    """

    def page_heading(self) -> Component:
        return html.H1(f'Welcome, {self.config.user_name}')

    def intro(self) -> Component:
        return dcc.Markdown(f'This is your {APP_NAME} landing page. From here, you can view your recent activities and '
                            f'view some high-level data about your activities. Use the links below to view more '
                            f'detailed information.')

    def _link(self, link_text: str, href: str, description: str) -> html.Li:
        return html.Li([
            html.B(html.A(link_text, href=href)),
            ': ',
            description
        ])

    def links(self) -> Component:
        return html.Ul([
            self._link('View all activities', '/activities',
                       'A full list of your uploaded activities, which you can filter. From here, you can view more '
                       'detailed information about each activity by clicking on its link.'),
            self._link('Overview', '/overview',
                       'Here, you can view data relating to multiple activities, such as progress over time.'),
            self._link('Upload', '/upload', f'Upload one or more activities to {APP_NAME}.'),
            self._link('Configure', '/config', f'Configure certain aspects of how {APP_NAME} looks and behaves.'),
            self._link('Calendar', '/calendar', 'View your activities in a calendar.')
        ])

    def recent_activities(self) -> Component:
        """Return a table of the most recent activities."""
        _logger.debug('Generating recent activity table.')
        metadata = self.activity_manager.all_metadata
        metadata.sort(key=lambda md: md.date_time, reverse=True)
        return html.Div([
            html.H2('Recent activities'),
            self.activities_table(metadata[:self.config.overview_activities_count], select=False)
        ])
