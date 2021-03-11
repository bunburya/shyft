"""Functions to help with rendering data in flask."""
import os
from io import BytesIO
from typing import Callable, Dict, Any, List
from zipfile import ZipFile

from flask import send_file, render_template
from logger import get_logger
from shyft.activity import ActivityMetaData
from shyft.activity_manager import ActivityManager
from shyft.message import MessageBus
from shyft.metadata import APP_NAME, VERSION, URL
from shyft.serialize.parse import PARSERS
from werkzeug.exceptions import abort

logger = get_logger(__name__)

MIMETYPES = {
    '.gpx': 'application/gpx+xml',
    '.fit': 'application/vnd.ant.fit',
    '.tcx': 'application/vnd.garmin.tcx+xml'
}
MIMETYPE_FALLBACK = 'application/octet-stream'


def id_str_to_ints(ids: str) -> List[int]:
    """Convert a string containing comma-separated activity IDs to a
    list of integers, performing some basic verification and raising a
    ValueError is the given id is not valid.
    """
    ids = ids.split(',')
    int_ids = []
    for i in ids:
        try:
            int_ids.append(int(i))
        except (ValueError, TypeError):
            raise ValueError(f'Bad activity id: "{i}".')
    return int_ids


def get_title(page_name: str) -> str:
    """Return the title to be displayed for a page."""
    return f'{page_name} - {APP_NAME}'


def get_footer_rendering_data() -> Dict[str, Any]:
    return {
        'app_name': APP_NAME,
        'app_version': VERSION,
        'app_url': URL
    }


def render_footer() -> str:
    """Render just the footer HTML (excluding the <footer> tag)."""
    return render_template('footer.html.jinja', **get_footer_rendering_data())


class FlaskController:
    """A class with certain state and helper functions for rendering
    data in flask.
    """

    def __init__(self, activity_manager: ActivityManager, msg_bus: MessageBus, stylesheets: List[str]):
        self.am = activity_manager
        self.msg_bus = msg_bus
        self.extensions = PARSERS.keys()
        self.stylesheets = stylesheets

    def is_allowed_file(self, fname: str) -> bool:
        return os.path.splitext(fname)[1].lower() in self.extensions

    def serve_file(self, id: int, fpath_getter: Callable[[ActivityMetaData], str],
                   not_found_msg: str = 'File not found.'):
        """A generic function to serve a file."""
        logger.debug(f'serve_file called with getter func: {fpath_getter}')
        metadata = self.am.get_metadata_by_id(id)
        if metadata is not None:
            fpath = fpath_getter(metadata)
        else:
            fpath = None
        if fpath:
            _, ext = os.path.splitext(fpath)
            mimetype = MIMETYPES.get(ext, MIMETYPE_FALLBACK)
            return send_file(fpath, mimetype=mimetype, as_attachment=True,
                             attachment_filename=os.path.basename(fpath))
        else:
            return abort(404, not_found_msg.format(id=id))

    def serve_files(self, ids: List[int], fpath_getter: Callable[[ActivityMetaData], str],
                    attachment_filename: str, not_found_msg: str = 'One or more files could not be found.'):
        """A generic function to serve multiple files as a zip archive."""
        logger.debug(f'serve_files called with getter func: {fpath_getter}')
        files = [fpath_getter(self.am.get_metadata_by_id(i)) for i in ids]
        zip_bytes = BytesIO()
        try:
            with ZipFile(zip_bytes, mode='w') as z:
                for f in files:
                    logger.debug(f'Adding {f} to zip archive.')
                    z.write(f, os.path.basename(f))
        except FileNotFoundError:
            return abort(404, not_found_msg)
        zip_bytes.seek(0)
        return send_file(zip_bytes, mimetype='application/zip', as_attachment=True,
                         attachment_filename=attachment_filename)

    def serve_files_from_str(self, id_str: str, fpath_getter: Callable[[ActivityMetaData], str],
                             attachment_filename: str, not_found_msg: str = 'One or more files could not be found.'):
        """A generic function to serve a file, or multiple files as a
        zip archive, based on a string which should consist of comma-
        delimited activity IDs.

        `fpath_getter` should be a function that takes a single
        ActivityMetaData instance and returns the path to the file to be
        served.

        `attachment_filename` should be the name of the zip archive to
        be served if multiple IDs are provided.

        `not_found_msg` is the message that will be displayed to the
        user if one or more relevant files is not found.
        """
        try:
            ids = id_str_to_ints(id_str)
        except ValueError:
            return abort(404, 'The query contains one or more bad activity IDs.')
        if len(ids) == 1:
            return self.serve_file(ids[0], fpath_getter, not_found_msg)
        elif len(ids) > 1:
            return self.serve_files(ids, fpath_getter, attachment_filename, not_found_msg)
        else:
            return abort(404, 'Must provide one or more activity IDs (separated by commas).')


    def get_flask_rendering_data(self, page_name: str) -> Dict[str, Any]:
        """Returns a dict containing the data we need to provide as
        arguments to the jinja render function (ignoring any
        page-specific data).
        """
        return {
            'title': get_title(page_name),
            'stylesheets': self.stylesheets,
            'messages': self.msg_bus.get_messages(),
            **get_footer_rendering_data()
        }
