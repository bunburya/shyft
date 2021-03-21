"""Classes and functions to help with converting Shyft objects to and
from JSON.
"""

import json
import datetime

import numpy as np

# https://stackoverflow.com/questions/12122007/python-json-encoder-to-support-datetime

class ShyftJSONEncoder(json.JSONEncoder):

    """A custom JSON encoder that can handle complex datatypes that are
    found in Shyft objects.
    """

    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
            # Convert datetime and similar objects to ISO 8601-formatted strings
            return obj.isoformat()
        elif isinstance(obj, datetime.timedelta):
            # Convert timedelta objects to seconds
            return obj.total_seconds()
        elif isinstance(obj, np.ndarray):
            # Convert NumPy arrays to lists
            return obj.tolist()

        return super(ShyftJSONEncoder, self).default(obj)
