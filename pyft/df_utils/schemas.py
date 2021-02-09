from dataclasses import replace
from pyft.df_utils.validate import DataFrameSchema, Column, ColumnList

points_schema = DataFrameSchema(
    columns=ColumnList([
        Column(
            name='latitude',
            type='float',
            description='The latitude of the point (in degrees).'
        ),
        Column(
            name='longitude',
            type='float',
            description='The longitude of the point (in degrees).'
        ),
        Column(
            name='elevation',
            type='number',
            nullable=True,
            description='The elevation of the point (in metres).'
        ),
        Column(
            name='time',
            type='datetime',
            description='The date and time at which the point was recorded.'
        ),
        Column(
            name='hr',
            type='number',
            nullable=True,
            description='Heart rate.'
        ),
        Column(
            name='cadence',
            type='number',
            nullable=True
        ),
        Column(
            name='step_length_2d',
            type='number',
            nullable=True,
            description='The distance between this point and the previous point.'
        ),
        Column(
            name='cumul_distance_2d',
            type='number',
            nullable=True,
            description='The cumulative distance traveled at this point.'
        ),
        Column(
            name='km',
            type='integer',
            description='The kilometre of the point (ie, the point is in the nth kilometre of the activity).'
        ),
        Column(
            name='mile',
            type='integer',
            description='The mile of the point.'
        ),
        Column(
            name='km_pace',
            type='timedelta',
            nullable=True
        ),
        Column(
            name='mile_pace',
            type='timedelta',
            nullable=True
        ),
        Column(
            name='kmph',
            type='number',
            nullable=True,
            description='Kilometres per hour.'
        ),
        Column(
            name='mph',
            type='number',
            nullable=True,
            description='Miles per hour.'
        ),
        Column(
            name='run_time',
            type='timedelta',
            description='The time of the point, relative to the start of the activity.'
        ),
        Column(
            name='lap',
            type='integer',
            nullable=True,
            description='The lap of the point.'
        )
    ]),
    extra_cols_ok=False,
    index_type='integer',
    description='A DataFrame containing information about the GPS points for an activity.'
)

laps_splits_km_schema = DataFrameSchema(
    columns=ColumnList([
        Column(
            name='start_time',
            type='datetime',
            description='The date and time at which the split/lap started.'
        ),
        Column(
            name='duration',
            type='timedelta',
            description='The duration of the split/lap.'
        ),
        Column(
            name='distance',
            type='number',
            description='The distance of the split/lap.'
        ),
        Column(
            name='mean_kmph',
            type='number',
            description='Average speed over the split/lap in km/h.'
        ),
        Column(
            name='mean_hr',
            type='number',
            nullable=True,
            description='Average heart rate over the split/lap.'
        ),
        Column(
            name='mean_cadence',
            type='number',
            mandatory=False,
            nullable=True,
            description='Average cadence over the split/lap.'
        ),
        Column(
            name='calories',
            type='number',
            mandatory=False,
            nullable=True,
            description='Calories burned during the split/lap.'
        )
    ]),
    extra_cols_ok=False,
    index_type='integer',
    description='A DataFrame containing information summarising the laps or splits of an activity (when the data'
                'is given in kilometres). Index is 1-based.'
)

laps_splits_mile_schema = replace(
    laps_splits_km_schema,
    columns=laps_splits_km_schema.columns.replace(
        mean_kmph=Column(
            name='mean_mph',
            type='number',
            description='Average speed over the split/lap in miles per hour.'
        )
    ),
    description='A DataFrame containing information summarising the laps or splits of an activity (when the data'
                'is given in miles). Index is 1-based.'
)