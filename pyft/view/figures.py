from typing import Sequence, Any, Optional, Iterable

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_table as dt
from pyft.single_activity import ActivityMetaData


def get_map_figure(df: pd.DataFrame, highlight_col: Optional[str] = None,
                   highlight_vals: Optional[Sequence[Any]] = None, **kwargs) -> go.Figure:
    fig = px.line_mapbox(df, lat="latitude", lon="longitude", zoom=11, **kwargs)
    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    if highlight_col and highlight_vals:
        for v in highlight_vals:
            data = df[df[highlight_col] == v]
            fig.add_trace(go.Scattermapbox(
                mode='lines',
                lat=data['latitude'],
                lon=data['longitude'],
                marker={'color': 'red'}
            ))
    return fig


def get_splits_dt(id: str, df: pd.DataFrame, **kwargs) -> dt.DataTable:
    df = df['time'].reset_index()
    df['km'] += 1
    df['time'] = df['time'].astype(str).str.split(' ').str[-1]
    cols = [{'name': i, 'id': i} for i in df.columns]
    data = df.to_dict('records')
    return dt.DataTable(
        id=id,
        columns=cols,
        data=data,
        # The below CSS is required so that the DataTable isn't cropped on the left side.
        # https://github.com/facultyai/dash-bootstrap-components/issues/334
        css=[{'selector': '.row', 'rule': 'margin: 0'}],
        row_selectable='multi',
        selected_rows=[],
        **kwargs
    )


ACTIVITY_TABLE_COLS = [
    {'id': 'thumb', 'name': '', 'presentation': 'markdown'},
    {'id': 'name', 'name': 'Activity', 'presentation': 'markdown'},
    {'id': 'date', 'name': 'Date', 'type': 'datetime'},
    {'id': 'dist', 'name': 'Distance', 'type': 'numeric'}
]


def get_activities_table(activities: Iterable[ActivityMetaData], **kwargs) -> dt.DataTable:
    data = [{
        'thumb': f'![]({a.thumbnail_file})',
        'name': f'{a.name}',
        'date': f'{a.date_time}',
        'dist': f'{a.distance_2d}'
    } for a in activities]
    return dt.DataTable(columns=ACTIVITY_TABLE_COLS, data=data, **kwargs)
