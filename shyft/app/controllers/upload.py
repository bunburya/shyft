import base64
import os
from logging import ERROR
from typing import Optional, List

from werkzeug.utils import secure_filename
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
from dash.exceptions import PreventUpdate

from shyft.logger import get_logger
from shyft.metadata import APP_NAME
from shyft.app.controllers._base import _BaseDashController


logger = get_logger(__name__)


class UploadController(_BaseDashController):
    """Controller for the file upload page."""

    def page_content(self):
        logger.info('Generating page content for upload.')
        return [
            html.Div(id={'type': 'redirect', 'context': 'upload', 'index': 'upload'}, hidden=True),
            html.Div('upload_redirect', hidden=True),
            *self.dc_factory.display_all_messages(),
            html.H1('Upload an activity'),
            dcc.Markdown(f'Here you can select one or more GPX, TCX or FIT files to upload to {APP_NAME}. '
                         f'Uploading several files may take a little while, and there is not currently a progress '
                         'bar to track progress.'),
            dcc.Upload(
                id='upload_data',
                children=html.Div([
                    'Drag and Drop or Select File'
                ]),
                style={
                    'height': '60px',
                    'lineHeight': '60px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'textAlign': 'center',
                    'margin': '10px'
                },
                multiple=True
            ),
            self.dc_factory.footer()

        ]

    def register_callbacks(self):
        logger.debug('Registering callbacks for upload page.')

        @self.dash_app.callback(
            Output({'type': 'redirect', 'context': 'upload', 'index': 'upload'}, 'children'),
            Input('upload_data', 'contents'),
            State('upload_data', 'filename')
        )
        def upload_file(content_list: Optional[List[str]], fname_list: Optional[List[str]]) -> str:
            """Initiate the file upload process, upon the user
            providing one of more files to upload.
            """
            logger.debug(f'upload_file called with filename: {fname_list}')
            if content_list is None:
                # Callback seems to fire on page load, with None as args
                logger.debug('Preventing update.')
                raise PreventUpdate
            else:
                if len(content_list) > 1:
                    for content, fname in zip(content_list, fname_list):
                        self.parse_contents(content, fname)
                    return '/upload'
                else:
                    id = self.parse_contents(content_list[0], fname_list[0])
                    if id is None:
                        return '/upload'
                    else:
                        return f'/activity/{id}'

    def parse_contents(self, contents: str, fname: str) -> Optional[int]:
        tmp_dir = os.path.join(self.config.data_dir, 'tmp')
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)
        logger.info(f'Received uploaded file "{fname}".')
        content_type, content_string = contents.split(',')
        tmp_fpath = os.path.join(tmp_dir, secure_filename(fname))
        with open(tmp_fpath, 'wb') as f:
            logger.info(f'Saving file to "{tmp_fpath}".')
            f.write(base64.b64decode(content_string))
        try:
            id = self.activity_manager.add_activity_from_file(tmp_fpath)
            logger.info(f'Added new activity with ID {id}.')
            self.msg_bus.add_message(f'Uploaded new activity from file {fname}.')
            return id
        except Exception as e:
            logger.error('Error adding activity.', exc_info=e)
            self.msg_bus.add_message(f'Could not upload activity from file "{fname}". '
                                     'Check the logs for details.', severity=ERROR)
            return None
