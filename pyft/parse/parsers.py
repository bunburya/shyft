from abc import ABC
from datetime import datetime
from typing import Optional, Callable, Tuple

import lxml.etree
import numpy as np
import pandas as pd
import pytz
import gpxpy
from gpxpy import gpx

MILE = 1609.344


class BaseParser:
    ACTIVITY_TYPES = {'run', 'walk', 'hike'}

    # The DataFrame that is passed to infer_points_data must contain all of these columns
    INITIAL_COL_NAMES = (
        'point_no', 'track_no', 'segment_no',
        'latitude', 'longitude', 'elevation',
        'time', 'hr', 'cadence', 'point'
    )

    def infer_points_data(self, df: pd.DataFrame, inplace=False) -> Optional[pd.DataFrame]:
        if missing := set(self.INITIAL_COL_NAMES).difference(df.columns):
            raise ValueError(f'DataFrame is missing the following columns: {missing}.')
        if not inplace:
            df = df.copy()
        df['prev_point'] = df['point'].shift()
        df['step_length_2d'] = self.distance_2d(df['point'], df['prev_point'])
        df['cumul_distance_2d'] = df['step_length_2d'].fillna(0).cumsum()
        df['km'] = (df['cumul_distance_2d'] // 1000).astype(int)
        df['mile'] = (df['cumul_distance_2d'] // MILE).astype(int)
        df['prev_time'] = df['time'].shift()
        df['km_pace'] = (1000 / df['step_length_2d']) * (df['time'] - df['prev_time'])
        # Basic handling of outliers (sometimes the raw data reports a very fast pace for a short period)
        mean_pace = df['km_pace'].mean()
        zscore = (df['km_pace'] - df['km_pace'].mean()) / df['km_pace'].std()
        rolling_mean = (df['km_pace'].shift(fill_value=mean_pace) + df['km_pace'].shift(-1, fill_value=mean_pace)) / 2
        df['km_pace'] = df['km_pace'].where(np.abs(zscore) < 2, rolling_mean)
        df['mile_pace'] = (MILE / df['step_length_2d']) * (df['time'] - df['prev_time'])
        df['kmph'] = (3600 / df['km_pace'].dt.total_seconds()).fillna(0)
        df['mph'] = df['kmph'] / (MILE / 1000)
        df['run_time'] = df['time'] - df.iloc[0]['time']
        df.drop(['point', 'prev_point', 'prev_time'], axis=1, inplace=True)
        if not inplace:
            return df

    def distance_2d(self, p1: pd.Series, p2: pd.Series) -> pd.Series:
        raise NotImplementedError('Child of BaseParser must implement a distance_2d method.')

    @property
    def points(self) -> pd.DataFrame:
        raise NotImplementedError('Child of BaseParser must implement a points_df property.')

    @property
    def date_time(self) -> datetime:
        raise NotImplementedError('Child of BaseParser must implement a date_time property.')

    @property
    def metadata(self) -> dict:
        raise NotImplementedError('Child of BaseParser must implement a metadata property.')

    @property
    def activity_type(self) -> str:
        raise NotImplementedError('Child of BaseParser must implement an activity_type property.')


class GPXParser(BaseParser):
    NAMESPACES = {'garmin_tpe': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1'}

    # TODO: Move these to a separate file.
    # Also, unless we make them comprehensive, we should include a mechanism for Pyft to "learn" from
    # users manually setting an activity type on an activity with an unknown type.
    STRAVA_TYPES = {
        '4': 'hike',
        '9': 'run',
        '10': 'walk',
    }
    GARMIN_TYPES = {
        'hiking': 'hike',
        'running': 'run',
        'walking': 'walk'
    }

    def __init__(self, fpath: str):
        with open(fpath) as f:
            self.gpx = gpxpy.parse(f)
        self.distance_2d = np.vectorize(self._get_try_func(lambda p1, p2: p1.distance_2d(p2)))
        self.distance_3d = np.vectorize(self._get_try_func(lambda p1, p2: p1.distance_3d(p2)))

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

    def _iter_points(self, g: gpx.GPX):
        for point, track_no, segment_no, point_no in g.walk():
            ext = self._get_garmin_tpe(point)
            hr = self._get_hr(ext)
            cad = self._get_cad(ext)

            # Convert tz from "SimpleTZ" used by gpxpy)
            time = point.time.replace(tzinfo=pytz.FixedOffset(point.time.tzinfo.offset))
            yield (
                point_no, track_no, segment_no,
                point.latitude, point.longitude, point.elevation,
                time, hr, cad, point
            )

    @property
    def points(self) -> pd.DataFrame:
        """Return a DataFrame with limited information on points (as
        described in INITIAL_COL_NAMES). The infer_points_data can be
        called on the resulting DataFrame to generate more data.
        """
        df = pd.DataFrame(self._iter_points(self.gpx), columns=self.INITIAL_COL_NAMES)
        self.infer_points_data(df, inplace=True)
        return df

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


def parser_factory(fpath: str) -> BaseParser:
    if fpath.endswith('.gpx'):
        return GPXParser(fpath)
    else:
        raise ValueError(f'No suitable parser found for file "{fpath}".')
