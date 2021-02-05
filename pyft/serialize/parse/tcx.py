"""Parser for FIT files."""

from datetime import timezone, timedelta, datetime
from typing import List

import lxml.etree
import dateutil.parser as dp
import pandas as pd

from pyft.serialize.parse._base import PyftParserException, BaseActivityParser, GarminMixin, StravaMixin


class FITParserError(PyftParserException): pass


class TCXParser(BaseActivityParser, GarminMixin, StravaMixin):
    NAMESPACES = {
        'ns': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2',
        'user_ns': 'http://www.garmin.com/xmlschemas/UserProfile/v2',
        'activity_ns': 'http://www.garmin.com/xmlschemas/ActivityExtension/v2',
        'profile_ns': 'http://www.garmin.com/xmlschemas/ProfileExtension/v1',
        'goals_ns': 'http://www.garmin.com/xmlschemas/ActivityGoals/v1'
    }

    def __init__(self, *args, **kwargs):
        self._metadata = {}
        super().__init__(*args, **kwargs)

    def _parse(self, fpath: str):
        self._xml_root: lxml.etree._Element = lxml.etree.parse(fpath).getroot()
        self._activity_elem: lxml.etree._Element = self._xml_root.find('ns:Activities', self.NAMESPACES)[0]
        self._iter_laps()
        self._parse_metadata()

    def _iter_laps(self):
        """Iterate through an Activity element and handle each Lap."""
        laps_data = []
        points_data = []
        for lap in self._activity_elem.findall('ns:Lap', self.NAMESPACES):
            lap_no = self._get_lap_no()
            lap_data = {'lap_no': lap_no}
            if 'StartTime' in lap.attrib:
                lap_data['start_time'] = dp.parse(lap.attrib['StartTime']).astimezone(timezone.utc)
            if (dist_elem := lap.find('ns:DistanceMeters', self.NAMESPACES)) is not None:
                lap_data['distance'] = float(dist_elem.text)
            if (time_elem := lap.find('ns:TotalTimeSeconds', self.NAMESPACES)) is not None:
                lap_data['duration'] = timedelta(seconds=float(time_elem.text))
            if (cal_elem := lap.find('ns:Calories', self.NAMESPACES)) is not None:
                lap_data['calories'] = float(cal_elem.text)
            laps_data.append(lap_data)
            self._iter_points(lap, points_data, lap_no)
        self._laps_df = pd.DataFrame(laps_data, columns=self.INITIAL_COL_NAMES_LAPS)
        points_df = pd.DataFrame(points_data, columns=self.INITIAL_COL_NAMES_POINTS)
        self._points_df = self._handle_points_data(points_df)

    def _iter_points(self, lap_elem: lxml.etree._Element, points_data: List[dict], lap_no: int):
        track = lap_elem.find('ns:Track', self.NAMESPACES)
        for point_elem in track.findall('ns:Trackpoint', self.NAMESPACES):
            data = {
                'lap': lap_no,
                'track_no': 0,
                'segment_no': 0,
                'point_no': self._get_point_no()
            }
            lat = lon = None
            if (position_elem := point_elem.find('ns:Position', self.NAMESPACES)) is not None:
                if (lat_elem := position_elem.find('ns:LatitudeDegrees', self.NAMESPACES)) is not None:
                    lat = data['latitude'] = float(lat_elem.text)
                if (lon_elem := position_elem.find('ns:LongitudeDegrees', self.NAMESPACES)) is not None:
                    lon = data['longitude'] = float(lon_elem.text)

            if (time_elem := point_elem.find('ns:Time', self.NAMESPACES)) is not None:
                data['time'] = dp.parse(time_elem.text).astimezone(timezone.utc)
            if (elev_elem := point_elem.find('ns:AltitudeMeters', self.NAMESPACES)) is not None:
                data['elevation'] = float(elev_elem.text)
            if (hr_elem := point_elem.find('ns:HeartRateBpm', self.NAMESPACES)) is not None:
                data['hr'] = float(hr_elem.find('ns:Value', self.NAMESPACES).text)

            # Cadence and speed can be recorded differently in different files:
            # - sometimes as direct children of the Trackpoint element (as Cadence and Speed);
            # - sometimes as children of the Extensions element (as activity_ns:RunCadence and activity_ns:Speed)
            if (cad_elem := point_elem.find('ns:Cadence', self.NAMESPACES)) is not None:
                data['cadence'] = float(cad_elem.text)
            if (speed_elem := point_elem.find('.//activity_ns:Speed', self.NAMESPACES)) is not None:
                data['kmph'] = self._convert_speed(float(speed_elem.text))
            if cad_elem is None:
                if (cad_ext_elem := point_elem.find('.//activity_ns:RunCadence', self.NAMESPACES)) is not None:
                    data['cadence'] = float(cad_ext_elem.text)
            if speed_elem is None:
                if (speed_ext_elem := point_elem.find('.//activity_ns:Speed', self.NAMESPACES)) is not None:
                    data['kmph'] = self._convert_speed(float(speed_ext_elem.text))


            self._handle_backfill(data, points_data, lat, lon)

    def _parse_metadata(self):
        """Get activity metadata from the XML element representing the
        activity and the DataFrame with laps data. Must be called after
        _iter_laps.
        """
        if (id_elem := self._activity_elem.find('ns:Id', self.NAMESPACES)) is not None:
            self._metadata['date_time'] = dp.parse(id_elem.text).astimezone(timezone.utc)
        self._metadata['distance_2d_km'] = self._laps_df['distance'].sum() / 1000
        self._metadata['duration'] = self._laps_df['duration'].sum()
        # Strangely, non-running activities seem to just have a Sport value of "Other", even if the underlying FIT
        # data reports a more specific activity type (eg, walking).
        self._metadata['activity_type'] = self.GARMIN_TYPES.get(self._activity_elem.attrib.get('Sport', '').lower())

    @property
    def metadata(self) -> dict:
        return self._metadata

    @property
    def activity_type(self) -> str:
        return self._metadata['activity_type']

    @property
    def points(self) -> pd.DataFrame:
        return self._points_df

    @property
    def laps(self) -> pd.DataFrame:
        return self._laps_df

    @property
    def date_time(self) -> datetime:
        return self._metadata['date_time']
