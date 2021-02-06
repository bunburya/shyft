"""Some helper functions to verify that various pandas DataFrames
contain the expected data.
"""
from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

check_funcs = {
    'datetime': pd.api.types.is_datetime64_dtype,
    'float': pd.api.types.is_float_dtype,
    'integer': pd.api.types.is_integer_dtype,
    'number': pd.api.types.is_numeric_dtype,
    'string': pd.api.types.is_string_dtype,
    'timedelta': pd.api.types.is_timedelta64_dtype
}


@dataclass
class Column:
    name: str
    type: str
    mandatory: bool = True
    nullable: bool = False
    description: Optional[str] = None


@dataclass
class DataFrameSchema:
    index_name: str
    index_type: str
    columns: List[Column]
    extra_cols_ok: bool = True
    description: Optional[str] = None


@dataclass
class Result:
    is_valid: bool
    missing_mandatory_cols: List[Column]
    missing_optional_cols: List[Column]
    type_mismatched_cols: List[Column]
    bad_null_cols: List[Column]
    extra_col_names: List[str]


def verify_dataframe(df: pd.DataFrame, schema: DataFrameSchema) -> Result:
    unchecked_cols = set(df.columns)

    missing_mandatory_cols = []
    missing_optional_cols = []
    type_mismatched_cols = []
    bad_null_cols = []

    for col in schema.columns:
        if col.name not in unchecked_cols:
            if col.mandatory:
                missing_mandatory_cols.append(col)
            else:
                missing_optional_cols.append(col)
            continue
        if not check_funcs[col.type](df[col.name]):
            type_mismatched_cols.append(col)
        if (not col.nullable) and df[col.name].isnull().any():
            bad_null_cols.append(col)
        unchecked_cols.remove(col.name)

    is_valid = not any((
        missing_mandatory_cols,
        missing_optional_cols,
        type_mismatched_cols,
        bad_null_cols,
        (not schema.extra_cols_ok) and unchecked_cols,
        df.index.name != schema.index_name,
        not check_funcs[schema.index_type](df.index)
    ))

    return Result(
        is_valid,
        missing_mandatory_cols,
        missing_optional_cols,
        type_mismatched_cols,
        bad_null_cols,
        extra_col_names=list(unchecked_cols)
    )
