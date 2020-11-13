"""Configuration.  Just a shell for testing at the moment.

TODO:  Implement proper configuration using ConfigParser.
"""
import json
import os
import configparser
from dataclasses import dataclass
from typing import Any, Dict, Optional

import appdirs

DAYS_OF_WEEK = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']


@dataclass(init=False)
class Config:

    # Add these as fields so that they are compared in __eq__
    data_dir: str
    user_name: str
    distance_unit: str
    match_center_threshold: float
    match_length_threshold: float
    tight_match_threshold: float
    default_activity_name_format: str
    week_start: str


    def __init__(self, ini_fpath: str,
                 activity_graphs_fpath: Optional[str] = None,
                 overview_graphs_fpath: Optional[str] = None,
                 **kwargs):
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
        self.week_start = parser['general']['week_start'].capitalize()

        for k in kwargs:
            setattr(self, k, kwargs[k])

        for _dir in (self.data_dir, self.thumbnail_dir, self.gpx_file_dir):
            if not os.path.exists(_dir):
                os.makedirs(_dir)

        if activity_graphs_fpath is not None:
            try:
                with open(activity_graphs_fpath) as f:
                    self.activity_graphs = json.load(f)
            except (FileNotFoundError, json.decoder.JSONDecodeError):
                self.activity_graphs = []
        else:
            self.activity_graphs = []

        if overview_graphs_fpath is not None:
            try:
                with open(overview_graphs_fpath) as f:
                    self.overview_graphs = json.load(f)
            except (FileNotFoundError, json.decoder.JSONDecodeError):
                self.overview_graphs = []
        else:
            self.overview_graphs = []

        # print(self.activity_graphs)

    @property
    def data_dir(self) -> str:
        try:
            return self._data_dir
        except AttributeError:
            return ''

    @data_dir.setter
    def data_dir(self, new):
        self._data_dir = new
        self.thumbnail_dir = os.path.join(new, 'thumbnails')
        self.gpx_file_dir = os.path.join(new, 'gpx_files')
        self.db_file = os.path.join(new, 'pyft.db')

    @property
    def week_start(self) -> str:
        try:
            return self._week_start
        except AttributeError:
            return ''

    @week_start.setter
    def week_start(self, new):
        self._week_start = new
        week_start_i = DAYS_OF_WEEK.index(new)
        self.days_of_week = DAYS_OF_WEEK[week_start_i:] + DAYS_OF_WEEK[:week_start_i]

    def to_file(self, fpath):
        """Save the current configuration options to `fpath` as a .ini file."""

        parser = configparser.ConfigParser()
        parser.add_section('general')
        for _field in self.__dataclass_fields__:
            parser['general'][_field] = str(getattr(self, _field))
        with open(fpath, 'w') as f:
            parser.write(f)
