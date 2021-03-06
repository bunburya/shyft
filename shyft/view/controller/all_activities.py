from typing import List

from _base import _BaseController
import dash_core_components as dcc
import dash_html_components as html
from dash.development.base_component import Component


class AllActivitiesController(_BaseController):

    def page_content(self) -> List[Component]:
        metadata = self.activity_manager.search_metadata()
        if metadata:
            #display = self.dc_factory.activities_table(metadata, select=True, id='all_activities_table')
            display = self.dc_factory.activities_table_with_actions('all_activities', metadata, 'all_action_location')
        else:
            display = dcc.Markdown('No activities found. Upload some or change search criteria.')
        return [
            html.Div(id={'type': 'redirect', 'context': 'activity_table', 'index': 'all_activities'}, hidden=True),
            *self.dc_factory.display_all_messages(),
            html.H1('View activities'),
            html.Div(id='all_activities_display_container', children=display),
            self.dc_factory.footer()
        ]