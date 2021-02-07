from pyft.df_utils.validate import DataFrameSchema, Column

LAPS_OR_SPLITS = DataFrameSchema(
    columns=[
        Column(
            name='start_time',
            type='datetime',
            mandatory=True,
            nullable=False,
            description='The date and time at which the split/lap started.'
        ),
        Column(
            name='duration',
            type='timedelta',
            mandatory=True,
            nullable=False,
            description='The duration of the split/lap.'
        ),
        Column(
            name='distance',
            type='number',
            mandatory=True,
            nullable=False,
            description='The distance of the split/lap.'
        ),
        Column(
            name='mean_hr',
            type='number',
            mandatory=False,
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
    ],
    extra_cols_ok=True,
    index_type='integer',
    description='A DataFrame containing information summarising the laps or splits of an activity.'
)