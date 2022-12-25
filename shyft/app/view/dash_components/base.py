from typing import Optional, Iterable, List, Dict, Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_table as dt
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash import dash
from dash.development.base_component import Component

from shyft.logger import get_logger
from shyft.config import Config
from shyft.activity_manager import ActivityManager
from shyft.activity import ActivityMetaData
import shyft.message as msg
from shyft.metadata import APP_NAME, VERSION, URL

_logger = get_logger(__name__)


class BaseDashComponentFactory:
    """A base for classes that generate Dash various components
    depending on the configuration and the given activity data.

    This base class contains methods and data which are expected to be
    common to all such factory classes.
    """

    # The basic columns to display in an activity table.
    # These may be supplemented in the activities_table method.
    ACTIVITY_TABLE_BASIC_COLS = [
        {'id': 'thumb', 'name': '', 'presentation': 'markdown'},
        {'id': 'name', 'name': 'Activity', 'presentation': 'markdown'}
    ]

    COMMON_DATATABLE_OPTIONS = {
        'style_cell': {
            'textAlign': 'left',
            'fontSize': 20
        },
        'style_data_conditional': [
            {
                # Disable highlighting of selected cells
                'if': {'state': 'active'},
                'backgroundColor': 'transparent',
                'border': '1px solid rgb(211, 211, 211)'
            },
            {
                # Fix size of thumbnail column
                'if': {'column_id': 'thumb'},
                'width': '37px'
            }
        ],
    }

    MSG_FG_COLORS = {
        msg.CRITICAL: '#FF0000',
        msg.ERROR: '#FF0000',
        msg.INFO: '#000000',
        msg.DEBUG: '#808080',
        msg.NOTSET: '#808080'
    }

    def __init__(self, dash_app: dash.Dash, activity_manager: ActivityManager, config: Config, msg_bus: msg.MessageBus):
        self.dash_app = dash_app
        self.config = config
        self.activity_manager = activity_manager
        self.msg_bus = msg_bus

    @property
    def summary(self) -> pd.DataFrame:
        return self.activity_manager.summarize_metadata()

    def activity_name(self, metadata: ActivityMetaData) -> str:
        """Return an activity's name or, if the activity has no name,
        generate one using the activity's other metadata.
        """

        return metadata.name_or_default

    def activities_table(self, metadata_list: Iterable[ActivityMetaData], select: bool = False,
                         **kwargs) -> dt.DataTable:
        """A generic function to return a DataTable containing a list of activities."""
        cols = self.ACTIVITY_TABLE_BASIC_COLS[:]
        data = [{
            'thumb': f'![{md.activity_id}]({self.thumbnail_link(md)})',
            'name': f'[{self.activity_name(md)}]({self.activity_link(md)})',
            'id': md.activity_id
        } for md in metadata_list]
        if select:
            row_selectable = 'multi'
        else:
            row_selectable = False
        return dt.DataTable(
            columns=cols,
            data=data,
            cell_selectable=False,
            row_selectable=row_selectable,
            selected_rows=[],
            markdown_options={'link_target': '_self'},
            **self.COMMON_DATATABLE_OPTIONS,
            **kwargs
        )

    def activities_table_with_actions(self, index: str, metadata_list: List[ActivityMetaData], location_id: str,
                                      **table_kwargs) -> List[Component]:
        """A generic function to create an activities table with a
        "Select all" button, an "Unselect all" button and a dropdown
        menu with options to export activities.

        `index` should be unique and will be used to generate the id
        of each component.
        """
        table_id = {'type': 'activity_table', 'index': index}
        select_id = {'type': 'select_all_button', 'index': index}
        unselect_id = {'type': 'unselect_all_button', 'index': index}
        # A hidden div that stores the IDs of the activities to delete (to be send as POST request)
        delete_hidden_id = {'type': 'delete_hidden', 'index': index}
        delete_button_id = {'type': 'delete_button', 'index': index}
        delete_form_id = {'type': 'delete_form', 'index': index}
        dropdown_id = {'type': 'activity_table_dropdown', 'index': index}
        download_link_id = {'type': 'download_link', 'index': index}
        download_button_id = {'type': 'download_button', 'index': index}
        table = self.activities_table(metadata_list, id=table_id, select=True, **table_kwargs)
        dropdown = dcc.Dropdown(dropdown_id, options=[
            {'label': 'Download as...', 'value': 'select'},
            # The below values should correspond to the pathname to redirect to
            {'label': 'Export to GPX', 'value': 'gpx_files'},
            {'label': 'Export to TCX', 'value': 'tcx_files'},
            {'label': 'Download source', 'value': 'source_files'}
        ], value='select')
        select_all_button = dbc.Button('Select all', id=select_id, n_clicks=0, style={'width': '100%'})
        unselect_all_button = dbc.Button('Unselect all', id=unselect_id, n_clicks=0, style={'width': '100%'})
        delete_hidden = dcc.Input(id=delete_hidden_id, type='hidden', name='id', value='')
        delete_button = dbc.Button('Delete', id=delete_button_id, type='submit', style={'width': '100%'})
        delete_form = html.Form([delete_hidden, delete_button], id=delete_form_id, action='/delete', method='POST')
        download_button = dbc.Button('Download', id=download_button_id, disabled=True, style={'width': '100%'})
        download_link = dcc.Link(download_button, id=download_link_id, href='', target='_top')
        action_row = dbc.Row([
            dbc.Col(select_all_button, width=2),
            dbc.Col(unselect_all_button, width=2),
            dbc.Col(delete_form, width=2),
            dbc.Col(dropdown, width=2),
            dbc.Col(download_link, width=2)
        ])

        return [action_row, table]

    def activities_table_html(self, metadata_list: List[ActivityMetaData], select: bool = True) -> html.Table:
        """An experimental alternative to activities_table, which
        returns a HTML table rather than a Dash DataTable. This means
        we can use dcc.Link for links, which would allow us to use
        Dash's faster in-app loading, rather than conventional links
        which reload the page (https://dash-docs.herokuapp.com/urls).

        Not sure there is actually much of a speed gain, so for the
        moment we're using activities_table to take advantage of the
        extra features offered by the DataTable.
        """
        header_row = [
            html.Th('', scope='col'),  # thumbnails
            html.Th('Activity', scope='col')  # activity name
        ]

        table_rows = [html.Tr(header_row)]
        for md in metadata_list:
            data_cells = [
                html.Th(html.Img(src=self.thumbnail_link(md))),
                html.Th(dcc.Link(self.activity_name(md), href=self.activity_link(md)))
            ]
            table_rows.append(html.Tr(data_cells))
        return html.Table(table_rows)

    def activity_link(self, metadata: ActivityMetaData) -> str:
        """Returns a (relative) link to the given activity."""
        return f'/activity/{metadata.activity_id}'

    def thumbnail_link(self, metadata: ActivityMetaData) -> str:
        """Returns a (relative) link to to the thumbnail image of the
        given activity.
        """
        return f'/thumbnails/{metadata.activity_id}.png'

    def gpx_file_link(self, metadata: ActivityMetaData) -> str:
        """Returns a (relative) link to the GPX file associated with the
        given activity.
        """
        return f'/gpx_files?id={metadata.activity_id}'

    def tcx_file_link(self, metadata: ActivityMetaData) -> str:
        """Returns a (relative) link to the TCX file associated with the
        given activity.
        """
        return f'/tcx_files?id={metadata.activity_id}'

    def source_file_link(self, metadata: ActivityMetaData) -> str:
        """Returns a (relative) link to the source file associated with
         the given activity (ie, the original data file from which the
         Activity was created).
         """
        return f'/source_files?id={metadata.activity_id}'

    def delete_link(self, metadata: ActivityMetaData) -> str:
        """Returns a (relative) link to delete the relevant activity."""
        return f'/delete?id={metadata.activity_id}'

    def graph(self, data: pd.DataFrame, graph_type: str, **kwargs) -> go.Figure:
        """A generic function to create a graph object in respect of an Activity.

        graph_type should correspond to the name of a factory function in
        plotly.express.

        Any additional keyword arguments will be passed to the relevant factory
        function.
        """

        func = getattr(px, graph_type)
        for k in kwargs:
            if kwargs[k] is None:
                kwargs[k] = data.index
        return func(data_frame=data, **kwargs)

    def display_message(self, message: msg.Message) -> dcc.Markdown:
        if message.severity >= msg.ERROR:
            prefix = 'ERROR: '
        elif message.severity <= msg.DEBUG:
            prefix = 'DEBUG: '
        else:
            prefix = ''
        return dcc.Markdown(f'*{prefix}{message.text}*', style={'color': self.MSG_FG_COLORS[message.severity]})

    def display_all_messages(self, severity: int = msg.INFO, view: Optional[str] = None) -> List[dcc.Markdown]:
        return [self.display_message(msg) for msg in self.msg_bus.get_messages(severity, view)]

    def title(self, page_title: str) -> html.Title:
        """Return a HTML title component which includes `page_title` and
        includes additional text to be included in all page titles.
        """
        return html.Title(f'{page_title} - {APP_NAME}')

    def _get_footer_data(self) -> Dict[str, Any]:
        return {
            'app_name': APP_NAME,
            'app_version': VERSION,
            'app_url': URL
        }

    def footer(self) -> html.Footer:
        """Return a footer element to be displayed at the bottom of
        the page.

        Because Dash does not have a way to directly render raw HTML,
        we can't just render the jinja template, but have to
        reconstruct an equivalent footer using Dash's html components.
        """
        app_metadata = self._get_footer_data()
        return html.Footer(html.Center([
            html.A(['Main page'], href='/'),
            ' | ',
            html.A(['{app_name} {app_version}'.format(**app_metadata)], href=app_metadata['app_url'])
        ]))

    def activities_filter_menu(self, id: str) -> Component:
        """Return a menu that provides a number of options for filtering
        activities.
        """
        date_range = dcc.DatePickerRange(
            id=f'filter_activities_date_range_{id}',
            start_date=self.activity_manager.earliest_datetime,
            end_date=self.activity_manager.latest_datetime,
            display_format='YYYY-MM-DD'
        )
        type_options = [{'label': 'all types', 'value': ''}]
        for t in self.activity_manager.activity_types:
            type_options.append({'label': t, 'value': t})
        type_dropdown = dcc.Dropdown(f'filter_activities_type_{id}', options=type_options, value='')
        apply_button = dbc.Button('Apply filters', id=f'filter_activities_apply_button_{id}', style={'width': '100%'})
        clear_button = dbc.Button('Clear filters', id=f'filter_activities_clear_button_{id}', style={'width': '100%'})
        return dbc.Row([
            dbc.Col(date_range, width=4),
            dbc.Col(type_dropdown, width=4),
            dbc.Col(apply_button, width=2),
            dbc.Col(clear_button, width=2)
        ])


