from datetime import datetime
from typing import Callable, Optional, Tuple

import lxml.etree
import numpy as np
import pandas as pd
import pytz
import gpxpy
from gpxpy import gpx

"""Helper functions for parsing GPX files."""

MILE = 1609.344

namespaces = {'garmin_tpe': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1'}


def get_try_func(func: Callable[[gpx.GPXTrackPoint, gpx.GPXTrackPoint], float]) -> Callable[
        [gpx.GPXTrackPoint, gpx.GPXTrackPoint], float]:
    def _try_func(p1: gpx.GPXTrackPoint, p2: gpx.GPXTrackPoint) -> Optional[float]:
        try:
            return func(p1, p2)
        except AttributeError:
            return np.nan

    return _try_func


distance_2d = np.vectorize(get_try_func(lambda p1, p2: p1.distance_2d(p2)))
distance_3d = np.vectorize(get_try_func(lambda p1, p2: p1.distance_3d(p2)))


def get_hr(elem: lxml.etree._Element) -> Optional[int]:
    try:
        return int(elem.find('garmin_tpe:hr', namespaces).text)
    except AttributeError:
        # "text" attribute not found, so presumably None
        return None


def get_cad(elem: lxml.etree._Element) -> Optional[int]:
    try:
        return int(elem.find('garmin_tpe:cad', namespaces).text)
    except AttributeError:
        return None


def get_garmin_tpe(point: gpx.GPXTrackPoint) -> lxml.etree._Element:
    for ext in point.extensions:
        if ext.tag.startswith(f'{{{namespaces["garmin_tpe"]}}}'):
            return ext


def _iter_points(g: gpx.GPX):
    for point, track_no, segment_no, point_no in g.walk():
        ext = get_garmin_tpe(point)
        hr = get_hr(ext)
        cad = get_cad(ext)

        # Convert tz from "SimpleTZ" used by gpxpy)
        time = point.time.replace(tzinfo=pytz.FixedOffset(point.time.tzinfo.offset))
        yield (
            point_no, track_no, segment_no,
            point.latitude, point.longitude, point.elevation,
            time, hr, cad, point
        )


INITIAL_COL_NAMES = (
    'point_no', 'track_no', 'segment_no',
    'latitude', 'longitude', 'elevation',
    'time', 'hr', 'cadence', 'point'
)


def gpx_points_to_df(g: gpx.GPX) -> pd.DataFrame:
    df = pd.DataFrame(_iter_points(g), columns=INITIAL_COL_NAMES)
    df['prev_point'] = df['point'].shift()
    df['step_length_2d'] = distance_2d(df['point'], df['prev_point'])
    df['cumul_distance_2d'] = df['step_length_2d'].fillna(0).cumsum()
    df['km'] = (df['cumul_distance_2d'] // 1000).astype(int)
    df['mile'] = (df['cumul_distance_2d'] // MILE).astype(int)
    df['prev_time'] = df['time'].shift()
    df['km_pace'] = (1000 / df['step_length_2d']) * (df['time'] - df['prev_time'])
    df['mile_pace'] = (MILE / df['step_length_2d']) * (df['time'] - df['prev_time'])
    df.drop(['point', 'prev_point', 'prev_time'], axis=1, inplace=True)
    return df


def get_gpx_time(g: gpx.GPX) -> datetime:
    try:
        return g.time.replace(tzinfo=pytz.FixedOffset(g.time.tzinfo.offset))
    except AttributeError:
        return g.time


def get_gpx_metadata(g: gpx.GPX) -> dict:
    """Return (selected) metadata for GPX object."""
    return {
        'name': g.name,
        'description': g.description,
        'time': get_gpx_time(g)
    }


def parse_gpx_file(fpath: str, mark_splits: bool = True) -> Tuple[pd.DataFrame, dict]:
    """Parses the file located at `fpath` and returns a tuple containing:
    - a pd.DataFrame with information about each point; and
    - a datetime representing the time of the GPX recording itself.
    """

    with open(fpath) as f:
        g = gpxpy.parse(f)
        return gpx_points_to_df(g), get_gpx_metadata(g)


