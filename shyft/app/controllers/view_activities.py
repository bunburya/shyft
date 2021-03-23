from typing import List, Dict

import dash_core_components as dcc
import dash_html_components as html
from dash.development.base_component import Component

from shyft.app.controllers._base import _BaseDashController


class ViewActivitiesController(_BaseDashController):

    def page_content(self, params: Dict[str, str]) -> List[Component]:
        metadata = self.main_controller.url_params_to_metadata(params)
        if metadata:
            #display = self.dc_factory.activities_table(metadata, select=True, id='all_activities_table')
            display = self.dc_factory.activities_table_with_actions('view_activities', metadata,
                                                                    'view_activities_action_location')
        else:
            display = dcc.Markdown('No activities found. Upload some or change search criteria.')
        return [
            html.Div(id={'type': 'redirect', 'context': 'activity_table', 'index': 'view_activities'}, hidden=True),
            *self.dc_factory.display_all_messages(),
            html.H1('View activities'),
            html.Div(id='view_activities_display_container', children=display),
            self.dc_factory.footer()
        ]