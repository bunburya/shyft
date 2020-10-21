from datetime import datetime
from typing import Iterable, Tuple, Sequence, Optional, Dict, Any, List

import pandas as pd

from pyft.config import Config
from pyft.database import DatabaseManager, str_to_timedelta
from pyft.geo_utils import distance, norm_dtw, norm_length_diff, norm_center_diff
from pyft.parse_gpx import distance_2d, parse_gpx_file
from pyft.single_activity import Activity, ActivityMetaData


class ActivityGroup:

    def __init__(self, activities: Sequence[Activity]):
        self._activities = list(activities)

    def __getitem__(self, i: int) -> Activity:
        return self._activities.__getitem__(i)

    def __setitem__(self, i: int, a: Activity):
        return self._activities.__setitem__(i, a)

    def __iter__(self):
        return self._activities.__iter__()

    def __len__(self) -> int:
        return self._activities.__len__()

    def summary(self, n: int) -> pd.DataFrame:
        # TODO
        activities = self._activities[:n]


class ActivityManager:

    def __init__(self, config: Config):
        self.config = config
        self.dbm = DatabaseManager(config)
        self.activities: List[Activity] = []


    @property
    def activity_ids(self):
        return self.dbm.get_all_activity_ids()

    @property
    def prototypes(self) -> Sequence[int]:
        """Return a sequence of the activity_ids of all Activities which are prototypes."""
        return self.dbm.get_all_prototypes()

    def get_activity_by_id(self, activity_id: int) -> Optional[Activity]:
        points = self.dbm.load_points(activity_id)
        try:
            return Activity(
                self.config,
                points,
                **self.dbm.load_activity_data(activity_id)
            )
        except ValueError:
            return None

    def get_metadata_by_id(self, activity_id: int) -> Optional[ActivityMetaData]:
        try:
            return ActivityMetaData(**self.dbm.load_activity_data(activity_id))
        except ValueError:
            return None

    def get_new_activity_id(self):
        return self.dbm.get_max_activity_id() + 1

    def add_activity(self, activity: Activity) -> int:
        """Add an Activity instance, including finding and assigning its
        matched prototype Activity.  Does not assign activity_id.  The
        Activity should be instantiated correctly (including with an
        activity_id) before being passed to this method.
        """
        if activity.metadata.prototype_id is None:
            activity.metadata.prototype_id = self.find_route_match(activity)
        self.save_activity_to_db(activity)
        self.activities.append(activity)
        return activity.metadata.activity_id

    def add_activity_from_gpx_file(self, fpath: str, activity_name: str = None,
                                   activity_description: str = None, activity_type: str = None) -> int:
        # TODO:  Is any of the below necessary?
        df, metadata = parse_gpx_file(fpath)
        _id = self.get_new_activity_id()
        _distance_2d = df['cumul_distance_2d'].iloc[-1]
        center = df[['latitude', 'longitude', 'elevation']].mean()
        return self.add_activity(
            Activity.from_gpx_file(fpath, self.config, activity_id=_id, activity_name=activity_name,
                                   activity_description=activity_description, activity_type=activity_type)
        )

    def loose_match_routes(self, a1: Activity, a2: Activity) -> bool:
        return (
                (norm_center_diff(a1.metadata.center, a2.metadata.center, a1.metadata.points_std,
                                  a2.metadata.points_std) < self.config.match_center_threshold)
                and (norm_length_diff(a1.metadata.distance_2d_km, a2.metadata.distance_2d_km) < self.config.match_length_threshold)
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
            # No matches; make this activity a prototype
            self.dbm.save_prototype(a.metadata.activity_id)
            return a.metadata.activity_id
        elif len(tight_matches) == 1:
            return tight_matches[0][0]
        else:
            return min(tight_matches, key=lambda p: p[1])[0]

    def search_activity_data(self,
                             from_date: Optional[datetime] = None,
                             to_date: Optional[datetime] = None,
                             prototype: Optional[int] = None,
                             number: Optional[int] = None
                             ) -> Sequence[ActivityMetaData]:
        results = self.dbm.search_activity_data(from_date, to_date, prototype, number)
        return [ActivityMetaData(**kwargs) for kwargs in results]

    def summarize_activity_data(self,
                             from_date: Optional[datetime] = None,
                             to_date: Optional[datetime] = None,
                             prototype: Optional[int] = None,
                             number: Optional[int] = None
                             ) -> pd.DataFrame:
        results = self.dbm.search_activity_data(from_date, to_date, prototype, number)
        return pd.DataFrame(results)

    def save_activity_to_db(self, activity: Activity):
        self.dbm.save_activity_data(activity.metadata)
        self.dbm.save_points(activity.points, activity.metadata.activity_id)

    def get_activity_matches(self, activity: ActivityMetaData, number=None) -> Iterable[ActivityMetaData]:
        results = list(filter(
            lambda a: a.activity_id != activity.activity_id,
            self.search_activity_data(prototype=activity.prototype_id)
        ))
        if number is None:
            return results
        else:
            return results[:number]
