from dash import dash
from shyft.activity_manager import ActivityManager
from shyft.config import Config
from shyft.logger import get_logger
from shyft.message import MessageBus
from shyft.view.controller._dash_components import BasicDashComponentFactory

logger = get_logger(__name__)

class _BaseController:
    """A base class for Dash-related controller classes."""

    # What component factory class to use. By default, use the basic factory class that can produce components
    # likely to be common to multiple pages; subclasses can override if they need a more specific component factory.
    DC_FACTORY = BasicDashComponentFactory

    def __init__(self, activity_manager: ActivityManager, config: Config, msg_bus: MessageBus, dash_app: dash.Dash):
        logger.info(f'Initialising controller {self.__class__.__name__}.')
        self.activity_manager = activity_manager
        self.config = config
        self.msg_bus = msg_bus
        self.dash_app = dash_app
        self.dc_factory = self.DC_FACTORY(activity_manager, config, msg_bus)
        self.register_callbacks()

    def register_callbacks(self):
        pass
