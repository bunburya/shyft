import re
import threading
from datetime import timezone, timedelta, datetime, date
from typing import Any, Dict, Optional, Sequence, List, Collection, Set
import sqlite3 as sql

import numpy as np
import pandas as pd

import shyft.config

import warnings
warnings.simplefilter('ignore', UserWarning)

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
            #tzinfo = pytz.utc
            tzinfo = timezone.utc
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


def str_to_timedelta(s: str) -> timedelta:
    """Parses a string (in the format returned by converting the
    timedelta to a str) and returns the relevant timedelta.
    """
    tokens = s.split()
    if len(tokens) > 1:
        # Days present
        days = int(tokens[0])
    else:
        days = 0
    hours, minutes, seconds = tokens[-1].split(':')
    return timedelta(days=days, hours=int(hours), minutes=int(minutes), seconds=float(seconds))


def activity_row_to_dict(row: sql.Row) -> Dict[str, Any]:
    """Convert a Row object representing a query on activity data
    into a dict.
    """
    results = dict(row)
    results['center'] = np.array((results.pop('center_lat'), results.pop('center_lon'), results.pop('center_elev')))
    results['points_std'] = np.array((results.pop('std_lat'), results.pop('std_lon'), results.pop('std_elev')))
    results['duration'] = str_to_timedelta(results['duration'])
    return results


