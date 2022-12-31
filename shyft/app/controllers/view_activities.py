from datetime import datetime
from typing import List, Dict, Any

from dash import callback_context, html, dcc
from dash.dependencies import Input, State, Output
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
            html.H2('Filter'),
            self.dc_factory.activities_filter_menu('view_activities'),
            html.H2('Activities'),
            html.Div(id='view_activities_display_container', children=display),
            self.dc_factory.footer()
        ]

    def register_callbacks(self):
        @self.dash_app.callback(
            Output({'type': 'activity_table', 'index': 'view_activities'}, 'data'),
            Input('filter_activities_apply_button_view_activities', 'n_clicks'),
            Input('filter_activities_reset_button_view_activities', 'n_clicks'),
            State('filter_activities_date_range_view_activities', 'start_date'),
            State('filter_activities_date_range_view_activities', 'end_date'),
            State('filter_activities_type_view_activities', 'value')
        )
        def filter_table(
                apply_clicks: int,
                reset_clicks: int,
                start_date: str,
                end_date: str,
                activity_type: str
        ) -> List[dict[str, Any]]:
            """Apply selected filters to the data table, showing only the relevant activities."""

            if callback_context.triggered_id == 'filter_activities_reset_button_view_activities':
                # Callback triggered by clicking "reset" button
                metadata = self.activity_manager.all_metadata
            else:
                # Callback triggered by clicking "apply" button
                if start_date is not None:
                    start_date = datetime.fromisoformat(start_date).date()
                if end_date is not None:
                    end_date = datetime.fromisoformat(end_date).date()

                if activity_type == '' or activity_type == 'all_types':
                    activity_type = None

                metadata = self.activity_manager.search_metadata(
                    from_date=start_date,
                    to_date=end_date,
                    activity_type=activity_type
                )

            return self.dc_factory.metadata_to_tabledata(metadata)
