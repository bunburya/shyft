# WIP, and probably won't come to anything unless we find a good way to handle points.

from pyft.parse_gpx import parse_gpx_file
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.ext.declarative import declarative_base

import pandas as pd

Base = declarative_base()


class Activity(Base):
    __tablename__ = 'activities'

    id = Column(Integer, primary_key=True)
    activity_type = Column(String, nullable=False)
    date_time = Column(DateTime, nullable=False)
    distance_2d = Column(Float, nullable=False)
    center_lat = Column(Float, nullable=False)
    center_lon = Column(Float, nullable=False)
    center_elev = Column(Float)
    matched_prototype = Column(Integer, ForeignKey('prototypes.id'))
    activity_name = Column(String)
    description = Column(String)
    data_file = Column(String)

class Prototype(Base):
    __tablename__ = 'prototypes'

    activity_id = Column(Integer, ForeignKey('activities.activity_type'), primary_key=True)


class Point(Base):

    __tablename__ = 'points'
    POINTS = """CREATE TABLE IF NOT EXISTS \"points\" (
            id INTEGER NOT NULL,
            activity_id INTEGER NOT NULL,
            point_no INTEGER,
            track_no INTEGER,
            segment_no INTEGER,
            latitude FLOAT NOT NULL,
            longitude FLOAT NOT NULL,
            elevation FLOAT,
            time TIMESTAMP NOT NULL,
            hr INTEGER,
            cadence INTEGER,
            step_length_2d FLOAT,
            cumul_distance_2d FLOAT,
            km INTEGER,
            km_pace FLOAT,
            FOREIGN KEY(activity_id) REFERENCES activities(id),
            PRIMARY KEY(id, activity_id)
        )"""
    id = Column(Integer, nullable=False)
    activity_id = Column(Integer, ForeignKey('activities.id'), nullable=False)
    point_no = Column(Integer)
    track_no = Column(Integer)
    segment_no = Column(Integer)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation = Column(Float)
    time = Column(DateTime, nullable=False)
    hr = Column(Integer)
    cadence = Column(Integer)
    step_length_2d = Column(Float)
    cumul_distance_2d = Column(Float)
    km = Column(Integer)
    km_pace = Column(Float)

    __table_args__ = (
        PrimaryKeyConstraint(id, activity_id)
    )

class ActivityManager:

    def add_activity_from_gpx_file(self, fpath: str):
        parse_gpx_file()

