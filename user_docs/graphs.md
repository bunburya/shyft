# Customising graphs

The graphs displayed for activities and in the activity overview page can be customised through two files, `activity_graphs.json` and `overview_graphs.json`.  Eventually Shyft will allow users to customise graphs through the web interface, but for now, this file describes how to customise the JSON files.

## Activity graphs

`activity_graphs.json` describes the graphs to be displayed in respect of a single activity.  The structure of the JSON file is a list of JSON objects, each of which describes one graph.  Most of the the key-value pairs in the JSON object are just passed as arguments to the relevant `plotly.express` factory function, and so the necessary ones will depend on the type of graph being constructed.  However, the common important ones are:

- `data_source`: Specifies where the data for the graph will come from.  Must be one of three values:
  - `points`:  The graph data will be taken from the DataFrame containing the GPX points for the activity.
  - `km_splits`:  The graph data will be taken from the DataFrame summarising the kilometre splits for the activity.
  - `mile_splits`:  Similar to `km_splits`.  
- `graph_type`: Specifies the type of graph.  Must correspond to one of the factory functions in `plotly.express` (eg, `bar`, `line`, `scatter`, etc).
- `x`: Specifies the data to be displayed on the x axis. 
  - If `data_source` is `points`, must correspond to an attribute of an `ActivityMetadata` instance.
  - If `data_source` is `km_splits` or `mile_splits`, must correspond to the name of a column of the relevant DataFrame.If `null`, the data used for the x axis will be the index of the relevant dataframe.
- `y`: Specifies the data to be displayed on the y axis.  Permitted values are the same as for `x`.

You can also provide other key-value pairs that will be passed as additional arguments to the relevant `plotly.express` function.  A common one is `title`.

## Overview graphs

`overview_graphs.json` describes the graphs to be displayed on the overview page.  Again, the structure of the JSON file is a list of JSON objects, each of which describes one graph.  The most important keys in each such object are:

- `graph_type`: As above.
- `x`: Specifies the data to be displayed on the x axis. Must correspond to the name of a column of the DataFrame output by the `summarize_activity_data` method of an `ActivityManager` instance. If the `agg` argument is provided (see below), the DataFrame will be grouped by the data specified by `x`. If `null`, the data used for the x axis will be the index of the relevant dataframe.
- `y`: Specifies the data to be displayed on the y axis.
- `groupby`: Optional. If provided, the DataFrame summarising the activities will be grouped by the specified column. `agg` must also be provided or else this will do nothing.
- `agg`: Must be provided if `groupby` is provided (and does nothing if `groupby` is not provided).  If provided, must correspond to an attribute of a `DataFrameGroupBy` (eg,`count`, `mean`).