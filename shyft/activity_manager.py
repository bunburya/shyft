import calendar
import os
from datetime import date, timedelta, datetime
from typing import Tuple, Sequence, Optional, Dict, List, Generator, Union, Callable, Any, Collection, Set

import pandas as pd
from dateutil.relativedelta import relativedelta

from shyft.config import Config
from shyft.database import DatabaseManager
from shyft.geo_utils import norm_dtw, norm_length_diff, norm_center_diff
from shyft.activity import Activity, ActivityMetaData
from shyft.df_utils import summarize_metadata
from shyft.logger import get_logger

logger = get_logger(__name__)


def _iter_dates(start: date, end_inclusive: date,
                step: Union[timedelta, relativedelta]) -> Generator[datetime, None, None]:
    current = start
    while current <= end_inclusive:
        yield current
        current += step


class ActivityManager:

    def __init__(self, config: Config):
        self.config = config
        if not os.path.exists(config.data_dir):
            os.makedirs(config.data_dir)
        self.dbm = DatabaseManager(config)
        self._cache: Dict[int, Activity] = {}

    @property
    def activity_ids(self):
        return self.dbm.all_activity_ids

    @property
    def prototypes(self) -> List[int]:
        """Return a sequence of the activity_ids of all Activities which are prototypes."""
        return self.dbm.all_prototypes

    @property
    def all_metadata(self) -> List[ActivityMetaData]:
        return [self.get_metadata_by_id(i) for i in self.activity_ids]

    @property
    def activity_types(self) -> Set[str]:
        return self.dbm.all_activity_types

    def get_activity_by_id(self, activity_id: int, cache: bool = True) -> Optional[Activity]:
        # logger.info(f'Getting activity with ID {activity_id} .')
        if activity_id in self._cache:
            #logger.debug(f'Fetching activity from cache.')
            return self._cache[activity_id]
        else:
            #logger.debug(f'Activity not in cache; loading from database.')
            points = self.dbm.load_points(activity_id)
            laps = self.dbm.load_laps(activity_id)
            try:
                activity = Activity(
                    self.config,
                    points,
                    laps,
                    **self.dbm.load_metadata(activity_id)
                )
                if cache:
                    self._cache[activity_id] = activity
                return activity
            except ValueError:
                logger.warning(f'No activity with ID {activity_id} found in database.')
                return None

    def get_metadata_by_id(self, activity_id: int) -> Optional[ActivityMetaData]:
        if activity_id in self._cache:
            return self._cache[activity_id].metadata
        else:
            try:
                return ActivityMetaData(self.config, **self.dbm.load_metadata(activity_id))
            except ValueError:
                return None

    def get_new_activity_id(self) -> int:
        return self.dbm.max_activity_id + 1

    def add_activity(self, activity: Activity, cache: bool = True) -> int:
        """Add an Activity instance, including finding and assigning its
        matched prototype Activity. Does not assign activity_id. The
        Activity should be instantiated correctly (including with an
        activity_id) before being passed to this method.
        """
        if activity.metadata.prototype_id is None:
            activity.metadata.prototype_id = self.find_route_match(activity)
        self.save_activity_to_db(activity)
        _id = activity.metadata.activity_id
        if cache:
            self._cache[_id] = activity
        return _id

    def add_activity_from_file(self, fpath: str, activity_name: str = None,
                               activity_description: str = None, activity_type: str = None) -> int:
        _id = self.get_new_activity_id()
        return self.add_activity(
            Activity.from_file(fpath, self.config, activity_id=_id, activity_name=activity_name,
                               activity_description=activity_description, activity_type=activity_type)
        )

    def loose_match_routes(self, a1: Activity, a2: Activity) -> bool:
        return (
                (norm_center_diff(a1.metadata.center, a2.metadata.center, a1.metadata.points_std,
                                  a2.metadata.points_std) < self.config.match_center_threshold)
                and (norm_length_diff(a1.metadata.distance_2d_km,
                                      a2.metadata.distance_2d_km) < self.config.match_length_threshold)
        )

    def tight_match_routes(self, a1: Activity, a2: Activity) -> Tuple[bool, float]:
        norm_distance = norm_dtw(a1.points[['latitude', 'longitude']], a2.points[['latitude', 'longitude']])
        return (norm_distance < self.config.tight_match_threshold), norm_distance

    def find_route_match(self, a: Activity) -> int:
        prototypes = (self.get_activity_by_id(i) for i in self.prototypes)
        # First, find loose matches
        loose_matches = filter(lambda p: self.loose_match_routes(p, a), prototypes)
        tight_matches = []
        for p in loose_matches:
            match, dist = self.tight_match_routes(p, a)
            if match:
                tight_matches.append((p.metadata.activity_id, dist))
        if not tight_matches:
            # No matches; make this _activity_elem a prototype
            self.dbm.save_prototype(a.metadata.activity_id)
            return a.metadata.activity_id
        elif len(tight_matches) == 1:
            return tight_matches[0][0]
        else:
            return min(tight_matches, key=lambda p: p[1])[0]

    def search_metadata(self,
                        from_date: Optional[date] = None,
                        to_date: Optional[date] = None,
                        prototype: Optional[int] = None,
                        activity_type: Optional[str] = None,
                        number: Optional[int] = None,
                        ids: Collection[int] = None
                        ) -> List[ActivityMetaData]:
        results = self.dbm.search_activity_data(from_date, to_date, prototype, activity_type, number, ids)
        return [ActivityMetaData(self.config, **kwargs) for kwargs in results]

    def summarize_metadata(self,
                           from_date: Optional[date] = None,
                           to_date: Optional[date] = None,
                           prototype: Optional[int] = None,
                           activity_type: Optional[str] = None,
                           number: Optional[int] = None
                           ) -> pd.DataFrame:
        metadata = self.search_metadata(from_date, to_date, prototype, activity_type, number)
        return summarize_metadata(metadata)

    def save_activity_to_db(self, activity: Activity):
        self.dbm.save_metadata(activity.metadata)
        self.dbm.save_dataframe('points', activity.points, activity.metadata.activity_id)
        if activity.laps is not None:
            self.dbm.save_dataframe('laps', activity.laps, activity.metadata.activity_id, index_label='lap_no')

    def get_activity_matches(self, metadata: ActivityMetaData,
                             number: Optional[int] = None) -> List[ActivityMetaData]:
        results = list(filter(
            lambda a: a.activity_id != metadata.activity_id,
            self.search_metadata(prototype=metadata.prototype_id)
        ))
        if number is None:
            return results
        else:
            return results[:number]

    def delete_activity(self, activity_id: int, delete_gpx_file: bool = True, delete_tcx_file: bool = True,
                        delete_source_file: bool = True):
        metadata = self.get_metadata_by_id(activity_id)
        if metadata is None:
            raise ValueError(f'Bad _activity_elem ID: {activity_id}')
        self.dbm.delete_activity(activity_id)
        if activity_id in self._cache:
            self._cache.pop(activity_id)
        if metadata.activity_id == metadata.prototype_id:
            matches = self.get_activity_matches(metadata)
            if matches:
                next_match_id = matches[0].activity_id
                self.replace_prototype(metadata.activity_id, next_match_id)
            else:
                self.dbm.delete_prototype(metadata.activity_id)
        if delete_gpx_file and (metadata.gpx_file is not None) and os.path.exists(metadata.gpx_file):
            os.remove(metadata.gpx_file)
        if delete_tcx_file and (metadata.tcx_file is not None) and os.path.exists(metadata.tcx_file):
            os.remove(metadata.tcx_file)
        if delete_source_file and (metadata.source_file is not None) and os.path.exists(metadata.source_file):
            os.remove(metadata.source_file)
        logger.info(f'Deleted activity with ID {metadata.activity_id}.')

    def replace_prototype(self, old_id: int, new_id: int):
        matches = self.search_metadata(prototype=old_id)
        for metadata in matches:
            if metadata.activity_id in self._cache:
                self._cache.pop(metadata.activity_id)
            metadata.prototype_id = new_id
            self.dbm.save_metadata(metadata, commit=False)
        self.dbm.change_prototype(old_id, new_id, commit=False)
        self.dbm.commit()

    def get_metadata_by_month(self, month: date, **kwargs) -> List[ActivityMetaData]:
        """
        :param month: The month to search. The `day` component of the `date` object is disregarded.
        :param kwargs: This method also takes the same arguments (other than from_date and to_date) as search_metadata,\
        and will filter the results accordingly.
        :return: A list of ActivityMetaData objects representing all (relevant) activities in the week that commences\
        on `start`.
        """
        #print(month, type(month))
        year = month.year
        month = month.month
        _, last = calendar.monthrange(year, month)
        start = date(year, month, 1)
        end = date(year, month, last)
        #print(start, end)
        return self.search_metadata(from_date=start, to_date=end, **kwargs)

    def get_metadata_by_week(self, start: date, **kwargs) -> List[ActivityMetaData]:
        """
        :param start: The date on which the week commences.
        :param kwargs: This method also takes the same arguments (other than `from_date` and `to_date`) as\
        search_metadata, and will filter the results accordingly.
        :return: A list of ActivityMetaData objects representing all (relevant) activities in the week that commences\
        on `start`.
        """
        end = start + timedelta(days=7)
        return self.search_metadata(start, end, **kwargs)

    def _metadata_time_series_df(self, freq: Union[timedelta, relativedelta],
                                 summary_func: Callable[[date, ...], List[ActivityMetaData]],
                                 from_date: Optional[date] = None, to_date: Optional[date] = None,
                                 **kwargs) -> pd.DataFrame:
        if from_date is None:
            from_date = self.earliest_datetime.date()
        if to_date is None:
            to_date = self.latest_datetime.date()
        data = []
        for date in _iter_dates(from_date, to_date, freq):
            period_data = summary_func(date, **kwargs)
            if not period_data:
                continue
            period_summary = summarize_metadata(period_data)
            #logger.debug(period_summary['mean_hr'])
            data.append({
                'date': pd.to_datetime(date),  # Pandas doesn't have its own `date` equivalent so convert to datetime
                'activity_count': period_summary.shape[0],
                'total_duration': period_summary['duration'].sum(),
                'total_distance_2d_km': period_summary['distance_2d_km'].sum(),
                'total_distance_2d_mile': period_summary['distance_2d_mile'].sum(),
                'mean_kmph': period_summary['mean_kmph'].mean(),
                'mean_mph': period_summary['mean_mph'].mean(),
                'mean_hr': period_summary['mean_hr'].mean(),
                'mean_cadence': period_summary['mean_cadence'].mean()
            })
        return pd.DataFrame(data).set_index('date')

    def metadata_weekly_time_series(self, from_date: Optional[date] = None, to_date: Optional[date] = None,
                                    **kwargs) -> pd.DataFrame:
        """
        :param from_date: The start date of the period you want to search.
        :param to_date: The end date of the period you want to search (inclusive).
        :param kwargs: This method also takes the same arguments (other than from_date and to_date) as search_metadata,\
        and will filter the results accordingly.
        :return: A pd.DataFrame, conforming to `metadata_time_series_schema`, containing information about the relevant\
        activities grouped by week.
        """
        return self._metadata_time_series_df(timedelta(weeks=1), self.get_metadata_by_week,
                                             from_date, to_date, **kwargs)

    def metadata_monthly_time_series(self, from_date: Optional[date] = None, to_date: Optional[date] = None,
                                     **kwargs) -> pd.DataFrame:
        """
        :param from_date: The start date of the period you want to search.
        :param to_date: The end date of the period you want to search (inclusive).
        :param kwargs: This method also takes the same arguments (other than from_date and to_date) as search_metadata,\
        and will filter the results accordingly.
        :return: A pd.DataFrame, conforming to `metadata_time_series_schema`, containing information about the relevant\
        activities grouped by month.
        """
        return self._metadata_time_series_df(relativedelta(months=1), self.get_metadata_by_month,
                                             from_date, to_date, **kwargs)

    @property
    def earliest_datetime(self) -> Optional[datetime]:
        """
        :return: The date and time of the earliest recorded activity.
        """
        return self.dbm.earliest_datetime

    @property
    def latest_datetime(self) -> Optional[datetime]:
        """
        :return: The date and time of the latest recorded activity.
        """
        return self.dbm.latest_datetime

    def __getitem__(self, key: int) -> Activity:
        #logger.debug(f'Getting activity {key}.')
        activity = self.get_activity_by_id(key)
        if activity is None:
            raise KeyError(f'No activity with ID {key}.')
        else:
            return activity

    def __iter__(self):
        self._ids = self.activity_ids
        self._i = -1
        return self

    def __next__(self) -> Activity:
        self._i += 1
        try:
            return self[self._ids[self._i]]
        except IndexError:
            raise StopIteration

    def __len__(self) -> int:
        return len(self.activity_ids)
