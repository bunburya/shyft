import pandas as pd
import lxml.etree

from gpxpy import gpx
from pyft.single_activity import Activity

# For now, we use Garmin's TrackPointExtension rather than rolling our own.
NAMESPACES = {'gpxtpx': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1'}


def _get_point_extensions(point_data: pd.Series) -> lxml.etree.Element:
    ext_elem = lxml.etree.Element('gpxtpx:TrackPointExtension', nsmap=NAMESPACES)
    hr_elem = lxml.etree.Element('gpxtpx:hr')
    hr_elem.text = point_data['hr']
    cad_elem = lxml.etree.Element('gpxtpx:cad')
    cad_elem.text = point_data['cadence']
    ext_elem.append(hr_elem)
    ext_elem.apend(cad_elem)
    return ext_elem


def _add_point_to_seg(point_data: pd.Series, seg: gpx.GPXTrackSegment):
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
    for track_no in points['track_no'].unique():
        track = gpx.GPXTrack()
        track.type = activity.metadata.activity_type
        track_points = points[points['track_no'] == track_no]
        for seg_no in track_points['segment_no'].unique():
            seg = gpx.GPXTrackSegment()
            track.segments.append(seg)
            seg_points = track_points[track_points['segment_no'] == seg_no]
            seg_points.apply(lambda row: _add_point_to_seg(row, seg))
        g.tracks.append(track)
    return g


def activity_to_gpx_file(activity: Activity, fpath: str):
    with open(fpath, 'w') as f:
        f.write(activity_to_gpx(activity).to_xml())
