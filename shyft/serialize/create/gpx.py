"""Functions for creating GPX files from Activities."""

# Handle circular import issue when using type hints
from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from shyft.metadata import APP_NAME, VERSION

if TYPE_CHECKING:
    from shyft.activity import Activity

import pandas as pd
import lxml.etree

from gpxpy import gpx


# For now, we use Garmin's TrackPointExtension rather than rolling our own.
from shyft.serialize._xml_namespaces import GPX_NAMESPACES as NAMESPACES
TPE_URL = NAMESPACES['garmin_tpe']


def _get_point_extensions(point_data: pd.Series) -> Optional[lxml.etree.Element]:
    # gpxtpx namespace is defined at the global level in activity_to_gpx
    ext_elem = lxml.etree.Element(f'{{{TPE_URL}}}TrackPointExtension')
    has_ext = False
    if not pd.isnull(point_data['hr']):
        has_ext = True
        hr_elem = lxml.etree.Element(f'{{{TPE_URL}}}hr')
        hr_elem.text = str(point_data['hr'])
        ext_elem.append(hr_elem)
    if not pd.isnull(point_data['cadence']):
        has_ext = True
        cad_elem = lxml.etree.Element(f'{{{TPE_URL}}}cad')
        cad_elem.text = str(point_data['cadence'])
        ext_elem.append(cad_elem)

    return ext_elem if has_ext else None


def _add_point_to_seg(point_data: pd.Series, seg: gpx.GPXTrackSegment):
    #print(point_data)
    point = gpx.GPXTrackPoint(
        point_data['latitude'],
        point_data['longitude'],
        point_data['elevation'],
        point_data['time']
    )
    ext = _get_point_extensions(point_data)
    if ext is not None:
        point.extensions.append(ext)
    seg.points.append(point)


def activity_to_gpx(activity: Activity) -> gpx.GPX:
    points = activity.points
    g = gpx.GPX()
    g.creator = f'{APP_NAME} {VERSION}'
    g.name = activity.metadata.name
    g.description = activity.metadata.description
    g.time = activity.metadata.date_time
    g.nsmap |= NAMESPACES
    track = gpx.GPXTrack()
    track.type = activity.metadata.activity_type
    seg = gpx.GPXTrackSegment()
    track.segments.append(seg)
    points.apply(lambda row: _add_point_to_seg(row, seg), axis=1)
    g.tracks.append(track)
    return g


def activity_to_gpx_file(activity: Activity, fpath: str):
    with open(fpath, 'w') as f:
        f.write(activity_to_gpx(activity).to_xml())