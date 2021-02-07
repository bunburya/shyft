"""Parser for FIT files."""

from datetime import datetime, timedelta
from typing import Dict, Union, Optional

import fitdecode
import pandas as pd
from pyft.serialize.parse._base import BaseActivityParser, PyftParserException
from pyft.serialize._activity_types import GARMIN_GPX_TO_PYFT


class TCXParserError(PyftParserException): pass


class FITParser(BaseActivityParser):

    GARMIN_TYPES = GARMIN_GPX_TO_PYFT

    MANDATORY_POINT_FIELDS = (
        'position_lat',
        'position_long',
        'timestamp'
    )

    OPTIONAL_POINT_FIELDS = (
        'altitude',
        'heart_rate',
        'cadence'
    )

    MANDATORY_LAP_FIELDS = (
        'start_time',
        'total_distance',
        'total_elapsed_time'
    )

    OPTIONAL_LAP_FIELDS = (
        'total_calories'
    )

    LATLON_TO_DECIMAL = (2 ** 32) / 360

    def __init__(self, *args, **kwargs):
        self._metadata: Dict[str, Union[str, datetime, timedelta, Optional[str]]] = {
            'name': None,
            'description': None
        }
        self._points_data = []
        self._laps_data = []
        super().__init__(*args, **kwargs)

    def _add_point(
            self,
            lat: Optional[float],
            lon: Optional[float],
            elev: Optional[float],
            timestamp: Optional[datetime],
            heart_rate: Optional[int],
            cadence: Optional[int],
            speed: Optional[float]
    ):
        data = {
            'point_no': self._get_point_no(),
            'track_no': 0,
            'segment_no': 0,
            'latitude': None,
            'longitude': None,
            'elevation': elev,
            'time': timestamp,
            'hr': heart_rate,
            'cadence': cadence,
            'lap': self._lap,
            'kmph': self._convert_speed(speed)
        }

        # https://gis.stackexchange.com/questions/122186/convert-garmin-or-iphone-weird-gps-coordinates
        if (lat is not None):
            data['latitude'] = lat / self.LATLON_TO_DECIMAL
        if (lon is not None):
            data['longitude'] = lon / self.LATLON_TO_DECIMAL

        self._handle_backfill(data, self._points_data, lat, lon)

    def _parse_record(self, frame: fitdecode.FitDataMessage):
        """Parse a FitDataMessage of type `record`, which contains
        information about a single point.
        """
        if frame.has_field('timestamp') and frame.has_field('altitude'):
            self._add_point(
                frame.get_value('position_lat', fallback=None),
                frame.get_value('position_long', fallback=None),
                frame.get_value('altitude'),
                frame.get_value('timestamp'),
                frame.get_value('heart_rate', fallback=None),
                frame.get_value('cadence', fallback=None),
                frame.get_value('speed', fallback=None)
            )

    def _parse_lap(self, frame: fitdecode.FitDataMessage):
        """Parse a FitDataMessage of type `lap`, which contains
        information about a lap.
        """
        self._laps_data.append({
            'lap_no': self._get_lap_no(),
            'start_time': frame.get_value('start_time'),
            'distance': frame.get_value('total_distance'),
            'duration': timedelta(seconds=frame.get_value('total_elapsed_time')),
            'calories': frame.get_value('total_calories', fallback=None)
        })

    def _parse_session(self, frame: fitdecode.FitDataMessage):
        """Parse a FitDataMessage of type `session`, which contains
        information about an _activity_elem.
        """
        self._metadata['date_time'] = frame.get_value('start_time')
        self._metadata['activity_type'] = self.GARMIN_TYPES.get(frame.get_value('sport'))
        if frame.has_field('total_elapsed_time'):
            self._metadata['duration'] = timedelta(seconds=frame.get_value('total_elapsed_time'))
        if frame.has_field('total_distance'):
            self._metadata['distance_2d_km'] = frame.get_value('total_distance') / 1000

    def _parse(self, fpath: str):
        with fitdecode.FitReader(fpath) as fit:
            for frame in fit:
                if isinstance(frame, fitdecode.FitDataMessage):
                    if frame.name == 'record':
                        self._parse_record(frame)
                    elif frame.name == 'lap':
                        self._parse_lap(frame)
                    elif frame.name == 'session':
                        self._parse_session(frame)

        self._points = self._handle_points_data(pd.DataFrame(self._points_data, columns=self.INITIAL_COL_NAMES_POINTS))
        self._laps = pd.DataFrame(self._laps_data, columns=self.INITIAL_COL_NAMES_LAPS)

    @property
    def metadata(self) -> dict:
        return self._metadata

    @property
    def activity_type(self) -> str:
        return self._metadata['activity_type']

    @property
    def points(self) -> pd.DataFrame:
        return self._points

    @property
    def laps(self) -> pd.DataFrame:
        return self._laps

    @property
    def date_time(self) -> datetime:
        return self._metadata['date_time']
