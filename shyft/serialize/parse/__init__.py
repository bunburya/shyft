import os

from shyft.config import Config
from shyft.serialize.parse._base import BaseParser, logger
from shyft.serialize.parse.fit import FITParser
from shyft.serialize.parse.gpx import gpx_parser_factory
from shyft.serialize.parse.tcx import TCXParser

PARSERS = {
    '.fit': FITParser,
    '.gpx': gpx_parser_factory,
    '.tcx': TCXParser
}

def parser_factory(fpath: str, config: Config) -> BaseParser:
    logger.info(f'Choosing parser for file "{fpath}".')
    _, ext = os.path.splitext(fpath.lower())
    try:
        parser = PARSERS[ext]
    except KeyError:
        raise ValueError(f'No suitable parser found for file "{fpath}".')
    logger.info(f'Chose parser "{parser.__name__}".')
    return parser(fpath, config)