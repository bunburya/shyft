"""Configuration.  Just a shell for testing at the moment.

TODO:  Implement proper configuration using ConfigParser.
"""
import json
import os
import configparser
from typing import Any, Dict, Optional

import appdirs


class Config:

    def __init__(self, ini_fpath: str, activity_graphs_fpath: Optional[str] = None, **kwargs):
        parser = configparser.ConfigParser()
        parser.read(ini_fpath)
        if parser['general']['data_dir'] is None:
            self.data_dir = appdirs.user_data_dir(appname='pyft')
        else:
            self.data_dir = parser['general']['data_dir']

        self.user_name = parser['general']['user_name']

        self.distance_unit = parser['general']['distance_unit']

        self.match_center_threshold = parser['general'].getfloat('match_center_threshold')
        self.match_length_threshold = parser['general'].getfloat('match_length_threshold')
        self.tight_match_threshold = parser['general'].getfloat('tight_match_threshold')

        self.default_activity_name_format = parser['general']['default_activity_name_format']

        for k in kwargs:
            setattr(self, k, kwargs[k])

        self.thumbnail_dir = os.path.join(self.data_dir, 'thumbnails')
        self.gpx_file_dir = os.path.join(self.data_dir, 'gpx_files')
        self.db_file = os.path.join(self.data_dir, 'pyft.db')

        for _dir in (self.data_dir, self.thumbnail_dir, self.gpx_file_dir):
            if not os.path.exists(_dir):
                os.makedirs(_dir)

        if activity_graphs_fpath is not None:
            with open(activity_graphs_fpath) as f:
                self.activity_graphs = json.load(f)
        else:
            self.activity_graphs = []
        #print(self.activity_graphs)
