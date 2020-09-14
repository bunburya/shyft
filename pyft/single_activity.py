import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Tuple, Callable, Optional, Any

import lxml.etree
import pandas as pd
import numpy as np
import pytz

import gpxpy
from pyft.config import Config
from pyft.database import DatabaseManager
from pyft.geo_utils import intersect_points
from pyft.parse_gpx import parse_gpx_file, MILE

pd.options.plotting.backend = "plotly"


@dataclass
class ActivityMetaData:
    """A dataclass representing a brief summary of an activity."""

    # NOTE:  Changes to the data stored in ActivityMetaData also need to be reflected in:
    # - DatabaseManager.ACTIVITIES;
    # - DatabaseManager.SAVE_ACTIVITY_DATA;
    # - DatabaseManager.save_activity_data;

    activity_id: int
    activity_type: str
    date_time: datetime
    distance_2d: float = None
    center: np.ndarray = None
    points_std: np.ndarray = None
    km_pace_mean: timedelta = None
    mile_pace_mean: timedelta = None
    duration: timedelta = None
    prototype_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    thumbnail_file: Optional[str] = None
    data_file: Optional[str] = None


@dataclass
class Activity:
    """ A dataclass representing a single activity.  Stores the points (as a pd.DataFrame),
    as well as some metadata about the activity.  We only separately store data about
    the activity which cannot easily and quickly be deduced from the points."""

    metadata: ActivityMetaData
    points: pd.DataFrame

    def __init__(self, config: Config, points: pd.DataFrame, metadata: Optional[ActivityMetaData] = None, **kwargs):
        self.config = config
        self.points = points
        if metadata is not None:
            self.metadata = metadata
        else:
            self.metadata = ActivityMetaData(**kwargs)

        if self.metadata.distance_2d is None:
            self.metadata.distance_2d = self.points['cumul_distance_2d'].iloc[-1]
        if self.metadata.center is None:
            self.metadata.center = self.points[['latitude', 'longitude', 'elevation']].mean().to_numpy()
        if self.metadata.points_std is None:
            self.metadata.points_std = self.points[['latitude', 'longitude', 'elevation']].std().to_numpy()
        if self.metadata.km_pace_mean is None:
            self.metadata.km_pace_mean = self.points['km_pace'].mean()
        if self.metadata.mile_pace_mean is None:
            self.metadata.mile_pace_mean = self.points['mile_pace'].mean()
        if self.metadata.duration is None:
            self.metadata.duration = self.points.iloc[-1]['time'] - self.metadata.date_time
        if (self.metadata.thumbnail_file is None) and config.thumbnail_dir:
            self.metadata.thumbnail_file = self.write_thumbnail()

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

    def get_split_summary(self, split_col: str, pace_col: str) -> pd.DataFrame:
        splits = self.points[[split_col, pace_col, 'time', 'cadence', 'hr', 'elevation']]
        grouped = splits.groupby(split_col)
        summary = grouped.mean()
        first = grouped.apply(lambda s: s.iloc[0])
        last = grouped.apply(lambda s: s.iloc[-1])
        summary['time'] = last['time'] - first['time']
        return summary

    @property
    def km_summary(self):
        return self.get_split_summary('km', 'km_pace')

    @property
    def mile_summary(self):
        return self.get_split_summary('mile', 'mile_pace')

    def write_thumbnail(self, fpath: Optional[str] = None) -> str:
        """Create a thumbnail representing the route and write it to
        fpath (determined by the config if not explicitly provided.
        Returns the path to which the image was saved.
        """
        # TODO:  Would be better not to rely on plotly / kaleido for this;
        # maybe roll our own using pillow.
        if fpath is None:
            fpath = os.path.join(self.config.thumbnail_dir, f'thumb_{self.metadata.activity_id}.png')

        fig = self.points.plot(
            x='longitude',
            y='latitude'
        )

        fig.update_traces(line={
            'width': 10
        })

        fig.update_layout({
            # Transparent background
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'plot_bgcolor': 'rgba(0,0,0,0)',
            # Disable axis labels, grid lines, etc
            'xaxis': {
                'showgrid': False,
                'zeroline': False,
                'visible': False,
            },
            'yaxis': {
                'showgrid': False,
                'zeroline': False,
                'visible': False,
            },
            'showlegend': False
        })
        # The use of `scale` to resize the image relies on the default image being 700x500, which seems to always
        # be the case with the activities I have tested.  Providing width and height arguments to write_image
        # results in the image just being a tiny blue dot.
        # TODO:  Find a way to explicitly specify the dimensions of the output image
        fig.write_image(fpath, format='png', scale=0.1)
        return fpath

    @staticmethod
    def from_gpx_file(fpath: str, config: Config, activity_id: int, activity_name: str = None,
                      activity_description: str = None, activity_type: str = 'run') -> 'Activity':
        points, metadata = parse_gpx_file(fpath)
        _distance_2d = points['cumul_distance_2d'].iloc[-1]
        center = points[['latitude', 'longitude', 'elevation']].mean()
        return Activity(
            config,
            points,
            activity_id=activity_id,
            activity_type=activity_type,
            date_time=metadata['time'],
            distance_2d=_distance_2d,
            center=center,
            data_file=fpath,
            name=activity_name or metadata['name'],
            description=activity_description or metadata['description']
        )
