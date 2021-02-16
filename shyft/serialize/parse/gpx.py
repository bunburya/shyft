"""Parser for GPX files."""

from collections import Callable
from datetime import datetime, timezone
from typing import Optional, Generator, Tuple

import numpy as np
import pandas as pd
import lxml.etree
import gpxpy
from gpxpy import gpx
from shyft.serialize._xml_namespaces import GPX_NAMESPACES
from shyft.serialize.parse._base import ShyftParserException, BaseParser
from shyft.serialize._activity_types import GARMIN_GPX_TO_SHYFT, STRAVA_GPX_TO_SHYFT, RK_GPX_TO_SHYFT


class GPXParserError(ShyftParserException): pass

class GPXParser(BaseParser):

    STRAVA_TYPES = STRAVA_GPX_TO_SHYFT
    GARMIN_TYPES = GARMIN_GPX_TO_SHYFT
    RK_TYPES = RK_GPX_TO_SHYFT

    # Namespaces for extensions
    # (Even though these relate to Garmin we do not put them in the GarminMixin class because they are also
    # used by Strava-generated GPX files.)
    NAMESPACES = GPX_NAMESPACES

    def __init__(self, *args, **kwargs):
        self._points_df = None
        super().__init__(*args, **kwargs)
        self._metadata['source_format'] = 'gpx'

    def _parse(self, fpath: str):
        with open(fpath) as f:
            self._gpx = gpxpy.parse(f)
        df = pd.DataFrame(self._iter_points(), columns=self.INITIAL_COL_NAMES_POINTS)
        self._points_df = self._handle_points_data(df)
        self._metadata |= {
            'name': self._gpx.name,
            'description': self._gpx.description,
            'date_time': self._get_activity_time(),
            'activity_type': self._get_activity_type()
        }

    def _get_activity_time(self) -> datetime:
        """Return the time the activity was recorded, falling back to
        the time the first point was registered if the GPX file does
        not specify a time for the activity.
        """
        time = self._gpx.time
        if time is not None:
            return self._gpx.time.replace(tzinfo=timezone(self._gpx.time.tzinfo.utcoffset(None)))
        else:
            return self._points_df.iloc[0]['time'].to_pydatetime()

    def _get_activity_type(self) -> str:
        activity_type = 'activity'
        track_type = self._gpx.tracks[0].type
        track_name = self._gpx.tracks[0].name
        if track_type in self.ACTIVITY_TYPES:
            activity_type = track_type
        elif self._gpx.creator.startswith('StravaGPX'):
            activity_type = self.STRAVA_TYPES.get(track_type, activity_type)
        elif self._gpx.creator.startswith('Garmin Connect'):
            activity_type = self.GARMIN_TYPES.get(track_type, activity_type)
        elif self._gpx.creator.startswith('Runkeeper'):
            activity_type = self.RK_TYPES.get(track_name.split(' ')[0], activity_type)
        return activity_type

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
                                            float,
                                            float,
                                            Optional[float],
                                            datetime,
                                            Optional[int],
                                            Optional[int],
                                            None,
                                            None
                                        ], None, None]:
        for point, track_no, segment_no, point_no in self._gpx.walk():
            ext = self._get_garmin_tpe(point)
            hr = self._get_hr(ext)
            cad = self._get_cad(ext)

            # Convert tz from "SimpleTZ" (used by gpxpy)
            time = point.time.replace(tzinfo=timezone(point.time.tzinfo.utcoffset(None)))
            yield (
                point_no,
                point.latitude,
                point.longitude,
                point.elevation,
                time,
                hr,
                cad,
                None,  # lap (GPX data doesn't have laps)
                None   # kmph (GPX data doesn't store speed)
            )

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
