"""Functions for creating files (eg, GPX files) from Activities."""

# Handle circular import issue when using type hints
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyft.single_activity import Activity

import pandas as pd
import lxml.etree

from gpxpy import gpx


# For now, we use Garmin's TrackPointExtension rather than rolling our own.
TPE_URL = 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1'
NAMESPACES = {'gpxtpx': TPE_URL}


def _get_point_extensions(point_data: pd.Series) -> lxml.etree.Element:
    # gpxtpx namespace is defined at the global level in activity_to_gpx
    ext_elem = lxml.etree.Element(f'{{{TPE_URL}}}TrackPointExtension')
    hr_elem = lxml.etree.Element(f'{{{TPE_URL}}}hr')
    hr_elem.text = str(point_data['hr'])
    cad_elem = lxml.etree.Element(f'{{{TPE_URL}}}cad')
    cad_elem.text = str(point_data['cadence'])
    ext_elem.append(hr_elem)
    ext_elem.append(cad_elem)
    return ext_elem


def _add_point_to_seg(point_data: pd.Series, seg: gpx.GPXTrackSegment):
    #print(point_data)
    point = gpx.GPXTrackPoint(
        point_data['latitude'],
        point_data['longitude'],
        point_data['elevation'],
        point_data['time']
    )
    point.extensions.append(_get_point_extensions(point_data))
    seg.points.append(point)


def activity_to_gpx(activity: Activity) -> gpx.GPX:
    points = activity.points
    g = gpx.GPX()
    g.creator = 'PyftGPX'
    g.name = activity.metadata.name
    g.description = activity.metadata.description
    g.time = activity.metadata.date_time
    g.nsmap |= NAMESPACES
    for track_no in points['track_no'].unique():
        track = gpx.GPXTrack()
        track.type = activity.metadata.activity_type
        track_points = points[points['track_no'] == track_no]
        for seg_no in track_points['segment_no'].unique():
            seg = gpx.GPXTrackSegment()
            track.segments.append(seg)
            seg_points = track_points[track_points['segment_no'] == seg_no]
            seg_points.apply(lambda row: _add_point_to_seg(row, seg), axis=1)
        g.tracks.append(track)
    return g


def activity_to_gpx_file(activity: Activity, fpath: str):
    with open(fpath, 'w') as f:
        f.write(activity_to_gpx(activity).to_xml())
