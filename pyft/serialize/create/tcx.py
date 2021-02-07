"""Functions for creating TCX files from Activities."""

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyft.activity import Activity


import lxml.etree

from pyft.serialize._xml_namespaces import TCX_NAMESPACES, TCX_SCHEMALOCATION



def activity_to_tcx(activity: Activity, split_col: str = 'km') -> lxml.etree._Element:

    tcx_attrib = {
        'xsi:schemaLocation': TCX_SCHEMALOCATION
    }
    tcx = lxml.etree.Element('TrainingCenterDatabase', attrib=tcx_attrib, nsmap=TCX_NAMESPACES)

    if activity.laps is not None:
        lap_data = activity.laps
    else:
        lap_data = activity.get_split_summary(split_col)
