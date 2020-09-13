"""Configuration.  Just a shell for testing at the moment.

TODO:  Implement proper configuration using ConfigParser.
"""
import os
from dataclasses import dataclass


@dataclass
class Config:

    db_file: str = None
    thumbnail_dir: str = None
    gpx_file_dir: str = None

    # Thresholds for loose matching
    match_center_threshold: float = 10000
    match_length_threshold: float = 0.01

    # Threshold for tight matching
    tight_match_threshold: float = 0.1

    def __post_init__(self):
        # TODO:  Create sane defaults for files
        pass
