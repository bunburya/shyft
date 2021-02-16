import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import numpy as np

from shyft.config import Config
from shyft.geo_utils import intersect_points
from shyft.helper_funcs import MILE_KM, kmph_to_mph, speed_to_pace
from shyft.serialize.create.gpx import activity_to_gpx_file
from shyft.serialize.create.tcx import activity_to_tcx_file
from shyft.serialize.parse import parser_factory

MILE = 1609.344
pd.options.plotting.backend = "plotly"


@dataclass
class ActivityMetaData:
    """A dataclass representing a brief summary of an _activity_elem."""

    # NOTE:  ActivityMetaData can be created in one of two situations:
    #   1.  when an Activity is created from a GPX file (points-related data will be calculated from the
    #       DataFrame at that stage); or
    #   2.  when loaded from the database (points-related data should have been saved to the database previously).

    # NOTE:  Changes to the data stored in ActivityMetaData also need to be reflected in:
    # - DatabaseManager.ACTIVITIES;
    # - DatabaseManager.SAVE_ACTIVITY_DATA;
    # - DatabaseManager.save_activity_data;

    config: Config
    activity_id: int
    date_time: datetime
    activity_type: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    gpx_file: Optional[str] = None
    tcx_file: Optional[str] = None
    source_file: Optional[str] = None
    source_format: Optional[str] = None  # The format of the source file (ie, TCX, GPX or FIT).

    # The following will be auto-generated when the associated Activity is instantiated, if not explicitly provided
    # (because they rely on points data)
    distance_2d_km: float = None
    center: np.ndarray = None
    points_std: np.ndarray = None
    duration: timedelta = None
    prototype_id: Optional[int] = None
    thumbnail_file: Optional[str] = None

    # The following will be auto-generated when ActivityMetaData is instantiated, if not explicitly provided
    distance_2d_mile: float = None
    mean_kmph: float = None
    mean_km_pace: timedelta = None
    mean_mile_pace: timedelta = None
    mean_mph: float = None
    day: str = None
    hour: int = None
    month: str = None
    mean_hr: Optional[float] = None
    mean_cadence: Optional[float] = None
    calories: Optional[float] = None

    def __post_init__(self):

        if self.distance_2d_mile is None:
            self.distance_2d_mile = self.distance_2d_km / MILE_KM

        # Calculate various speed-related metrics
        if self.mean_kmph is None:
            self.mean_kmph = self.distance_2d_km / (self.duration.total_seconds() / 3600)
        if self.mean_km_pace is None:
            self.mean_km_pace = speed_to_pace(self.mean_kmph)
        if self.mean_mph is None:
            self.mean_mph = kmph_to_mph(self.mean_kmph)
        if self.mean_mile_pace is None:
            self.mean_mile_pace = speed_to_pace(self.mean_mph)

        # Date and time of the activity
        if self.day is None:
            self.day = self.date_time.strftime('%A')
        if self.hour is None:
            self.hour = self.date_time.hour
        if self.month is None:
            self.month = self.date_time.strftime('%M')

        # File locations for export
        if self.gpx_file is None:
            # Note: gpx_file is where the GPX file generated by Pyft *should* be; it still needs to be created,
            # and this should be done in Activity.__init__
            self.gpx_file = os.path.join(self.config.gpx_file_dir, f'{self.file_name}.gpx')
        if self.tcx_file is None:
            self.tcx_file = os.path.join(self.config.tcx_file_dir, f'{self.file_name}.tcx')

        if self.activity_type is None:
            self.activity_type = self.config.default_activity_type

    @property
    def name_or_default(self) -> str:
        """Returns either the activity's name, if set, or the default
        name based on the format specified in the config.
        """

        if self.name is not None:
            return self.name
        else:
            return self.default_name

    @property
    def default_name(self) -> str:
        """The 'default' name of the activity, determined according to
        the default format specified in the config.
        """
        return self.config.default_activity_name_format.format(**vars(self))

    @property
    def file_name(self) -> str:
        """A name to be used as a base for the name of data files describing the Activity."""
        # TODO: Move this to config to allow it to be specified by the user.
        return '_'.join(map(str, (
            self.activity_id,
            self.activity_type,
            f'{self.distance_2d_km:.2f}km',
            self.date_time.strftime('%Y-%m-%d_%H-%M')
        )))


