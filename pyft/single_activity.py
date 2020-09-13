from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Tuple, Callable, Optional, Any

import lxml.etree
import pandas as pd
import numpy as np
import pytz

import gpxpy
from pyft.database import DatabaseManager
from pyft.geo_utils import intersect_points
from pyft.parse_gpx import parse_gpx_file, MILE


@dataclass
class ActivityMetaData:
    """A dataclass representing a brief summary of an activity."""

    activity_type: str
    date_time: datetime
    distance_2d: float = None
    center: np.ndarray = None
    points_std: np.ndarray = None
    activity_id: Optional[int] = None
    prototype_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    data_file: Optional[str] = None


@dataclass
class Activity:
    """ A dataclass representing a single activity.  Stores the points (as a pd.DataFrame),
    as well as some metadata about the activity.  We only separately store data about
    the activity which cannot easily and quickly be deduced from the points."""

    metadata: ActivityMetaData
    points: pd.DataFrame

    def __init__(self, points: pd.DataFrame, *args, **kwargs):
        self.points = points
        self.metadata = ActivityMetaData(*args, **kwargs)
        if self.metadata.distance_2d is None:
            self.metadata.distance_2d = self.points['cumul_distance_2d'].iloc[-1]
        if self.metadata.center is None:
            self.metadata.center = self.points[['latitude', 'longitude', 'elevation']].mean().to_numpy()
        if self.metadata.points_std is None:
            self.metadata.points_std = self.points[['latitude', 'longitude', 'elevation']].std().to_numpy()

    def get_split_markers(self, split_col: str, split_len: float) -> pd.DataFrame:
        """Takes a DataFrame, calculates the points that lie directly on
        the boundaries between splits and returns those points as a
        DataFrame.
        """
        df = self.points
        min_split = df[split_col].min()
        max_split = df[split_col].max()
        markers = []
        for i in range(int(min_split) + 1, int(max_split) + 1):
            p1 = df[df[split_col] == i - 1].iloc[-1]
            p2 = df[df[split_col] == i].iloc[0]
            overrun = p2['cumul_distance_2d'] - (split_len * i)
            underrun = (split_len * i) - p1['cumul_distance_2d']
            portion = underrun / (underrun + overrun)
            markers.append(intersect_points(p1, p2, portion))
        return pd.DataFrame(markers)

    @property
    def km_markers(self):
        return self.get_split_markers('km', 1000)

    @property
    def mile_markers(self):
        return self.get_split_markers('mile', MILE)

    def split_summary(self, split_col: str, pace_col: str) -> pd.DataFrame:
        splits = self.points[[split_col, pace_col, 'time', 'cadence', 'hr', 'elevation']]
        grouped = splits.groupby(split_col)
        summary = grouped.mean()
        first = grouped.apply(lambda s: s.iloc[0])
        last = grouped.apply(lambda s: s.iloc[-1])
        summary['time'] = last['time'] - first['time']
        return summary

    @property
    def km_summary(self):
        return self.split_summary('km', 'km_pace')

    @property
    def mile_summary(self):
        return self.split_summary('mile', 'mile_pace')

    @staticmethod
    def from_gpx_file(fpath: str, activity_name: str = None, activity_description: str = None,
                      activity_type: str = 'run') -> 'Activity':
        points, metadata = parse_gpx_file(fpath)
        _distance_2d = points['cumul_distance_2d'].iloc[-1]
        center = points[['latitude', 'longitude', 'elevation']].mean()
        return Activity(
            points,
            activity_type=activity_type,
            date_time=metadata['time'],
            distance_2d=_distance_2d,
            center=center,
            data_file=fpath,
            name=activity_name or metadata['name'],
            description=activity_description or metadata['description']
        )
