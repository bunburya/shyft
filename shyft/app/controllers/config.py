from typing import List

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component

from shyft.logger import get_logger
from shyft.metadata import APP_NAME
from shyft.app.controllers._base import _BaseController

DAYS_OF_WEEK = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

logger = get_logger(__name__)


class ConfigController(_BaseController):
    label_width = 2
    input_width = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, register_callbacks=False)
        self.raw_config = self.config.raw()
        self.config_file = self.config.ini_fpath
        self.register_callbacks()

    def generate_form(self) -> dbc.Form:
        data_dir_input = dbc.FormGroup([
            dbc.Label('Data directory', html_for='data_dir', width=self.label_width),
            dbc.Col(dbc.Input(id='data_dir', type='text', value=self.raw_config.data_dir), width=self.input_width),
        ], row=True)
        name_input = dbc.FormGroup([
            dbc.Label('Your name', html_for='user_name', width=self.label_width),
            dbc.Col(dbc.Input(id='user_name', type='text', value=self.raw_config.user_name), width=self.input_width)
        ], row=True)
        dist_unit_input = dbc.FormGroup([
            dbc.Label('Preferred unit of distance', html_for='dist_unit', width=self.label_width),
            dbc.Col(dcc.Dropdown(id='dist_unit', options=[
                {'label': 'kilometre', 'value': 'km'},
                {'label': 'mile', 'value': 'mile'}
            ], value=self.raw_config.distance_unit), width=self.input_width)
        ], row=True)
        match_center_input = dbc.FormGroup([
            dbc.Label('Threshold for loose-matching of route centres', html_for='match_center', width=self.label_width),
            dbc.Col(dbc.Input(id='match_center', type='number', value=self.raw_config.match_center_threshold),
                    width=self.input_width)
        ], row=True)
        match_length_input = dbc.FormGroup([
            dbc.Label('Threshold for loose-matching of route lengths', html_for='match_length', width=self.label_width),
            dbc.Col(dbc.Input(id='match_length', type='number', value=self.raw_config.match_length_threshold),
                    width=self.input_width)
        ], row=True)
        tight_match_input = dbc.FormGroup([
            dbc.Label('Threshold for tight-matching routes', html_for='tight_match', width=self.label_width),
            dbc.Col(dbc.Input(id='tight_match', type='number', value=self.raw_config.tight_match_threshold),
                    width=self.input_width)
        ], row=True)
        name_fmt_input = dbc.FormGroup([
            dbc.Label('Format for displaying activity name (where no activity name is specified)',
                      width=self.label_width),
            dbc.Col(dbc.Textarea(id='name_fmt', value=self.raw_config.default_activity_name_format),
                    width=self.input_width)
        ], row=True)
        week_start_input = dbc.FormGroup([
            dbc.Label('The first day of the week', html_for='week_start', width=self.label_width),
            dbc.Col(dcc.Dropdown(id='week_start', options=[{'label': d, 'value': d} for d in DAYS_OF_WEEK],
                                 value=self.raw_config.week_start), width=self.input_width)
        ], row=True)

        buttons = dbc.ButtonGroup([
            dbc.Button('Save', id='save_button', n_clicks=0),
            dbc.Button('Reset', id='reset_button', n_clicks=0)
        ])

        return dbc.Form([
            data_dir_input,
            name_input,
            dist_unit_input,
            match_center_input,
            match_length_input,
            tight_match_input,
            name_fmt_input,
            week_start_input,
            buttons
        ])

    def page_content(self) -> List[Component]:
        return [
            *self.dc_factory.display_all_messages(),
            html.H1(f'Configure {APP_NAME}'),
            dcc.Markdown(f'Here you can configure how {APP_NAME} behaves. See the [documentation](/user_docs/config) '
                         'for more information on some of these options.'),
            self.generate_form(),
            dbc.Modal(id='config_saved_modal', centered=True, children=[
                dbc.ModalHeader('Saved'),
                dbc.ModalBody('Configuration saved!'),
                dbc.ModalFooter(dbc.Button('Close', id='close_config_saved_modal'))
            ]),
            self.dc_factory.footer()
        ]

    def register_callbacks(self):
        logger.debug(f'Registering callbacks for {self.__class__.__name__}.')

        @self.dash_app.callback(
            Output('config_saved_modal', 'is_open'),
            [Input('save_button', 'n_clicks'),
             Input('close_config_saved_modal', 'n_clicks')],
            [State('data_dir', 'value'),
             State('user_name', 'value'),
             State('dist_unit', 'value'),
             State('match_center', 'value'),
             State('match_length', 'value'),
             State('tight_match', 'value'),
             State('name_fmt', 'value'),
             State('week_start', 'value')]
        )
        def save_config(save_button_clicks: int, close_button_clicks: int, data_dir: str, user_name: str,
                        dist_unit: str, match_center: float, match_length: float, tight_match: float, name_fmt: str,
                        week_start: str) -> bool:
            ctx = main.callback_context
            if not ctx.triggered:
                return False
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            logger.debug(f'save_config triggered by f{button_id}.')
            if button_id == 'save_button':
                logger.info(f'Saving configuration to "{self.config_file}".')
                self.raw_config.data_dir = data_dir
                self.raw_config.user_name = user_name
                self.raw_config.distance_unit = dist_unit
                self.raw_config.match_center_threshold = match_center
                self.raw_config.match_length_threshold = match_length
                self.raw_config.tight_match_threshold = tight_match
                self.raw_config.default_activity_name_format = name_fmt
                self.raw_config.week_start = week_start
                self.raw_config.to_file(self.config_file)
                self.config.read_file(self.config_file)
                return True
            elif button_id == 'close_config_saved_modal':
                return False
