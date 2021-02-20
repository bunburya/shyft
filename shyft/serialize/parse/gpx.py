"""Parser for GPX files."""
import logging
import re
from collections import Callable
from datetime import datetime, timezone
from typing import Optional, Generator, Tuple, Dict, Union, Any, List

import numpy as np
import pandas as pd
import lxml.etree
import gpxpy
from gpxpy import gpx
from shyft.config import Config
from shyft.serialize._xml_namespaces import GPX_NAMESPACES
from shyft.serialize.parse._base import ShyftParserException, BaseParser
from shyft.serialize._activity_types import GARMIN_GPX_TO_SHYFT, STRAVA_GPX_TO_SHYFT, RK_GPX_TO_SHYFT, DEFAULT_TYPE


class GPXParserError(ShyftParserException): pass


class GPXParserType(type):
    parsers: List['GPXParserType'] = []

    PATTERN: Union[str, re.Pattern]

    def __new__(mcs, name, base, attrs):
        p = super().__new__(mcs, name, base, attrs)
        GPXParserType.parsers.append(p)
        return p


class BaseGPXParser(BaseParser, metaclass=GPXParserType):
    PATTERN: Optional[Union[str, re.Pattern]] = None

    def __init__(self, gpx: gpxpy.gpx.GPX, fpath: str, config: Config):
        self._points_df = None
        self._gpx = gpx
        super().__init__(fpath, config)
        self._metadata['source_format'] = 'gpx'

    def _parse(self, fpath: str):
        df = pd.DataFrame(self._iter_point_data(), columns=self.INITIAL_COL_NAMES_POINTS)
        self._points_df = self._handle_points_data(df)
        self._metadata = self._parse_metadata()
        self._metadata['source_format'] = 'gpx'

    def _parse_metadata(self) -> Dict[str, Any]:
        """Parse activity metadata from GPX object and return as a dict."""
        return {
            'name': self._gpx.name,
            'description': self._gpx.description,
            'date_time': self._get_activity_time(),
            'activity_type': self._get_activity_type()
        }

    def _get_activity_time(self) -> Optional[datetime]:
        """Return the time the activity was recorded, if specified,
        or None otherwise.
        """
        time = self._gpx.time
        if time is not None:
            return time.replace(tzinfo=timezone(time.tzinfo.utcoffset(None)))
        else:
            return None

    def _get_raw_activity_type(self) -> Optional[str]:
        """Return an activity type exactly as it appears in the GPX
        file (as the type associated with the first track in the file).

        This value must then be converted to a useful type by the
        _get_activity_type method.
        """
        return self._gpx.tracks[0].type

    def _get_activity_type(self) -> str:
        """Return the type of the activity. Must be one of the activity
        types recognised by Shyft. By default, just returns the
        application default activity type, and should be overridden
        by subclasses.
        """
        return DEFAULT_TYPE

    def _get_basic_point_data(self, point: gpx.GPXTrackPoint) -> Dict[str, Union[int, float, datetime, None]]:
        """Return a dict containing a point's latitude, longitude,
        elevation (or None, if no elevation data is present) and the
        time at which it was recorded.

        This is the data that a trkpt element must (or may) have
        according to the GPX schema, ignoring any extensions (which
        should be handled in other methods that may be implemented by
        subclasses).
        """
        # Convert tz from "SimpleTZ" (used by gpxpy)
        time = point.time.replace(tzinfo=timezone(point.time.tzinfo.utcoffset(None)))
        return {
            'latitude': point.latitude,
            'longitude': point.longitude,
            'elevation': point.elevation,
            'time': time
        }

    def _get_additional_point_data(self, point: gpx.GPXTrackPoint) -> Dict[str, Any]:
        """Takes a GPXTrackPoint object and returns a dict containing
        additional data about the point, which may be derived from
        extensions (for example). The keys and values should conform to
        the schema for the points DataFrame.

        By default, returns an empty dict; this method may be
        overridden by subclasses in order to provide more information
        about points.
        """

        return {}

    def _iter_point_data(self) -> Generator[Dict[str, Union[int, float, datetime, None]], None, None]:
        """Generator which iterates through the trackpoints stored in
        the GPX object and yields a dict containing data about each
        point, which will be used to construct the points DataFrame.

        The keys and values should conform to the schema for the points
        DataFrame.
        """
        for point in self._gpx.walk(only_points=True):
            data = self._get_basic_point_data(point)
            data |= self._get_additional_point_data(point)
            yield data

    @property
    def points(self) -> pd.DataFrame:
        """Return a DataFrame with limited information on points (as
        described in INITIAL_COL_NAMES_POINTS). The infer_points_data
        method can be called on the resulting DataFrame to generate
        more data.
        """
        return self._points_df

    @property
    def date_time(self) -> datetime:
        return self._metadata['date_time']

    @property
    def metadata(self) -> dict:
        """Return (selected) metadata for GPX object."""
        return self._metadata

    @property
    def activity_type(self) -> str:
        return self._metadata['activity_type']


