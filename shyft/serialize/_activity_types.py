"""Dicts mapping the activity types used by other services (Strava,
Garmin etc) to the ones used by Pyft.
"""


def _reverse_dict(in_dict: dict) -> dict:
    """Reverse a dict so that keys become values and values become keys."""

    out_dict = {}
    for k in in_dict:
        out_dict[in_dict[k]] = k
    return out_dict

DEFAULT_TYPE = 'activity'

SHYFT_TYPES = {
    'run',
    'walk',
    'hike',
    'cycle',
    DEFAULT_TYPE
}

FIT_TO_SHYFT = {
    'hiking': 'hike',
    'running': 'run',
    'walking': 'walk'
}

TCX_TO_SHYFT = {
    'Running': 'run',
    'Biking': 'cycle',
    'Other': DEFAULT_TYPE
}

# Unlike GPX, TCX only allows three different activity types, so we need to convert our own types back to these in order
# to create a TCX file from an Activity.
SHYFT_TO_TCX = _reverse_dict(TCX_TO_SHYFT)
for t in SHYFT_TYPES:
    if t not in SHYFT_TO_TCX:
        SHYFT_TO_TCX[t] = 'Other'

# The GPX files created by Garmin seem to use the same naming scheme as the underlying FIT files.
GARMIN_GPX_TO_SHYFT = FIT_TO_SHYFT.copy()

STRAVA_GPX_TO_SHYFT = {
    '4': 'hike',
    '9': 'run',
    '10': 'walk',
}

RK_GPX_TO_SHYFT = {
    'Running': 'run',
    'Walking': 'walk',
    'Cycling': 'cycle'
}
