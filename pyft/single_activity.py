import os
import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Tuple, Callable, Optional, Any

import lxml.etree
import pandas as pd
import numpy as np
import pytz

import gpxpy
from pyft.config import Config
from pyft.geo_utils import intersect_points
from pyft.serialize.create import activity_to_gpx_file
from pyft.serialize.parse import parser_factory

MILE = 1609.344
pd.options.plotting.backend = "plotly"


@dataclass
class ActivityMetaData:
    """A dataclass representing a brief summary of an activity."""

    # NOTE:  ActivityMetaData can be created in one of two situations:
    #   1.  when an Activity is created from a GPX file (points-related data will be calculated from the
    #       DataFrame at that stage); or
    #   2.  when loaded from the database (points-related data should have been saved to the database previously).

    # NOTE:  Changes to the data stored in ActivityMetaData also need to be reflected in:
    # - DatabaseManager.ACTIVITIES;
    # - DatabaseManager.SAVE_ACTIVITY_DATA;
    # - DatabaseManager.save_activity_data;

    activity_id: int
    activity_type: str
    date_time: datetime
    name: Optional[str] = None
    description: Optional[str] = None
    data_file: Optional[str] = None
    source_file: Optional[str] = None

    # The following will be auto-generated when the associated Activity is instantiated, if not explicitly provided
    distance_2d_km: float = None
    center: np.ndarray = None
    points_std: np.ndarray = None
    km_pace_mean: timedelta = None
    duration: timedelta = None
    prototype_id: Optional[int] = None
    thumbnail_file: Optional[str] = None

    # The following will be auto-generated when ActivityMetaData is instantiated, if not explicitly provided
    kmph_mean: float = None
    distance_2d_mile: float = None
    mile_pace_mean: timedelta = None
    mph_mean: float = None
    day: str = None
    hour: int = None
    month: str = None


    def __post_init__(self):
        if self.distance_2d_mile is None:
            self.distance_2d_mile = self.distance_2d_km * 1000 / MILE
        if self.kmph_mean is None:
            self.kmph_mean = 3600 / self.km_pace_mean.seconds
        if self.mph_mean is None:
            self.mph_mean = self.kmph_mean / MILE
        if self.mile_pace_mean is None:
            self.mile_pace_mean = timedelta(seconds=60/self.mph_mean)
        if self.day is None:
            self.day = self.date_time.strftime('%A')
        if self.hour is None:
            self.hour = self.date_time.hour
        if self.month is None:
            self.month = self.date_time.strftime('%M')

