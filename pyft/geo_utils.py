"""Various helper functions for working with spatial data.

Some of these functions are based on the functions implemented in gpxpy,
but are vectorised.
"""
from typing import Union
from datetime import datetime

import pandas as pd
import numpy as np

# latitude/longitude in GPX files is always in WGS84 datum
# WGS84 defined the Earth semi-major axis with 6378.137 km
from fastdtw import fastdtw

EARTH_RADIUS = 6378.137 * 1000

# One degree in meters:
ONE_DEGREE = (2 * np.pi * EARTH_RADIUS) / 360  # ==> 111.319 km


def haversine_distance(latitude_1: np.ndarray, longitude_1: np.ndarray,
                       latitude_2: np.ndarray, longitude_2: np.ndarray) -> np.ndarray:
    """
    Haversine distance between two points, expressed in meters.
    Implemented from http://www.movable-type.co.uk/scripts/latlong.html
    """
    d_lon = np.radians(longitude_1 - longitude_2)
    lat1 = np.radians(latitude_1)
    lat2 = np.radians(latitude_2)
    d_lat = lat1 - lat2

    a = (np.sin(d_lat / 2) ** 2) + np.multiply(np.multiply((np.sin(d_lon / 2) ** 2), np.cos(lat1)), np.cos(lat2))
    c = 2 * np.arcsin(np.sqrt(a))
    d = EARTH_RADIUS * c

    return d


def naive_distance(latitude_1: np.ndarray, longitude_1: np.ndarray,
                   latitude_2: np.ndarray, longitude_2: np.ndarray) -> np.ndarray:
    coef = np.cos(np.radians(latitude_1))
    x = latitude_1 - latitude_2
    y = (longitude_1 - longitude_2) * coef

    distance_2d = np.sqrt(x * x + y * y) * ONE_DEGREE

    return distance_2d


def distance(latitude_1: Union[float, np.ndarray], longitude_1: Union[float, np.ndarray],
             latitude_2: Union[float, np.ndarray], longitude_2: Union[float, np.ndarray],
             haversine=True) -> np.ndarray:
    if haversine:
        return haversine_distance(latitude_1, longitude_1, latitude_2, longitude_2)
    else:
        return naive_distance(latitude_1, longitude_1, latitude_2, longitude_2)

def intersect_points(p1: pd.Series, p2: pd.Series, portion: float) -> pd.Series:
    """Returns a pd.Series representing a point that lies `portion`
    way between p1 and p2.
    `portion` should be a float between 0.0 and 1.0:
        if 0.0, the returned point will be the same as p0;
        if 1.0, the returned point will be the same as p1;
        otherwise, the returned point will be somewhere in between.
    Assumes the points have latitude, longitude, elevation and time
    columns (and the constructed point will have only these
    columns).
    """

    p3 = pd.Series(dtype=np.int64)
    for item in ('latitude', 'longitude', 'elevation'):
        p3[item] = ((1 - portion) * p1[item]) + (portion * p2[item])
    p3['time'] = datetime.fromtimestamp(
        ((1 - portion) * p1.time.timestamp()) + (portion * p2.time.timestamp()),
        p1.time.tzinfo
    )
    return p3


def norm_length_diff(len_1: float, len_2: float) -> float:
    """Return the difference between two lengths, normalised by mean."""
    return abs(len_1 - len_2) / ((len_1 + len_2) / 2)


def norm_center_diff(center_1: np.ndarray, center_2: np.ndarray, std_1: np.ndarray, std_2: np.ndarray) -> float:
    """Return the distance between two center points, normalised by the
    standard deviations of the series.
     """

    norm_center_1 = std_1
    norm_center_2 = std_2
    return float(distance(norm_center_1[0], norm_center_1[1], norm_center_2[0], norm_center_2[1]))


def norm_dtw(series_1: np.ndarray, series_2: np.ndarray) -> float:
    """Normalise two series and perform DTW.
    - z-normalisation to account for variance.
    - divide by average length to account for length.
    """
    series_1 = (series_1 - series_1.mean()) / series_1.std()
    series_2 = (series_2 - series_2.mean()) / series_2.std()
    return fastdtw(series_1, series_2, dist=2)[0] / ((len(series_1) + len(series_2)) / 2)
