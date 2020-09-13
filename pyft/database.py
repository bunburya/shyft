import re
from datetime import timezone, timedelta, datetime
from typing import Any, Iterable

import pyft.config
import sqlite3 as sql

import pandas as pd
import pytz

# The below code is taken from Django's codebase (with some minor
# adjustments) and is intended to address the fact that sqlite3
# cannot handle timezone-aware timestamps:
# https://stackoverflow.com/questions/48614488/python-sqlite-valueerror-invalid-literal-for-int-with-base-10-b5911

datetime_re = re.compile(
    r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})'
    r'[T ](?P<hour>\d{1,2}):(?P<minute>\d{1,2})'
    r'(?::(?P<second>\d{1,2})(?:[\.,](?P<microsecond>\d{1,6})\d{0,6})?)?'
    r'(?P<tzinfo>Z|[+-]\d{2}(?::?\d{2})?)?$'
)


def get_fixed_timezone(offset):
    """Return a tzinfo instance with a fixed offset from UTC."""
    if isinstance(offset, timedelta):
        offset = offset.total_seconds() // 60
    sign = '-' if offset < 0 else '+'
    hhmm = '%02d%02d' % divmod(abs(offset), 60)
    name = sign + hhmm
    return timezone(timedelta(minutes=offset), name)


def parse_datetime(value):
    """Parse a string and return a datetime.datetime.
    This function supports time zone offsets. When the input contains one,
    the output uses a timezone with a fixed offset from UTC.
    Raise ValueError if the input is well formatted but not a valid datetime.
    Return None if the input isn't well formatted.
    """
    value = value.decode()
    match = datetime_re.match(value)
    if match:
        kw = match.groupdict()
        kw['microsecond'] = kw['microsecond'] and kw['microsecond'].ljust(6, '0')
        tzinfo = kw.pop('tzinfo')
        if tzinfo == 'Z':
            tzinfo = pytz.utc
        elif tzinfo is not None:
            offset_mins = int(tzinfo[-2:]) if len(tzinfo) > 3 else 0
            offset = 60 * int(tzinfo[1:3]) + offset_mins
            if tzinfo[0] == '-':
                offset = -offset
            tzinfo = get_fixed_timezone(offset)
        kw = {k: int(v) for k, v in kw.items() if v is not None}
        kw['tzinfo'] = tzinfo
        return datetime(**kw)


sql.dbapi2.register_converter("datetime", parse_datetime)
sql.dbapi2.register_converter("timestamp", parse_datetime)


class DatabaseManager:
    ACTIVITIES = """CREATE TABLE IF NOT EXISTS \"activities\" (
        id INTEGER PRIMARY KEY,
        type TEXT NOT NULL,
        date_time TIMESTAMP NOT NULL,
        distance_2d FLOAT NOT NULL,
        center_lat FLOAT NOT NULL,
        center_lon FLOAT NOT NULL,
        center_elev FLOAT,
        std_lat FLOAT,
        std_lon FLOAT,
        std_elev FLOAT,
        prototype_id INTEGER,
        name TEXT,
        description TEXT,
        data_file TEXT,
        FOREIGN KEY(prototype_id) REFERENCES prototypes(id)
    )"""

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
        mile INTEGER,
        km_pace FLOAT,
        mile_pace FLOAT,
        FOREIGN KEY(activity_id) REFERENCES activities(id),
        PRIMARY KEY(id, activity_id)
    )"""

    PROTOTYPES = """CREATE TABLE IF NOT EXISTS \"prototypes\" (
        activity_id INTEGER PRIMARY KEY,
        FOREIGN KEY(activity_id) REFERENCES activities(id)
    )"""

    SAVE_ACTIVITY_DATA = """INSERT OR REPLACE INTO \"activities\"
        (id, type, date_time, distance_2d, center_lat, center_lon, center_elev, std_lat, std_lon, std_elev,
        prototype_id, name, description, data_file)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    SAVE_PROTOTYPE = """INSERT INTO \"prototypes\"
        (activity_id)
        VALUES(?)
    """

    def __init__(self, config: pyft.config.Config):
        self.connection = sql.connect(config.db_file, detect_types=sql.PARSE_DECLTYPES)
        #self.connection.set_trace_callback(print)
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self, commit: bool = True):
        self.cursor.execute(self.ACTIVITIES)
        self.cursor.execute(self.POINTS)
        self.cursor.execute(self.PROTOTYPES)
        if commit:
            self.connection.commit()

    def save_activity_data(self, metadata: 'ActivityMetaData', commit: bool = True) -> int:
        self.cursor.execute(self.SAVE_ACTIVITY_DATA, (
            metadata.activity_id,
            metadata.activity_type,
            metadata.date_time,
            metadata.distance_2d,
            # Note: center and points_std should each have length 3
            *metadata.center,
            *metadata.points_std,
            metadata.prototype_id,
            metadata.name,
            metadata.description,
            metadata.data_file
        ))
        if commit:
            self.connection.commit()
        return self.cursor.lastrowid

    def save_points(self, points: pd.DataFrame, activity_id: int, commit: bool = True):
        points = points.copy()
        points['activity_id'] = activity_id
        points.to_sql('points', self.connection, if_exists='append', index_label='id')
        if commit:
            self.connection.commit()

    def save_prototype(self, prototype_id: int, commit: bool = True):
        self.cursor.execute(self.SAVE_PROTOTYPE, (prototype_id,))
        if commit:
            self.connection.commit()

    def load_activity_data(self, activity_id: int) -> Iterable[Any]:
        self.cursor.execute('SELECT * FROM "activities" WHERE id=?', (activity_id,))
        return self.cursor.fetchone()

    def load_points(self, activity_id: int) -> pd.DataFrame:
        points = pd.read_sql_query('SELECT * FROM "points" WHERE activity_id=?', self.connection,
                                   params=(activity_id,)).drop(['id', 'activity_id'], axis=1)
        points['km_pace'] = pd.to_timedelta(points['km_pace'], unit='ns')
        points['mile_pace'] = pd.to_timedelta(points['mile_pace'], unit='ns')
        return points

    def load_prototype(self, prototype_id: int):
        self.cursor.execute('SELECT activity_id FROM "prototypes" WHERE id=?', (prototype_id,))
        return self.cursor.fetchone()

    def all_prototypes(self):
        self.cursor.execute('SELECT activity_id FROM "prototypes"')
        # fetchall returns a sequence of 1-tuples
        return [t[0] for t in self.cursor.fetchall()]

    def get_max_activity_id(self) -> int:
        self.cursor.execute('SELECT MAX(id) FROM "activities"')
        return self.cursor.fetchone()[0] or 0