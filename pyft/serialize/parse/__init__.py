import os

from pyft.config import Config
from pyft.serialize.parse._base import BaseParser
from pyft.serialize.parse.fit import FITParser
from pyft.serialize.parse.gpx import GPXParser
from pyft.serialize.parse.tcx import TCXParser

PARSERS = {
    '.fit': FITParser,
    '.gpx': GPXParser,
    '.tcx': TCXParser
}


def parser_factory(fpath: str, config: Config) -> BaseParser:
    _, ext = os.path.splitext(fpath.lower())
    try:
        parser = PARSERS[ext]
    except KeyError:
        raise ValueError(f'No suitable parser found for file "{fpath}".')
    return parser(fpath, config)