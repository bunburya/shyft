# DataFrames

This section describes the format of the various pandas DataFrames that are associated with an Activity.

## Lap or split information

Each Activity can generate a DataFrame summarising its mile or kilometre splits (`activity.get_split_summary('km')` or
`activity.get_split_summary('mile')`).