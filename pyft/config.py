"""Configuration.  Just a shell for testing at the moment.

TODO:  Implement proper configuration using ConfigParser.
"""
import os
from dataclasses import dataclass

import appdirs


@dataclass
class Config:

    data_dir: str = appdirs.user_data_dir(appname='pyft')
    db_file: str = None
    thumbnail_dir: str = None
    gpx_file_dir: str = None

    # Size of thumbnail images in px (width, height)
    # Not currently implemented, until we find a way to properly scale thumbnail images to custom sizes
    #thumbnail_size = (70, 50)

    # Thresholds for loose matching
    match_center_threshold: float = 10000
    match_length_threshold: float = 0.01

    # Threshold for tight matching
    tight_match_threshold: float = 0.1

    def __post_init__(self):
        # TODO:  Create sane defaults for files
        if not self.db_file:
            self.db_file = os.path.join(self.data_dir, 'pyft.db')
        if not self.thumbnail_dir:
            self.thumbnail_dir = os.path.join(self.data_dir, 'thumbnails')
        if not self.gpx_file_dir:
            self.gpx_file_dir = os.path.join(self.data_dir, 'gpx_files')
        for fpath in (self.data_dir, self.thumbnail_dir, self.gpx_file_dir):
            if not os.path.exists(fpath):
                os.makedirs(fpath)
