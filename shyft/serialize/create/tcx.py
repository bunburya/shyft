"""Functions for creating TCX files from Activities."""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from shyft.serialize import _activity_types

if TYPE_CHECKING:
    from shyft.activity import Activity

import lxml.etree
import pandas as pd

from shyft.serialize._xml_namespaces import TCX_NAMESPACES, TCX_SCHEMALOCATION


def _tcx_elem(name: str, attrib: Optional[dict] = None, ns_name: Optional[str] = None) -> lxml.etree._Element:
    """Create an element in the relevant TCX namespace."""
    if attrib is None:
        attrib = {}
    ns = TCX_NAMESPACES[ns_name]
    return lxml.etree.Element(f'{{{ns}}}{name}', attrib=attrib, nsmap=TCX_NAMESPACES)


def _create_point_elem(point: pd.Series, track_elem: lxml.etree._Element):
    """Create a Trackpoint element from a pd.Series representing a
    single point, and append it to `track_elem`.
    """
    # The TCX schema states that a Trackpoint *must* have a "Time" element
    # and *may* have the following elements (order matters):
    # - Position
    # - AltitudeMeters
    # - DistanceMeters
    # - HeartRateBpm
    # - Cadence
    # - SensorState
    # - Extensions
    tp_elem = _tcx_elem('Trackpoint')

    time_elem = _tcx_elem('Time')
    time_elem.text = point['time'].isoformat()
    tp_elem.append(time_elem)

    pos_elem = _tcx_elem('Position')
    lat_elem = _tcx_elem('LatitudeDegrees')
    lat_elem.text = str(point['latitude'])
    pos_elem.append(lat_elem)
    lon_elem = _tcx_elem('LongitudeDegrees')
    lon_elem.text = str(point['longitude'])
    pos_elem.append(lon_elem)
    tp_elem.append(pos_elem)

    if ('elevation' in point) and pd.notnull(point['elevation']):
        elev_elem = _tcx_elem('AltitudeMeters')
        elev_elem.text = str(point['elevation'])
        tp_elem.append(elev_elem)

    dist_elem = _tcx_elem('DistanceMeters')
    dist_elem.text = str(point['cumul_distance_2d'])
    tp_elem.append(dist_elem)

    if ('hr' in point) and (pd.notnull(point['hr'])):
        hr_elem = _tcx_elem('HeartRateBpm')
        hr_val_elem = _tcx_elem('Value')
        hr_val_elem.text = str(round(point['hr']))
        hr_elem.append(hr_val_elem)
        tp_elem.append(hr_elem)

    if ('cadence' in point) and (pd.notnull(point['cadence'])):
        cad_elem = _tcx_elem('Cadence')
        cad_elem.text = str(round(point['cadence']))
        tp_elem.append(cad_elem)

    ext_elem = _tcx_elem('Extensions')
    act_ext_elem = _tcx_elem('TPX', ns_name='activity_extension')
    speed_ext_elem = _tcx_elem('Speed', ns_name='activity_extension')
    speed_ext_elem.text = str(point['kmph'] / 3.6)
    act_ext_elem.append(speed_ext_elem)
    ext_elem.append(act_ext_elem)
    tp_elem.append(ext_elem)

    track_elem.append(tp_elem)


def _create_track_elem(points: pd.DataFrame) -> lxml.etree._Element:
    """Create a Track element."""
    # The TCX schema states that a Track element *must* have at least one Trackpoint element.

    track_elem = _tcx_elem('Track')
    points.apply(_create_point_elem, args=(track_elem,), axis=1)
    return track_elem