@dataclass(init=False)
class Activity:
    """ A dataclass representing a single Activity.  Stores the points (as a pd.DataFrame),
    as well as some metadata about the Activity.  We only separately store data about
    the Activity which cannot easily and quickly be deduced from the points.
    """

    metadata: ActivityMetaData
    points: pd.DataFrame
    laps: Optional[pd.DataFrame] = None

    def __init__(self, config: Config, points: pd.DataFrame, laps: Optional[pd.DataFrame] = None,
                 metadata: Optional[ActivityMetaData] = None, **kwargs):
        self.config = config
        self.points = points
        self.laps = laps
        if metadata is not None:
            self.metadata = metadata
        else:
            if kwargs.get('distance_2d_km') is None:
                kwargs['distance_2d_km'] = self.points['cumul_distance_2d'].iloc[-1] / 1000
            if kwargs.get('center') is None:
                kwargs['center'] = self.points[['latitude', 'longitude', 'elevation']].mean().to_numpy()
            if kwargs.get('points_std') is None:
                kwargs['points_std'] = self.points[['latitude', 'longitude', 'elevation']].std().to_numpy()
            if kwargs.get('duration') is None:
                kwargs['duration'] = self.points.iloc[-1]['time'] - kwargs['date_time']
            if (kwargs.get('thumbnail_file') is None) and config.thumbnail_dir:
                kwargs['thumbnail_file'] = self.write_thumbnail(activity_id=kwargs['activity_id'])

            self.metadata = ActivityMetaData(config, **kwargs)

            if (self.metadata.gpx_file is not None) and (not os.path.exists(self.metadata.gpx_file)):
                self.to_gpx_file(self.metadata.gpx_file)
            if (self.metadata.tcx_file is not None) and (not os.path.exists(self.metadata.tcx_file)):
                self.to_tcx_file(self.metadata.tcx_file)

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
        """Returns a DataFrame with certain summary information about the
        splits (km or mile).
        """
        # TODO: Use functions in df_utils.helper_funcs for this.
        speed_col = self.get_speed_col(split_col)
        splits = self.points[[split_col, speed_col, 'cadence', 'hr']]
        split_no = splits[split_col] + 1
        splits.set_index(split_no)
        # groupby drops any null columns, so preserve and re-add these
        null_cols = list(filter(lambda c: splits[c].isnull().all(), splits.columns))
        summary = splits.groupby(split_col).mean()
        for col in null_cols:
            summary[col] = None
        # split_time = point in time at which split ended/began, not duration of split
        split_times = self.get_split_markers(split_col)['time']
        start_times = [self.metadata.date_time]
        start_times.extend(split_times)
        summary['start_time'] = pd.Series(start_times)
        summary['duration'] = split_times - split_times.shift(fill_value=self.points.iloc[0]['time'])
        summary.loc[summary.index[-1], 'duration'] = self.points.iloc[-1]['time'] - split_times.iloc[-1]
        #summary['duration'] = get_lap_durations(summary, self.points)
        if split_col == 'km':
            summary['distance'] = 1000
        elif split_col == 'mile':
            summary['distance'] = MILE
        return summary.rename(columns={
            'cadence': 'mean_cadence',
            'hr': 'mean_hr',
            speed_col: f'mean_{speed_col}'
        })

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

    def get_speed_col(self, distance_unit: str) -> str:
        if distance_unit == 'km':
            return 'kmph'
        elif distance_unit == 'mile':
            return 'mph'
        else:
            raise ValueError(f'distance_unit must be "km" or "mile", not "{distance_unit}".')

    @staticmethod
    def from_file(fpath: str, config: Config, activity_id: int, activity_name: str = None,
                  activity_description: str = None, activity_type: str = None) -> 'Activity':
        fname, ext = os.path.splitext(fpath)
        parser = parser_factory(fpath, config)

        metadata = parser.metadata
        if activity_type is not None:
            metadata['activity_type'] = activity_type
        if activity_name is not None:
            metadata['activity_name'] = activity_name
        if activity_description is not None:
            metadata['description'] = activity_description

        activity = Activity(
            config,
            parser.points,
            parser.laps,
            activity_id=activity_id,
            **metadata
        )
        source_file = os.path.join(config.source_file_dir, f'{activity.metadata.file_name}{ext}')
        if not os.path.exists(source_file):
            shutil.copyfile(fpath, source_file)
        activity.metadata.source_file = source_file
        return activity

    def to_gpx_file(self, fpath: str):
        activity_to_gpx_file(self, fpath)

    def to_tcx_file(self, fpath: str):
        activity_to_tcx_file(self, fpath)