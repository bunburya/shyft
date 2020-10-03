import os
from time import time

import numpy as np
import pandas as pd
from pyft.geo_utils import norm_length_diff, norm_center_diff, norm_dtw
from pyft.single_activity import Activity

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')

# Test GPX files.
# Neither 0 nor 1 should loose- or tight-match any other activity.
# 2 and 3 should loose- and tight-match each other but not match any others.
# 4 and 5 should loose- but not tight-match each other.
# TBC if 6 should match 4 or 5.
TEST_GPX_FILES = [
    os.path.join(TEST_DATA_DIR, 'GNR_2019.gpx'),                                # 0
    os.path.join(TEST_DATA_DIR, 'Morning_Run_Miami.gpx'),                       # 1
    os.path.join(TEST_DATA_DIR, '2020_08_05_pp_9k_ccw.gpx'),         # 2
    os.path.join(TEST_DATA_DIR, '2020_08_04_pp_9k_ccw.gpx'),       # 3
    os.path.join(TEST_DATA_DIR, '2020_03_20_pp_7.22k_cw.gpx'),           # 4
    os.path.join(TEST_DATA_DIR, '2020_06_18_pp_7.23k_ccw.gpx'),    # 5
    os.path.join(TEST_DATA_DIR, '2019_07_08_pp_7k_ccw.gpx'),         # 6
]

# ints here are index values in TEST_GPX_FILES
LOOSE_MATCH = (
    (2, 3),
    (4, 5)
)

TIGHT_MATCH = (
    (2, 3),
)

UNIQUE = (0, 1)

def main():
    length_df = pd.DataFrame(np.zeros((len(TEST_GPX_FILES), len(TEST_GPX_FILES))))
    length_t_df = pd.DataFrame(np.zeros((len(TEST_GPX_FILES), len(TEST_GPX_FILES))))
    center_df = pd.DataFrame(np.zeros((len(TEST_GPX_FILES), len(TEST_GPX_FILES))))
    center_t_df = pd.DataFrame(np.zeros((len(TEST_GPX_FILES), len(TEST_GPX_FILES))))
    dtw_df = pd.DataFrame(np.zeros((len(TEST_GPX_FILES), len(TEST_GPX_FILES))))
    dtw_t_df = pd.DataFrame(np.zeros((len(TEST_GPX_FILES), len(TEST_GPX_FILES))))
    for i, fpath1 in enumerate(TEST_GPX_FILES):
        for j, fpath2 in enumerate(TEST_GPX_FILES):
            a1 = Activity.from_gpx_file(fpath1)
            a2 = Activity.from_gpx_file(fpath2)
            t = time()
            length_df[i][j] = norm_length_diff(a1.metadata.distance_2d_km, a2.metadata.distance_2d_km)
            length_t_df[i][j] = time() - t
            t = time()
            length_df[j][i] = norm_length_diff(a2.metadata.distance_2d_km, a1.metadata.distance_2d_km)
            length_t_df[j][i] = time() - t
            lat2, lon2, _ = a2.metadata.center
            t = time()
            center_df[i][j] = norm_center_diff(a1.metadata.center, a2.metadata.center,
                                               a1.metadata.points_std, a2.metadata.points_std)
            center_t_df[i][j] = time() - t
            t = time()
            center_df[j][i] = norm_center_diff(a2.metadata.center, a1.metadata.center,
                                               a2.metadata.points_std, a1.metadata.points_std)
            center_t_df[j][i] = time() - t
            t = time()
            dtw_df[i][j] = norm_dtw(a1.points[['latitude', 'longitude']], a2.points[['latitude', 'longitude']])
            dtw_t_df[i][j] = time() - t
            t = time()
            dtw_df[j][i] = norm_dtw(a2.points[['latitude', 'longitude']], a1.points[['latitude', 'longitude']])
            dtw_t_df[j][i] = time() - t

    print('DIFFERENCES')
    print('LENGTH:')
    print(length_df)
    print('CENTER:')
    print(center_df)
    print('DTW:')
    print(dtw_df)
    print('TIMES')
    print('LENGTH:')
    print(length_t_df)
    print('CENTER:')
    print(center_t_df)
    print('DTW:')
    print(dtw_t_df)

if __name__ == '__main__':
    main()
