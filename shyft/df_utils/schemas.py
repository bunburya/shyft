from dataclasses import replace
from shyft.df_utils.validate import DataFrameSchema, Column, ColumnList
from shyft.metadata import APP_NAME

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

metadata_summary_schema = DataFrameSchema(
    columns=ColumnList([
        Column(
            name='activity_id',
            type='integer',
            description='An integer index for the activity.'
        ),
        Column(
            name='activity_type',
            type='string',
            description='The type of the activity.'
        ),
        Column(
            name='name',
            type='string',
            description='The name of the activity',
            mandatory=False,
            nullable=True
        ),
        Column(
            name='description',
            type='string',
            description='A description of the activity',
            mandatory=False,
            nullable=True
        ),
        Column(
            name='gpx_file',
            type='string',
            description=f'A path to the GPX file generated by {APP_NAME} for the activity. '
                        'Does not guarantee that the file exists.',
            mandatory=False,
            nullable=True
        ),
        Column(
            name='tcx_file',
            type='string',
            description=f'A path to the TCX file generated by {APP_NAME} for the activity. '
                        'Does not guarantee that the file exists.',
            mandatory=False,
            nullable=True
        ),
        Column(
            name='source_file',
            type='string',
            description=f'A path to the source file used by {APP_NAME} to generate the activity '
                        f'(eg, the TCX, GPX or FIT file).',
            mandatory=False,
            nullable=True
        ),
        Column(
            name='source_format',
            type='string',
            description=f'The format of the source file, eg, TCX, GPX or FIT.',
            mandatory=False,
            nullable=True
        ),
        Column(
            name='date_time',
            type='datetime',
            description='The date and time of the activity.',
        ),
        Column(
            name='distance_2d_km',
            type='number',
            description='The distance of the activity in kilometres (excluding elevation).',
        ),
        Column(
            name='center_lat',
            type='number',
            description='The latitude of the point that is the center of all the recorded points of the activity.',
        ),
        Column(
            name='center_lon',
            type='number',
            description='The longitude of the point that is the center of all the recorded points of the activity.',
        ),
        Column(
            name='center_elev',
            type='number',
            description='The elevation of the point that is the center of all the recorded points of the activity.',
        ),
        # NOTE: points_std?
        Column(
            name='duration',
            type='timedelta',
            description='The duration of the activity.',
        ),
        Column(
            name='prototype_id',
            type='integer',
            description='The ID of the activity that is this activity\'s prototype for route matching purposes.'
        ),
        Column(
            name='thumbnail_file',
            type='string',
            description=f'A path to the PNG file containing a thumbnail representation of the activity. '
                        'Does not guarantee that the file exists.',
            mandatory=False,
            nullable=True
        ),
        Column(
            name='distance_2d_mile',
            type='number',
            description='The distance of the activity in miles (excluding elevation).'
        ),
        Column(
            name='mean_kmph',
            type='number',
            description='The average speed during the activity, in kilometres per hour.'
        ),
        Column(
            name='mean_km_pace',
            type='timedelta',
            description='The average kilometre pace (minutes per km) of the activity.'
        ),
        Column(
            name='mean_mile_pace',
            type='timedelta',
            description='The average mile pace (minutes per mile) of the activity.'
        ),
        Column(
            name='mean_mph',
            type='number',
            description='The average speed during the activity, in miles per hour.'
        ),
        Column(
            name='day',
            type='string',
            description='The day of the week on which the activity took place, as a string.'
        ),
        Column(
            name='hour',
            type='integer',
            description='The hour of the day in which the activity began, as an integer.'
        ),
        Column(
            name='month',
            type='integer',
            description='The month in which the activity took place, as an integer.'
        ),
        Column(
            name='mean_hr',
            type='number',
            description='The average recorded heart rate over the course of the activity (beats per minute).',
            mandatory=False,
            nullable=True
        ),
        Column(
            name='mean_cadence',
            type='number',
            description='The average recorded cadence over the course of the activity.',
            mandatory=False,
            nullable=True
        ),
        Column(
            name='calories',
            type='number',
            description='The total recorded calories burned during the activity.',
            mandatory=False,
            nullable=True
        )
    ]),
    extra_cols_ok=True,
    index_type='integer',
    description='A DataFrame where each row represents an activity and includes summary information about that activity'
                'taken from the relevant ActivityMetaData object.'
)

metadata_time_series_schema = DataFrameSchema(
    columns=ColumnList([
        Column(
            name='activity_count',
            type='integer',
            description='The number of activities recorded in the relevant time period.'
        ),
        Column(
            name='total_duration',
            type='timedelta',
            description='The total duration of all activities.'
        ),
        Column(
            name='total_distance_2d_km',
            type='number',
            description='The total distance moved over all activities, in kilometres, ignoring elevation.'
        ),
        Column(
            name='total_distance_2d_mile',
            type='number',
            description='The total distance moved over all activities, in miles, ignoring elevation.'
        ),
        Column(
            name='mean_kmph',
            type='number',
            description='Simple average speed in kilometres per hour.'
        ),
        Column(
            name='mean_mph',
            type='number',
            description='Simple average speed in miles per hour.'
        ),
        Column(
            name='mean_hr',
            type='number',
            description='Simple average heart rate in beats per minute.',
            mandatory=False,
            nullable=True
        ),
        Column(
            name='mean_cadence',
            type='number',
            description='Simple average cadence.',
            mandatory=False,
            nullable=True
        )
    ]),
    index_type='datetime',
    description='A DataFrame where each row contains aggregate information about all the activities in a give'
                'time period.'
)