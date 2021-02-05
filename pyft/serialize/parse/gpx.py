"""Parser for GPX files."""

from collections import Callable
from datetime import datetime
from typing import Optional, Generator, Tuple

import numpy as np
import pandas as pd
import lxml.etree
import gpxpy
import pytz
from gpxpy import gpx
from pyft.serialize.parse._base import PyftParserException, BaseParser, GarminMixin, StravaMixin


class GPXParserError(PyftParserException): pass


class GPXParser(BaseParser, GarminMixin, StravaMixin):
    # Namespaces for extensions
    # (Even though these relate to Garmin we do not put them in the GarminMixin class because they are also
    # used by Strava-generated GPX files.)
    NAMESPACES = {'garmin_tpe': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1'}

    def __init__(self, *args, **kwargs):
        self._points_df = None
        super().__init__(*args, **kwargs)

    def _parse(self, fpath: str):
        with open(fpath) as f:
            self.gpx = gpxpy.parse(f)

    def _get_try_func(self, func: Callable[[gpx.GPXTrackPoint, gpx.GPXTrackPoint], float]) \
            -> Callable[[gpx.GPXTrackPoint, gpx.GPXTrackPoint], Optional[float]]:
        def _try_func(p1: gpx.GPXTrackPoint, p2: gpx.GPXTrackPoint) -> Optional[float]:
            try:
                return func(p1, p2)
            except AttributeError:
                return np.nan

        return _try_func

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

    def _iter_points(self) -> Generator[Tuple[
                                            int,
                                            int,
                                            int,
                                            float,
                                            float,
                                            Optional[float],
                                            datetime,
                                            Optional[int],
                                            Optional[int],
                                            None,
                                            None
                                        ], None, None]:
        for point, track_no, segment_no, point_no in self.gpx.walk():
            ext = self._get_garmin_tpe(point)
            hr = self._get_hr(ext)
            cad = self._get_cad(ext)

            # Convert tz from "SimpleTZ" used by gpxpy)
            # TODO: Replace with timezone from datatime or dateutil
            time = point.time.replace(tzinfo=pytz.FixedOffset(point.time.tzinfo.offset))
            yield (
                point_no, track_no, segment_no,
                point.latitude, point.longitude, point.elevation,
                time, hr, cad,
                None,  # lap (GPX data doesn't have laps)
                None   # kmph
            )

    @property
    def points(self) -> pd.DataFrame:
        """Return a DataFrame with limited information on points (as
        described in INITIAL_COL_NAMES_POINTS). The infer_points_data
        method can be called on the resulting DataFrame to generate
        more data.
        """
        if self._points_df is None:
            df = pd.DataFrame(self._iter_points(), columns=self.INITIAL_COL_NAMES_POINTS)
            self._points_df = self._handle_points_data(df)
        return self._points_df

    @property
    def date_time(self) -> datetime:
        try:
            return self.gpx.time.replace(tzinfo=pytz.FixedOffset(self.gpx.time.tzinfo.offset))
        except AttributeError:
            return self.gpx.time

    @property
    def metadata(self) -> dict:
        """Return (selected) metadata for GPX object."""
        return {
            'name': self.gpx.name,
            'description': self.gpx.description,
            'date_time': self.date_time,
            'activity_type': self.activity_type
        }

    @property
    def activity_type(self) -> str:
        activity_type = 'unknown'
        track_type = self.gpx.tracks[0].type
        if track_type in self.ACTIVITY_TYPES:
            activity_type = track_type
        elif self.gpx.creator.startswith('StravaGPX'):
            activity_type = self.STRAVA_TYPES.get(track_type, activity_type)
        elif self.gpx.creator.startswith('Garmin Connect'):
            activity_type = self.GARMIN_TYPES.get(track_type, activity_type)
        return activity_type
