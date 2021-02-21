"""Functions to help with rendering data in flask."""
import os
from typing import Callable, Dict, Any, List

from flask import send_file, render_template
from shyft.activity import ActivityMetaData
from shyft.activity_manager import ActivityManager
from shyft.message import MessageBus
from shyft.metadata import APP_NAME, VERSION, URL
from shyft.serialize.parse import PARSERS
from werkzeug.exceptions import abort

MIMETYPES = {
    '.gpx': 'application/gpx+xml',
    '.fit': 'application/vnd.ant.fit',
    '.tcx': 'application/vnd.garmin.tcx+xml'
}
MIMETYPE_FALLBACK = 'application/octet-stream'


def id_str_to_int(id: str) -> int:
    """Convert a string activity id to an integer, performing some
    basic verification and raising a ValueError is the given id is
    not valid.
    """
    try:
        activity_id = int(id)
    except (ValueError, TypeError):
        activity_id = None
    if activity_id is None:
        raise ValueError(f'Bad activity id: "{id}".')
    return activity_id


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

    def id_str_to_metadata(self, id: str) -> ActivityMetaData:
        return self.am.get_metadata_by_id(id_str_to_int(id))

    def is_allowed_file(self, fname: str) -> bool:
        return os.path.splitext(fname)[1].lower() in self.extensions

    def serve_file(self, id: str, fpath_getter: Callable[[ActivityMetaData], str],
                   not_found_msg: str = 'File not found.'):
        """A generic function to serve a file.

        `fpath_getter` should be a function that takes an ActivityMetaData
        instance and returns the path to the file to be served.

        `not_found_msg` is the message that will be displayed to the user
        if the relevant file is not found. It can reference the provided
        ID using Python's string formatting (ie, '{id}').
        """
        try:
            metadata = self.id_str_to_metadata(id)
        except ValueError:
            return abort(404, f'Invalid activity ID specified: "{id}".')
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
