import os

from shyft.config import Config
from shyft.serialize.parse._base import BaseParser
from shyft.serialize.parse.fit import FITParser
from shyft.serialize.parse.gpx import gpx_parser_factory
from shyft.serialize.parse.tcx import TCXParser

PARSERS = {
    '.fit': FITParser,
    '.gpx': gpx_parser_factory,
    '.tcx': TCXParser
}

def parser_factory(fpath: str, config: Config) -> BaseParser:
    _, ext = os.path.splitext(fpath.lower())
    try:
        parser = PARSERS[ext]
    except KeyError:
        raise ValueError(f'No suitable parser found for file "{fpath}".')
    return parser(fpath, config)