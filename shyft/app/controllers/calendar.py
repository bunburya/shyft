from typing import List
from dash import html
from dash.development.base_component import Component
from shyft.app.controllers._base import _BaseDashController
from shyft.logger import get_logger

_logger = get_logger(__name__)

class CalendarController(_BaseDashController):

    def page_content(self) -> List[Component]:
        return [
            *self.dc_factory.display_all_messages(),
            html.H1('Training calendar'),
            html.Iframe(id='calendar_iframe', src='/_calendar', width='100%', style={'border': 0},
                        height=878,  #  It's not at all easy to dynamically change the height of an iframe to fit its
                                     #  content, so this is a fallback for now.
                        ),
            self.dc_factory.footer()
        ]
