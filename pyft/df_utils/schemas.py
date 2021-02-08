from pyft.df_utils.validate import DataFrameSchema, Column

POINTS = DataFrameSchema(
    columns=[
        Column(
            name='activity_id',
            type='integer',
            description='The ID of the relevant Activity.'
        ),
        Column(
            name='point_no',
            type='integer',
            description='The number/index of the point within the Activity.'
        ),
        Column(
            name='track_no',
            type='integer',
            description='The number/index of the track to which the point belongs. Mainly relevant to GPX files.'
        )
    ]
)

LAPS_OR_SPLITS = DataFrameSchema(
    columns=[
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
            name='mean_hr',
            type='number',
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
    ],
    extra_cols_ok=True,
    index_type='integer',
    description='A DataFrame containing information summarising the laps or splits of an activity.'
)