class DatabaseManager:
    ACTIVITIES = """CREATE TABLE IF NOT EXISTS \"activities\" (
        activity_id INTEGER PRIMARY KEY,
        activity_type TEXT NOT NULL,
        date_time TIMESTAMP NOT NULL,
        distance_2d_km FLOAT NOT NULL,
        center_lat FLOAT NOT NULL,
        center_lon FLOAT NOT NULL,
        center_elev FLOAT,
        std_lat FLOAT,
        std_lon FLOAT,
        std_elev FLOAT,
        duration TEXT,
        mean_kmph FLOAT,
        prototype_id INTEGER,
        name TEXT,
        description TEXT,
        thumbnail_file TEXT,
        gpx_file TEXT,
        tcx_file TEXT,
        source_file TEXT,
        source_format TEXT,
        calories FLOAT,
        mean_hr FLOAT,
        mean_cadence FLOAT,
        source_hash TEXT,
        FOREIGN KEY(prototype_id) REFERENCES prototypes(id)
    )"""

    POINTS = """CREATE TABLE IF NOT EXISTS \"points\" (
        id INTEGER NOT NULL,
        activity_id INTEGER NOT NULL,
        point_no INTEGER,
        latitude FLOAT NOT NULL,
        longitude FLOAT NOT NULL,
        elevation FLOAT,
        time TIMESTAMP NOT NULL,
        hr INTEGER,
        cadence INTEGER,
        step_length_2d FLOAT,
        cumul_distance_2d FLOAT,
        km INTEGER NOT NULL,
        mile INTEGER NOT NULL,
        km_pace FLOAT NOT NULL,
        mile_pace FLOAT NOT NULL,
        kmph FLOAT,
        mph FLOAT,
        run_time FLOAT NOT NULL,
        lap INTEGER,
        FOREIGN KEY(activity_id) REFERENCES activities(id),
        PRIMARY KEY(id, activity_id)
    )"""

    PROTOTYPES = """CREATE TABLE IF NOT EXISTS \"prototypes\" (
        activity_id INTEGER PRIMARY KEY,
        FOREIGN KEY(activity_id) REFERENCES activities(id)
    )"""

    LAPS = """CREATE TABLE IF NOT EXISTS \"laps\" (
        lap_no INTEGER NOT NULL,
        activity_id INTEGER NOT NULL,
        start_time TIMESTAMP NOT NULL,
        distance FLOAT NOT NULL,
        duration FLOAT NOT NULL,
        mean_cadence INTEGER,
        mean_hr INTEGER,
        mean_kmph FLOAT,
        calories INTEGER,
        FOREIGN KEY(activity_id) REFERENCES activities(id),
        PRIMARY KEY(activity_id, lap_no)
    )"""

    SAVE_ACTIVITY_DATA = """INSERT OR REPLACE INTO \"activities\"
        (activity_id, activity_type, date_time, distance_2d_km, center_lat, center_lon, center_elev, std_lat, std_lon,
        std_elev, duration, mean_kmph, prototype_id, name, description, thumbnail_file, gpx_file, tcx_file,
        source_file, source_format, calories, mean_hr, mean_cadence, source_hash)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    def __init__(self, config: shyft.config.Config):
        self.lock = threading.Lock()
        self.connection = sql.connect(config.db_file, detect_types=sql.PARSE_DECLTYPES | sql.PARSE_COLNAMES,
                                      check_same_thread=False)
        #self.connection.set_trace_callback(print)
        self.connection.row_factory = sql.Row
        self.cursor = self.connection.cursor()
        self.create_tables()

    def sql_execute(self, *args, **kwargs):
        """Execute SQL in a threadsafe manner and return the results.

        args and kwargs should be the arguments that would normally be
        passed to cursor.execute.

        NOTE: Does not commit; this must be done separately.
        """
        with self.lock:
            self.cursor.execute(*args, **kwargs)

    def sql_fetchone(self) -> sql.Row:
        with self.lock:
            return self.cursor.fetchone()

    def sql_fetchall(self) -> List[sql.Row]:
        with self.lock:
            return self.cursor.fetchall()

    def commit(self):
        self.connection.commit()

    def create_tables(self, commit: bool = True):
        self.sql_execute(self.ACTIVITIES)
        self.sql_execute(self.POINTS)
        self.sql_execute(self.LAPS)
        self.sql_execute(self.PROTOTYPES)
        if commit:
            self.commit()

    def save_metadata(self, metadata: 'ActivityMetaData', commit: bool = True) -> int:
        self.sql_execute(self.SAVE_ACTIVITY_DATA, (
            metadata.activity_id,
            metadata.activity_type,
            metadata.date_time,
            metadata.distance_2d_km,
            # Note: center and points_std should each have length 3
            *metadata.center,
            *metadata.points_std,
            str(metadata.duration),
            metadata.mean_kmph,
            metadata.prototype_id,
            metadata.name,
            metadata.description,
            metadata.thumbnail_file,
            metadata.gpx_file,
            metadata.tcx_file,
            metadata.source_file,
            metadata.source_format,
            metadata.calories,
            metadata.mean_hr,
            metadata.mean_cadence,
            metadata.source_hash
        ))
        if commit:
            self.commit()
        with self.lock:
            return self.cursor.lastrowid

    def save_dataframe(self, table_name: str, data: pd.DataFrame, activity_id: int, commit: bool = True,
                       index_label: str = 'id'):
        """Generic method to save a DataFrame to the database. Can be
        used for points or laps. DataFrame must have index with a name
        corresponding to `index label` (by default "id").
        """
        data = data.copy()
        data['activity_id'] = activity_id
        data.to_sql(table_name, self.connection, if_exists='append', index_label=index_label)
        if commit:
            self.commit()

    def save_prototype(self, prototype_id: int, commit: bool = True):
        self.sql_execute('INSERT INTO \"prototypes\" (activity_id) VALUES(?)', (prototype_id,))
        if commit:
            self.commit()

    def delete_prototype(self, prototype_id: int, commit: bool = True):
        self.sql_execute('DELETE from "prototypes" WHERE activity_id=?', (prototype_id,))
        if commit:
            self.commit()

    def change_prototype(self, old_id: int, new_id: int, commit: bool = True):
        self.save_prototype(new_id, commit=False)
        self.delete_prototype(old_id, commit=False)
        if commit:
            self.commit()

    def load_metadata(self, activity_id: int) -> Dict[str, Any]:
        """Load metadata for the activity represented by activity_id and
        return it as a dict.  Raises a ValueError if activity_id is not
        valid.
        """
        self.sql_execute('SELECT * FROM "activities" WHERE activity_id=?', (activity_id,))
        result = self.sql_fetchone()
        if not result:
            raise ValueError(f'No activity found with activity_id {activity_id}.')
        return activity_row_to_dict(result)

    def search_activity_data(self,
                             from_date: Optional[date] = None,
                             to_date: Optional[date] = None,
                             prototype: Optional[int] = None,
                             activity_type: Optional[str] = None,
                             number: Optional[int] = None,
                             ids: Collection[int] = None) -> Sequence[Dict[str, Any]]:
        where: List[str] = []
        params: List[Any] = []
        if from_date and to_date:
            where.append('date(date_time) BETWEEN ? and ?')
            params += [from_date, to_date]
        elif from_date:
            where.append('date(date_time) >= ?')
            params.append(from_date)
        elif to_date:
            where.append('date(date_time) <= ?')
            params.append(to_date)
        if prototype is not None:
            where.append('prototype_id = ?')
            params.append(prototype)
        if activity_type is not None:
            where.append('activity_type = ?')
            params.append(activity_type)
        if ids:
            where.append(f'activity_id IN ({",".join("?" * len(ids))})')
            params.extend(ids)
        query = 'SELECT * FROM "activities"'
        if where:
            query += ' WHERE ' + ' AND '.join(where)
        query += 'ORDER BY date_time'
        self.sql_execute(query, params)
        results = self.sql_fetchall()
        return [activity_row_to_dict(r) for r in results[:number]]

    def get_activities_in_timerange(self,
                                    year: int = None,
                                    month: int = None,
                                    dow: int = None,
                                    number: int = None) -> Sequence[Dict[str, Any]]:
        dt_format = []
        expected = []
        if year is not None:
            dt_format.append('%Y')
            expected.append(str(year))
        if month is not None:
            dt_format.append('%m')
            expected.append(f'{month:02}')
        if dow is not None:
            dt_format.append('%w')
            expected.append(f'{dow:02}')
        query = f'SELECT * FROM "activities" WHERE datetime({" ".join(dt_format)}, date_time) = "{" ".join(expected)}"'
        self.sql_execute(query)
        results = self.sql_fetchall()
        return [activity_row_to_dict(r) for r in results[:number]]

    def load_points(self, activity_id: int) -> pd.DataFrame:
        points = pd.read_sql_query('SELECT * FROM "points" WHERE activity_id=?', self.connection,
                                   params=(activity_id,)).drop(['id', 'activity_id'], axis=1)
        # Convert pace-related columns from floats to timedeltas
        for col in ('km_pace', 'mile_pace', 'run_time'):
            points[col] = pd.to_timedelta(points[col], unit='ns')
        return points

    def load_laps(self, activity_id: int) -> Optional[pd.DataFrame]:
        laps = pd.read_sql_query('SELECT * FROM "laps" WHERE activity_id=?', self.connection,
                                 params=(activity_id,)).drop('activity_id', axis=1).set_index('lap_no')
        if laps.empty:
            return None
        else:
            laps['duration'] = pd.to_timedelta(laps['duration'], unit='ns')
            return laps

    @property
    def all_activity_ids(self) -> List[int]:
        self.sql_execute('SELECT activity_id from "activities"')
        # fetchall returns a sequence of Row objects
        return [r['activity_id'] for r in self.sql_fetchall()]

    @property
    def all_prototypes(self) -> List[int]:
        self.sql_execute('SELECT activity_id FROM "prototypes"')
        return [r['activity_id'] for r in self.sql_fetchall()]

    @property
    def all_source_hashes(self) -> Set[str]:
        self.sql_execute('SELECT source_hash FROM "activities" WHERE source_hash IS NOT NULL')
        return {r['source_hash'] for r in self.sql_fetchall()}

    @property
    def all_activity_types(self) -> Set[str]:
        self.sql_execute('SELECT DISTINCT activity_type FROM "activities"')
        return {r['activity_type'] for r in self.sql_fetchall()}

    @property
    def max_activity_id(self) -> int:
        """Return the highest activity_id in activities.  If activities
        is empty, return -1.
        """
        self.sql_execute('SELECT MAX(activity_id) FROM "activities"')
        max_id = self.sql_fetchone()[0]
        if max_id is None:
            max_id = -1
        return max_id

    @property
    def earliest_datetime(self) -> Optional[datetime]:
        self.sql_execute('SELECT MIN(date_time) as "date_time [timestamp]" FROM "activities"')
        return self.sql_fetchone()[0]

    @property
    def latest_datetime(self) -> Optional[datetime]:
        self.sql_execute('SELECT MAX(date_time) as "date_time [timestamp]" FROM "activities"')
        return self.sql_fetchone()[0]

    def delete_points(self, activity_id: int, commit: bool = True):
        self.sql_execute('DELETE FROM "points" WHERE activity_id=?', (activity_id,))
        if commit:
            self.commit()

    def delete_laps(self, activity_id: int, commit: bool = True):
        self.sql_execute('DELETE FROM "laps" WHERE activity_id=?', (activity_id,))
        if commit:
            self.commit()

    def delete_metadata(self, activity_id: int, commit: bool = True):
        self.sql_execute('DELETE FROM "activities" WHERE activity_id=?', (activity_id,))
        if commit:
            self.commit()

    def delete_activity(self, activity_id: int, commit: bool = True):
        # NOTE: This doesn't handle updating the prototype ID of the matched activities if the deleted activity
        # is a prototype. That must be done elsewhere (eg, in ActivityManager).
        self.delete_points(activity_id, commit=False)
        self.delete_laps(activity_id, commit=False)
        self.delete_metadata(activity_id, commit=False)
        if commit:
            self.commit()
