import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Callable, Tuple, Generator, Dict, Union, List

import fitdecode
import lxml.etree
import numpy as np
import pandas as pd
import pytz
import dateutil.parser as dp
import gpxpy
from gpxpy import gpx
from pyft.config import Config
from pyft.geo_utils import haversine_distance
import logging

# logging.getLogger().setLevel(logging.INFO)



# Error definitions
# TODO: Use these.






