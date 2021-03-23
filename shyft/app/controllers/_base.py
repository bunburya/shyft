from __future__ import annotations

from shyft.logger import get_logger
from shyft.app.view.dash_components.base import BaseDashComponentFactory

import typing
if typing.TYPE_CHECKING:
    from main import MainController

logger = get_logger(__name__)

class _BaseDashController:
    """A base class for Dash-related controllers classes."""

    # What component factory class to use. By default, use the basic factory class that can produce components
    # likely to be common to multiple pages; subclasses can override if they need a more specific component factory.
    DC_FACTORY = BaseDashComponentFactory

    def __init__(self, main_controller: MainController, register_callbacks: bool = True):
        logger.info(f'Initialising controller {self.__class__.__name__}.')
        self.main_controller = main_controller
        self.activity_manager = main_controller.activity_manager
        self.config = main_controller.config
        self.msg_bus = main_controller.msg_bus
        self.dash_app = main_controller.dash_app
        self.dc_factory = self.DC_FACTORY(self.dash_app, self.activity_manager, self.config, self.msg_bus)
        if register_callbacks:
            self.register_callbacks()

    def register_callbacks(self):
        pass
