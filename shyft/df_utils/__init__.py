"""Some useful functions for working with DataFrames that are used
multiple times in different places.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional, Union, List, Sequence

import pandas as pd

import typing
if typing.TYPE_CHECKING:
    from activity import ActivityMetaData

MILE = 1609.344  # metres in a mile
MILE_KM = MILE / 1000  # km in a mile


# Speed-related conversions.

def ms_to_kmph(meters_per_sec: Optional[Union[float, pd.Series]]) -> Optional[Union[float, pd.Series]]:
    """Converts meters/second to km/hour."""
    if meters_per_sec is not None:
        return meters_per_sec * 3.6
    else:
        return None


def speed_to_pace(speed: Union[float, pd.Series]) -> Union[timedelta, pd.Series]:
    """Convert speed (in kmph or mph) to pace (ie, seconds per km or mile)."""
    if isinstance(speed, pd.Series):
        return pd.to_timedelta(3600 / speed, unit='s')
    else:
        return timedelta(seconds=(3600 / speed))


def pace_to_speed(pace: Union[timedelta, pd.Series]) -> float:
    if isinstance(pace, pd.Series):
        sec = pace.dt.total_seconds()
    else:
        sec = pace.total_seconds()
    return 3600 / sec


def kmph_to_mph(kmph: Union[float, pd.Series]) -> Union[float, pd.Series]:
    return kmph / MILE_KM


def mph_to_kmph(mph: Union[float, pd.Series]) -> Union[float, pd.Series]:
    return mph * MILE_KM


# Functions to work out certain data about laps or splits.

def get_lap_durations(laps: pd.DataFrame, points: pd.DataFrame) -> pd.Series:
    """Get durations of laps (or splits)."""
    start_times = laps['start_time']
    return start_times - start_times.shift(-1, fill_value=points.iloc[-1]['time'])


def get_lap_distances(points: pd.DataFrame) -> pd.Series:
    """Get approximate lap distances."""
    first = points[['cumul_distance_2d', 'lap']].groupby('lap').first()
    return first - first.shift(-1, fill_value=points.iloc[-1]['cumul_distance_2d'])


def get_lap_means(cols: List[str], points: pd.DataFrame, groupby: str = 'lap') -> pd.DataFrame:
    """Get mean heart rate, cadence, km/hr and miles/hr for lap (or split)."""
    if groupby not in cols:
        cols.append(groupby)
    return points[cols].groupby(groupby).mean()

# Functions to work with ActivityMetaData objects.

def summarize_metadata(metadata: Sequence[ActivityMetaData]) -> pd.DataFrame:
    """Return a DataFrame each row of which summarises an
    ActivityMetaData object.
    """
    df = pd.DataFrame(vars(md) for md in metadata)
    # print(df.columns)
    df['center_lat'] = df['center'].str[0]
    df['center_lon'] = df['center'].str[1]
    df['center_elev'] = df['center'].str[2]
    return df