class GarminGPXParser(BaseGPXParser):
    """A parser for GPX files generated by Garmin Connect."""

    PATTERN = re.compile(r'\AGarmin Connect')

    ACTIVITY_TYPES = GARMIN_GPX_TO_SHYFT

    # Namespaces for extensions
    NAMESPACES = GPX_NAMESPACES

    def _get_hr(self, elem: lxml.etree._Element) -> Optional[int]:
        try:
            return int(elem.find('garmin_tpe:hr', self.NAMESPACES).text)
        except AttributeError:
            # "text" attribute not found, so presumably None
            return None

    def _get_cad(self, elem: lxml.etree._Element) -> Optional[int]:
        try:
            return int(elem.find('garmin_tpe:cad', self.NAMESPACES).text)
        except AttributeError:
            return None

    def _get_garmin_tpe(self, point: gpx.GPXTrackPoint) -> lxml.etree._Element:
        for ext in point.extensions:
            if ext.tag.startswith(f'{{{self.NAMESPACES["garmin_tpe"]}}}'):
                return ext

    def _get_additional_point_data(self, point: gpx.GPXTrackPoint) -> Dict[str, Any]:
        garmin_tpe = self._get_garmin_tpe(point)
        return {
            'hr': self._get_hr(garmin_tpe),
            'cadence': self._get_cad(garmin_tpe)
        }

    def _get_activity_type(self) -> str:
        raw_type = self._get_raw_activity_type()
        return self.ACTIVITY_TYPES.get(raw_type, DEFAULT_TYPE)


class StravaGPXParser(GarminGPXParser):
    """A parser for GPX files generated by Strava."""

    PATTERN = re.compile(r'\AStravaGPX')

    # Basically the exact same as the GarminGPXParser, except that the types are described differently.

    ACTIVITY_TYPES = STRAVA_GPX_TO_SHYFT

class ShyftGPXParser(GarminGPXParser):
    """A parser for GPX files generated by Shyft."""

    PATTERN = re.compile(r'\AShyft')

    def _get_activity_type(self) -> str:
        # Shyft will create GPX files with the activity types we need
        return self._get_raw_activity_type()


class RunkeeperGPXParser(BaseGPXParser):
    """A parser for GPX files generated by Runkeeper."""

    PATTERN = re.compile(r'\ARunkeeper')

    ACTIVITY_TYPES = RK_GPX_TO_SHYFT

    def _get_activity_type(self) -> str:
        track_name = self._gpx.tracks[0].name
        return self.ACTIVITY_TYPES.get(track_name.split(' ')[0], DEFAULT_TYPE)


def gpx_parser_factory(fpath: str, config: Config) -> BaseGPXParser:
    catchalls = []
    matched = []
    with open(fpath) as f:
        gpx = gpxpy.parse(f)
    creator = gpx.creator
    for p in GPXParserType.parsers:
        if p.PATTERN is None:
            catchalls.append(p)
        elif re.match(p.PATTERN, creator):
            matched.append(p)

    if len(matched) > 1:
        matched_names = [p.__name__ for p in matched]
        logging.warning(f'Creator string `{creator}` matched multiple parsers ({", ".join(matched_names)}. '
                        f'Using the last one ({matched_names[-1]}).')
        parser = matched[-1]
    elif matched:
        parser = matched[0]
    elif len(catchalls) > 1:
        catchall_names = [p.__name__ for p in catchalls]
        logging.warning(f'Creator string `{creator}` did not match any specific parsers, and multiple catchall parsers '
                        f'specified ({", ".join(catchall_names)}. Using the last one ({catchall_names[-1]}).')
        parser = catchalls[-1]
    elif catchalls:
        parser = catchalls[0]
    else:
        msg = f'Creator string `{creator}` did not match any specific parsers, and no catchall parser specified.'
        logging.error(msg)
        raise GPXParserError(msg)

    return parser(gpx, fpath, config)
