from typing import Iterable, Tuple, Sequence, Optional

import numpy as np
from scipy.spatial.distance import euclidean

from fastdtw import fastdtw

from pyft.config import Config
from pyft.database import DatabaseManager
from pyft.geo_utils import distance, norm_dtw, norm_length_diff, norm_center_diff
from pyft.parse_gpx import distance_2d, parse_gpx_file
from pyft.single_activity import Activity


class ActivityManager:

    def __init__(self, config: Config):
        self.config = config
        self.db = DatabaseManager(config)
        self.activities = []

    @property
    def prototypes(self) -> Sequence[int]:
        """Return a sequence of the activity_ids of all Activities which are prototypes."""
        return self.db.all_prototypes()

    def get_activity_by_id(self, activity_id: int) -> Activity:
        points = self.db.load_points(activity_id)
        (_id, _type, _date_time, _distance_2d, _center_lat, _center_lon, _center_elev, _std_lat, _std_lon, _std_elev,
         _prototype_id, _name, _description, _data_file) = self.db.load_activity_data(activity_id)
        return Activity(
            activity_id=_id,
            activity_type=_type,
            date_time=_date_time,
            distance_2d=_distance_2d,
            center=np.array((_center_lat, _center_lon, _center_elev)),
            points_std=np.array((_std_lat, _std_lon, _std_elev)),
            prototype_id=_prototype_id,
            name=_name,
            description=_description,
            data_file=_data_file,
            points=points
        )

    def add_activity(self, activity: Activity) -> int:
        activity.metadata.activity_id = self.db.get_max_activity_id() + 1
        activity.metadata.prototype_id = self.find_route_match(activity)
        self.save_activity_to_db(activity)
        self.activities.append(activity)
        return activity.metadata.activity_id

    def add_activity_from_gpx_file(self, fpath: str, activity_name: str = None,
                                   activity_description: str = None, activity_type: str = 'run') -> int:
        df, metadata = parse_gpx_file(fpath)
        _distance_2d = df['cumul_distance_2d'].iloc[-1]
        center = df[['latitude', 'longitude', 'elevation']].mean()
        return self.add_activity(Activity.from_gpx_file(fpath, activity_name, activity_description, activity_type))

    def loose_match_routes(self, a1: Activity, a2: Activity) -> bool:
        return (
                (norm_center_diff(a1.metadata.center, a2.metadata.center, a1.metadata.points_std,
                                  a2.metadata.points_std) < self.config.match_center_threshold)
                and (norm_length_diff(a1.metadata.distance_2d, a2.metadata.distance_2d) < self.config.match_length_threshold)
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
            self.db.save_prototype(a.metadata.activity_id)
            return a.metadata.activity_id
        elif len(tight_matches) == 1:
            return tight_matches[0][0]
        else:
            return min(tight_matches, key=lambda p: p[1])[0]

    def save_activity_to_db(self, activity: Activity):
        self.db.save_activity_data(activity.metadata)
        self.db.save_points(activity.points, activity.metadata.activity_id)
