"""Configuration.  Just a shell for testing at the moment.

TODO:  Implement proper configuration using ConfigParser.
"""
import getpass
import json
import os
import sys
from configparser import ConfigParser, Interpolation, BasicInterpolation
from dataclasses import dataclass
from typing import Any, Dict, Optional

import appdirs
from metadata import APP_NAME

DAYS_OF_WEEK = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']


@dataclass(init=False)
class Config:
    # Add these as fields so that they are compared in __eq__
    data_dir: str
    user_name: str
    distance_unit: str
    default_activity_type: str
    match_center_threshold: float
    match_length_threshold: float
    tight_match_threshold: float
    default_activity_name_format: str
    week_start: str
    speed_measure_interval: int
    overview_activities_count: int

    def __init__(self, ini_fpath: str,
                 activity_graphs_fpath: Optional[str] = None,
                 overview_graphs_fpath: Optional[str] = None,
                 interpolation: Optional[Interpolation] = BasicInterpolation(),
                 **kwargs):

        self.interpolation = interpolation

        self.ini_fpath = ini_fpath
        self.activity_graphs_fpath = activity_graphs_fpath
        self.overview_graphs_fpath = overview_graphs_fpath
        self.user_docs_dir = appdirs.user_data_dir(APP_NAME)
        self.kwargs = kwargs

        self.load()

    def read_file(self, ini_fpath: str):
        parser = ConfigParser(interpolation=self.interpolation)
        self.raw_config = ConfigParser(interpolation=None)
        parser.read(ini_fpath)
        self.raw_config.read(ini_fpath)

        if not parser['general']['user_name']:
            self.user_name = getpass.getuser()
        else:
            self.user_name = parser['general']['user_name']

        if not parser['general']['data_dir']:
            self.data_dir = appdirs.user_data_dir(appname='shyft')
        else:
            self.data_dir = parser['general']['data_dir']

        self.distance_unit = parser['general']['distance_unit']
        self.default_activity_type = parser['general']['default_activity_type']

        self.match_center_threshold = parser['general'].getfloat('match_center_threshold')
        self.match_length_threshold = parser['general'].getfloat('match_length_threshold')
        self.tight_match_threshold = parser['general'].getfloat('tight_match_threshold')

        self.default_activity_name_format = parser['general']['default_activity_name_format']
        self.week_start = parser['general']['week_start'].capitalize()
        self.speed_measure_interval = parser['general'].getint('speed_measure_interval')

        self.overview_activities_count = parser['general'].getint('overview_activities_count')
        self.matched_activities_count = parser['general'].getint('matched_activities_count')

    def load(self, fpath: Optional[str] = None):
        """Load values from the given files and keyword arguments."""

        fpath = fpath or self.ini_fpath
        self.read_file(fpath)

        for k in self.kwargs:
            setattr(self, k, self.kwargs[k])

        for _dir in (self.data_dir, self.thumbnail_dir, self.gpx_file_dir, self.tcx_file_dir, self.source_file_dir):
            if not os.path.exists(_dir):
                os.makedirs(_dir)

        if self.activity_graphs_fpath is not None:
            try:
                with open(self.activity_graphs_fpath) as f:
                    self.activity_graphs = json.load(f)
            except (FileNotFoundError, json.decoder.JSONDecodeError):
                self.activity_graphs = []
        else:
            self.activity_graphs = []

        if self.overview_graphs_fpath is not None:
            try:
                with open(self.overview_graphs_fpath) as f:
                    self.overview_graphs = json.load(f)
            except (FileNotFoundError, json.decoder.JSONDecodeError):
                self.overview_graphs = []
        else:
            self.overview_graphs = []

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
        self.tcx_file_dir = os.path.join(new, 'tcx_files')
        self.source_file_dir = os.path.join(new, 'source_files')
        self.tmp_dir = os.path.join(new, 'tmp')
        self.db_file = os.path.join(new, 'shyft.db')
        self.log_file = os.path.join(new, 'shyft.log')


        for _dir in (self.data_dir, self.thumbnail_dir, self.gpx_file_dir, self.tcx_file_dir, self.source_file_dir,
                     self.tmp_dir):
            if not os.path.exists(_dir):
                os.makedirs(_dir)

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

    def to_configparser(self, generate_raw: bool = False) -> ConfigParser:
        """Save the current configuration options to a ConfigParser
        object and return it.

        If generate_raw is True, use a new Config instance using the raw()
        method, which will have raw (uninterpolated) versions of the values
        that this instance was initialised with (NOT necessarily its current
        values).
        """

        if generate_raw:
            to_save = self.raw()
        else:
            to_save = self

        parser = ConfigParser(interpolation=None)
        parser.add_section('general')
        for _field in to_save.__dataclass_fields__:
            parser['general'][_field] = str(getattr(to_save, _field))
        return parser

    def to_file(self, fpath: Optional[str] = None, generate_raw: bool = False):
        """Save the current configuration options to `fpath` as a .ini
        file. If `fpath` is not provided, print to stdout.
        """

        parser = self.to_configparser(generate_raw=generate_raw)

        if fpath:
            with open(fpath, 'w') as f:
                parser.write(f)
        else:
            parser.write(sys.stdout)

    def raw(self) -> 'Config':
        """Return a new Config object initialised with the same values as this
        instance, but with no interpolation. It is this raw version that should
        generally be used when loading and saving configuration settings.
        """
        return Config(self.ini_fpath, self.activity_graphs_fpath, self.overview_graphs_fpath, interpolation=None,
                      **self.kwargs)
