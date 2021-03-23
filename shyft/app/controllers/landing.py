from typing import List

from dash.development.base_component import Component
from shyft.app.controllers._base import _BaseDashController
from shyft.app.view.dash_components.landing_view import LandingViewComponentFactory


class LandingPageController(_BaseDashController):

    DC_FACTORY = LandingViewComponentFactory

    def page_content(self) -> List[Component]:
        return [
            *self.dc_factory.display_all_messages(),
            self.dc_factory.page_heading(),
            self.dc_factory.intro(),
            self.dc_factory.links(),
            self.dc_factory.recent_activities(),
            self.dc_factory.footer()
        ]
