import os
from time import time

import numpy as np
import pandas as pd
from pyft.config import Config
from pyft.geo_utils import norm_length_diff, norm_center_diff, norm_dtw
from pyft.activity_manager import ActivityManager
from pyft.activity import Activity
from test.test_common import *

TEST_RUN_DATA_DIR = run_data_dir('threshold', replace=True)
TEST_CONFIG_FILE = config_file(TEST_RUN_DATA_DIR)

def main():

    # TODO: Change so that all activities are added to the manager, and then iterate through _activity_elem IDs.

    config = Config(TEST_CONFIG_FILE)
    am = ActivityManager(config)
    length_df = pd.DataFrame(np.zeros((len(TEST_GPX_FILES), len(TEST_GPX_FILES))))
    length_t_df = pd.DataFrame(np.zeros((len(TEST_GPX_FILES), len(TEST_GPX_FILES))))
    center_df = pd.DataFrame(np.zeros((len(TEST_GPX_FILES), len(TEST_GPX_FILES))))
    center_t_df = pd.DataFrame(np.zeros((len(TEST_GPX_FILES), len(TEST_GPX_FILES))))
    dtw_df = pd.DataFrame(np.zeros((len(TEST_GPX_FILES), len(TEST_GPX_FILES))))
    dtw_t_df = pd.DataFrame(np.zeros((len(TEST_GPX_FILES), len(TEST_GPX_FILES))))
    for i, fpath1 in enumerate(TEST_GPX_FILES):
        for j, fpath2 in enumerate(TEST_GPX_FILES):
            id1 = Activity.from_file(fpath1)
            a2 = Activity.from_file(fpath2)
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
