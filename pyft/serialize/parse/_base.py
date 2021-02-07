"""Base classes for building parsers."""

from datetime import datetime
from typing import Optional, Union, List
import logging

import numpy as np
import pandas as pd

from pyft.config import Config
from pyft.geo_utils import haversine_distance
from pyft.serialize._activity_types import PYFT_TYPES

MILE = 1609.344  # metres in a mile


class PyftParserException(Exception): pass


class BaseParser:
    ACTIVITY_TYPES = PYFT_TYPES

    # The DataFrame that is passed to infer_points_data must contain all of these columns
    INITIAL_COL_NAMES_POINTS = (
        'point_no', 'track_no', 'segment_no',
        'latitude', 'longitude', 'elevation',
        'time', 'hr', 'cadence', 'lap', 'kmph'
    )

    INITIAL_COL_NAMES_LAPS = (
        'lap_no', 'start_time', 'distance', 'duration', 'calories'
    )

    def __init__(self, fpath: str, config: Config):
        logging.debug(f'Parsing {fpath} using {type(self).__name__}.')
        self.config = config
        self._parse(fpath)

    def _convert_speed(self, meters_per_sec: Optional[Union[float, pd.Series]]) -> Optional[Union[float, pd.Series]]:
        """Converts meters/second to km/hour."""
        if meters_per_sec is not None:
            return meters_per_sec * 3.6
        else:
            return None

    def _infer_points_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        prev_lat = df['latitude'].shift()
        prev_lon = df['longitude'].shift()
        df['step_length_2d'] = self.distance_2d(df['latitude'], df['longitude'], prev_lat, prev_lon)
        df['cumul_distance_2d'] = df['step_length_2d'].fillna(0).cumsum()
        df['km'] = (df['cumul_distance_2d'] // 1000).astype(int)
        df['mile'] = (df['cumul_distance_2d'] // MILE).astype(int)
        df['run_time'] = df['time'] - df.iloc[0]['time']
        logging.debug(f'Average step length (distance): {df["step_length_2d"].mean()}')
        # step_time = df['time'] - df['time'].shift()
        # logging.info(f'Average step length (time): {step_time.mean()}s')

        # Calculate speed / pace.
        # If we have speed from the device, calculate the other metrics from that.
        # Otherwise, calculate the metrics from the time and location data.
        prev_time = df['time'].shift(self.config.speed_measure_interval)
        prev_cumul_distance = df['cumul_distance_2d'].shift(self.config.speed_measure_interval)
        interval_distance = df['cumul_distance_2d'] - prev_cumul_distance
        interval_time = df['time'] - prev_time
        if df['kmph'].isnull().all():
            df['kmph'] = self._convert_speed(interval_distance / interval_time.dt.seconds)
        df['km_pace'] = (1000 / interval_distance) * interval_time
        df['mile_pace'] = (MILE / interval_distance) * interval_time
        df['mph'] = (1000 * df['kmph']) / MILE
        # df['km_pace'] = 3600 / df['kmph']
        # df['mile_pace'] = 3600 / df['mph']

        # df['kmph'] = (3600 / df['km_pace'].dt.total_seconds())
        # df['mph'] = df['kmph'] / (MILE / 1000)

        return df

    def _clean_points_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Do some basic cleaning of the points data."""
        df = df.copy()
        df.set_index('point_no', inplace=True)
        df.drop_duplicates('time', ignore_index=True, inplace=True)
        return df

    def _handle_points_data(self, df: pd.DataFrame) -> pd.DataFrame:
        if missing := set(self.INITIAL_COL_NAMES_POINTS).difference(df.columns):
            raise ValueError(f'DataFrame is missing the following columns: {missing}.')
        return self._infer_points_data(self._clean_points_data(df))

    def distance_2d(self, lat1: pd.Series, lon1: pd.Series, lat2: pd.Series, lon2: pd.Series) -> np.ndarray:
        return haversine_distance(lat1, lon1, lat2, lon2)

    def _parse(self, fpath: str):
        raise NotImplementedError('Child of BaseParser must implement a _parse method.')

    @property
    def points(self) -> pd.DataFrame:
        """Return a DataFrame with limited information on points (as
        described in INITIAL_COL_NAMES_POINTS). The infer_points_data can be
        called on the resulting DataFrame to generate more data.
        """
        raise NotImplementedError('Child of BaseParser must implement a points property.')

    @property
    def laps(self) -> Optional[pd.DataFrame]:
        """Return a DataFrame with limited information on laps (as
        described in INITIAL_COL_NAMES_LAPS), if available (or None
        otherwise).

        Return None by default.
        """
        return None

    @property
    def date_time(self) -> datetime:
        raise NotImplementedError('Child of BaseParser must implement a date_time property.')

    @property
    def metadata(self) -> dict:
        raise NotImplementedError('Child of BaseParser must implement a metadata property.')

    @property
    def activity_type(self) -> str:
        raise NotImplementedError('Child of BaseParser must implement an activity_type property.')


class BaseActivityParser(BaseParser):
    """A base class for parsers that parse files describing an activity
    (such as TCX and FIT files), rather than simply GPS data (such as
    GPX files). Contains additional methods for parsing and converting
    additional data generally not found in GPX files.
    """

    def __init__(self, *args, **kwargs):
        self._backfill = []
        self._lap = 1
        self._point = 0
        super().__init__(*args, **kwargs)

    def _get_lap_no(self) -> int:
        lap = self._lap
        self._lap += 1
        return lap

    def _get_point_no(self) -> int:
        point = self._point
        self._point += 1
        return point

    def _handle_backfill(self, point_data: dict, all_points_data: List[dict],
                         lat: Optional[float], lon: Optional[float]):
        # Sometimes, a file will report elevation without reporting lat/lon data. In this case, we store
        # whatever data we find, and once we subsequently receive lat/lon data we "backfill" the missing data with that.
        if (lat is None) or (lon is None):
            self._backfill.append(point_data)
        else:
            if self._backfill:
                for to_add in self._backfill:
                    for k in point_data:
                        if (to_add.get(k) is None) and (point_data[k] is not None):
                            to_add[k] = point_data[k]
                    all_points_data.append(to_add)
                self._backfill = []
            # if isinstance(self, TCXParser):
            #    print(f'adding {point_data["elevation"]}')
            all_points_data.append(point_data)
            # if isinstance(self, TCXParser):
            #    raise ValueError