def _create_lap_elem(lap: pd.Series, points: pd.DataFrame) -> lxml.etree._Element:
    """Create a Lap element.

    `lap` should be a pd.Series corresponding to a row in
    activity.laps.

    `points` should be a pd.DataFrame which is a subset of
    activity.points, containing only the points belonging to the
    relevant lap/split.
    """
    # The TCX schema states that a Lap element *must* have a "StartTime" attribute
    # and *must* contain the following elements:
    # - TotalTimeSeconds
    # - DistanceMeters
    # - Calories
    # - Intensity
    # - TriggerMethod
    # Additionally, a lap *may* have the following elements:
    # - MaximumSpeed
    # - AverageHeartRateBpm
    # - MaximumHeartRateBpm
    # - Cadence
    # - Track
    # - Notes
    # - Extensions

    notes = []
    lap_elem = _tcx_elem('Lap', attrib={'StartTime': lap['start_time'].isoformat()})

    total_time_elem = _tcx_elem('TotalTimeSeconds')
    total_time_elem.text = str(float(lap['duration'].total_seconds()))
    lap_elem.append(total_time_elem)

    distance_elem = _tcx_elem('DistanceMeters')
    distance_elem.text = str(float(lap['distance']))
    lap_elem.append(distance_elem)

    calories_elem = _tcx_elem('Calories')
    if ('calories' not in lap) or pd.isnull(lap['calories']):
        # For some reason, the TCX schema requires calories.
        # If we do not have calorie data, we set this to 0, and leave a note indicating that the calorie information
        # was not present.
        calories_text = '0'
        notes.append('shyft:no_calorie_data')
    else:
        calories_text = str(round(lap['calories']))
    calories_elem.text = calories_text
    lap_elem.append(calories_elem)

    intensity_elem = _tcx_elem('Intensity')
    # Intensity is required, and must be "Active" or "Resting".
    # Absent any objective way to determine the level, we just say "Active" for everything (this is an "activity",
    # after all).
    intensity_elem.text = 'Active'
    lap_elem.append(intensity_elem)

    trigger_elem = _tcx_elem('TriggerMethod')
    # TriggerMethod is required and refers to why the lap was created (eg, whether it was automatically created once a
    # certain distance was run, or manually created by the user, etc).
    # I'm only including this because it's a required element, so for the sake of simplicity, we'll just set it to
    # "Manual" for now (that seems to be what Garmin does with my TCX files anyway, even when the laps are actually
    # triggered by distance).
    trigger_elem.text = 'Manual'
    lap_elem.append(trigger_elem)

    track_elem = _create_track_elem(points)
    lap_elem.append(track_elem)

    if notes:
        notes_elem = _tcx_elem('Notes')
        notes_elem.text = ' '.join(notes)
        lap_elem.append(notes_elem)

    # TODO: Add other optional elements.

    return lap_elem

def _create_activity_elem(activity: Activity, split_col) -> lxml.etree._Element:
    """Create an Activity element from an Activity."""
    # The TCX schema says that an Activity element *must* have a "Sport" attribute and also *must* have an "Id" element
    # (representing the date and time of the activity) and one or more Lap elements.
    # In addition an Activity element *may* have the following elements:
    # - Notes
    # - Training
    # - Creator
    # - Extensions
    sport = _activity_types.SHYFT_TO_TCX.get(activity.metadata.activity_type, 'Other')
    activity_elem = _tcx_elem('Activity', attrib={'Sport': sport})

    id_elem = _tcx_elem('Id')
    id_elem.text = activity.metadata.date_time.isoformat()
    activity_elem.append(id_elem)

    if activity.laps is not None:
        lap_data = activity.laps
        lap_no_col = 'lap'
    else:
        lap_data = activity.get_split_summary(split_col)
        lap_no_col = split_col

    for i in lap_data.index:
        lap_no = i
        lap_points = activity.points[activity.points[lap_no_col] == lap_no]
        activity_elem.append(_create_lap_elem(lap_data.loc[i], lap_points))

    return activity_elem


def activity_to_tcx(activity: Activity, split_col: str) -> lxml.etree._Element:
    schema_location = lxml.etree.QName("http://www.w3.org/2001/XMLSchema-instance", "schemaLocation")
    tcx_attrib = {
        schema_location: TCX_SCHEMALOCATION
    }
    tcx_elem = _tcx_elem('TrainingCenterDatabase', attrib=tcx_attrib)
    # The TCX schema says that a TrainingCenterDatabase element *may* have the following elements:
    # - Folders
    # - Activities
    # - Workouts
    # - Course
    # - Author
    # - Extensions

    activities_elem = _tcx_elem('Activities')
    # The TCX schema says that an Activities element *may* have one or more Activity elements and one or more
    # MultiSportSession elements.
    activities_elem.append(_create_activity_elem(activity, split_col))

    tcx_elem.append(activities_elem)

    return tcx_elem

def activity_to_tcx_file(activity: Activity, fpath: str, split_col: str = 'km'):

    with open(fpath, 'wb') as f:
        f.write(lxml.etree.tostring(
            activity_to_tcx(activity, split_col),
            encoding='UTF-8',
            xml_declaration=True,
            pretty_print=True
        ))