@dataclass(init=False)
class Activity:
    """ A dataclass representing a single activity.  Stores the points (as a pd.DataFrame),
    as well as some metadata about the activity.  We only separately store data about
    the activity which cannot easily and quickly be deduced from the points.
    """

    metadata: ActivityMetaData
    points: pd.DataFrame

    def __init__(self, config: Config, points: pd.DataFrame, metadata: Optional[ActivityMetaData] = None, **kwargs):
        self.config = config
        self.points = points
        if metadata is not None:
            self.metadata = metadata
        else:
            if kwargs.get('distance_2d_km') is None:
                kwargs['distance_2d_km'] = self.points['cumul_distance_2d'].iloc[-1] / 1000
            if kwargs.get('center') is None:
                kwargs['center'] = self.points[['latitude', 'longitude', 'elevation']].mean().to_numpy()
            if kwargs.get('points_std') is None:
                kwargs['points_std'] = self.points[['latitude', 'longitude', 'elevation']].std().to_numpy()
            if kwargs.get('km_pace_mean') is None:
                kwargs['km_pace_mean'] = self.points['km_pace'].mean()
            if kwargs.get('duration') is None:
                kwargs['duration'] = self.points.iloc[-1]['time'] - kwargs['date_time']
            if (kwargs.get('thumbnail_file') is None) and config.thumbnail_dir:
                kwargs['thumbnail_file'] = self.write_thumbnail(activity_id=kwargs['activity_id'])
            if ((activity_id := kwargs.get('activity_id')) is not None) and (kwargs.get('data_file') is None):
                kwargs['data_file'] = os.path.join(config.gpx_file_dir, f'{activity_id}.gpx')

            self.metadata = ActivityMetaData(**kwargs)
            if (self.metadata.data_file is not None) and (not os.path.exists(self.metadata.data_file)):
                self.to_gpx_file(self.metadata.data_file)

    def get_split_markers(self, split_col: str) -> pd.DataFrame:
        """Takes a DataFrame, calculates the points that lie directly on
        the boundaries between splits and returns those points as a
        DataFrame.
        """
        if split_col == 'km':
            split_len = 1000
        elif split_col == 'mile':
            split_len = MILE
        else:
            raise ValueError(f'split_col must be "km" or "mile", not "{split_col}".')
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
            m = intersect_points(p1, p2, portion)
            m['ends'] = i - 1
            m['begins'] = i
            markers.append(m)
        return pd.DataFrame(markers)

    @property
    def km_markers(self) -> pd.DataFrame:
        return self.get_split_markers('km')

    @property
    def mile_markers(self) -> pd.DataFrame:
        return self.get_split_markers('mile')

    def get_split_summary(self, split_col: str) -> pd.DataFrame:
        if split_col == 'km':
            pace_col = 'km_pace'
        elif split_col == 'mile':
            pace_col = 'mile_pace'
        else:
            raise ValueError(f'split_col must be "km" or "mile", not "{split_col}".')
        splits = self.points[[split_col, pace_col, 'time', 'cadence', 'hr', 'elevation']]
        grouped = splits.groupby(split_col)
        summary = grouped.mean()
        split_times = self.get_split_markers(split_col)['time']
        summary['time'] = split_times - split_times.shift(fill_value=self.points.iloc[0]['time'])
        summary.loc[summary.index[-1], 'time'] = self.points.iloc[-1]['time'] - split_times.iloc[-1]
        return summary

    @property
    def km_summary(self):
        return self.get_split_summary('km')

    @property
    def mile_summary(self):
        return self.get_split_summary('mile')

    def write_thumbnail(self, fpath: Optional[str] = None, activity_id: int = None) -> str:
        """Create a thumbnail representing the route and write it to
        fpath (determined by the config if not explicitly provided.
        Returns the path to which the image was saved.
        """
        # TODO:  Would be better not to rely on plotly / kaleido for this;
        # maybe roll our own using pillow.
        if activity_id is None:
            activity_id = self.metadata.activity_id

        if fpath is None:
            fpath = os.path.join(self.config.thumbnail_dir, f'{activity_id}.png')

        fpath = os.path.abspath(fpath)

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
        #print(f'thumbnail fpath is {fpath}')
        return fpath

    @property
    def activity_hash(self):
        """Generate a unique (enough) hash for the Activity by hashing the combination of the ActivityMetaData
        variables and the shape (rows and cols) of the points.
        """
        # TODO:  Check if this is used
        return hashlib.sha1(json.dumps(vars(self.metadata)).encode('utf-8') + bytes(self.points.shape)).hexdigest()

    @staticmethod
    def from_file(fpath: str, config: Config, activity_id: int, activity_name: str = None,
                  activity_description: str = None, activity_type: str = None) -> 'Activity':
        fname, ext = os.path.splitext(fpath)
        parser = parser_factory(fpath, config)
        source_file = os.path.join(config.source_file_dir, f'{activity_id}{ext}')
        if not os.path.exists(source_file):
            shutil.copyfile(fpath, source_file)
        return Activity(
            config,
            parser.points,
            activity_id=activity_id,
            activity_type=activity_type or parser.metadata['activity_type'],
            date_time=parser.metadata['date_time'],
            source_file=source_file,
            name=activity_name or parser.metadata['name'],
            description=activity_description or parser.metadata['description']
        )



    def to_gpx_file(self, fpath: str):
        activity_to_gpx_file(self, fpath)
