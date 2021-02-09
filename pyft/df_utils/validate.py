"""Some helper functions to verify that various pandas DataFrames
contain the expected data.
"""

from __future__ import annotations
from dataclasses import dataclass, replace, field
from typing import List, Optional, Tuple, Dict

import pandas as pd

_pd_dtype_check_funcs = {
    'datetime': pd.api.types.is_datetime64_any_dtype,
    'float': pd.api.types.is_float_dtype,
    'integer': pd.api.types.is_integer_dtype,
    'number': pd.api.types.is_numeric_dtype,
    'string': pd.api.types.is_string_dtype,
    'timedelta': pd.api.types.is_timedelta64_dtype
}


@dataclass(frozen=True)
class Column:
    name: str
    type: str
    mandatory: bool = True
    nullable: bool = False
    description: Optional[str] = None


@dataclass
class ColumnList:
    _column_list: List[Column]
    # dict mapping column name to index position in _column_list
    _column_index: Dict[str, int] = field(init=False)

    def __post_init__(self):
        self._column_index = {col.name: i for i, col in enumerate(self._column_list)}

    def __getitem__(self, i) -> Column:
        return self._column_list[i]

    def get(self, col_name) -> Optional[Column]:
        try:
            return self[self._column_index[col_name]]
        except KeyError:
            return None

    def replace(self, **replacements) -> ColumnList:
        new_col_list = self._column_list.copy()
        for col_name in replacements:
            new_col_list[self._column_index[col_name]] = replacements[col_name]
        return ColumnList(new_col_list)


@dataclass
class Result:
    is_valid: bool
    missing_mandatory_cols: List[Column]
    missing_optional_cols: List[Column]
    # dict mapping column.name to tuple of (actual dtype, expected type)
    type_mismatched_cols: Dict[Column, Tuple[str, str]]
    bad_null_cols: List[Column]
    extra_col_names: List[str]
    index_name_ok: bool
    index_type_ok: bool


@dataclass
class DataFrameSchema:
    columns: ColumnList
    extra_cols_ok: bool = True
    description: Optional[str] = None
    index_name: Optional[str] = None
    index_type: Optional[str] = None

    def validate_dataframe(self, df: pd.DataFrame) -> Result:
        unchecked_cols = set(df.columns)

        missing_mandatory_cols: List[Column] = []
        missing_optional_cols: List[Column] = []
        type_mismatched_cols: Dict[Column, Tuple[str, str]] = {}
        bad_null_cols: List[Column] = []

        for col in self.columns:
            if col.name not in unchecked_cols:
                if col.mandatory:
                    missing_mandatory_cols.append(col)
                else:
                    missing_optional_cols.append(col)
                continue
            if not _pd_dtype_check_funcs[col.type](df[col.name]):
                if not (col.nullable and df[col.name].isnull().all()):
                    # If a column is all null values, it will likely fail a type check.
                    # That is okay, if the column is nullable.
                    type_mismatched_cols[col] = (df[col.name].dtype, col.type)
            if (not col.nullable) and df[col.name].isnull().any():
                bad_null_cols.append(col)
            unchecked_cols.remove(col.name)

        index_name_ok = (self.index_name is None) or (df.index.name == self.index_name)
        index_type_ok = (self.index_type is None) or _pd_dtype_check_funcs[self.index_type](df.index)

        is_valid = not any((
            missing_mandatory_cols,
            type_mismatched_cols,
            bad_null_cols,
            (not self.extra_cols_ok) and unchecked_cols,
            not index_name_ok,
            not index_type_ok
        ))

        return Result(
            is_valid=is_valid,
            missing_mandatory_cols=missing_mandatory_cols,
            missing_optional_cols=missing_optional_cols,
            type_mismatched_cols=type_mismatched_cols,
            bad_null_cols=bad_null_cols,
            extra_col_names=list(unchecked_cols),
            index_name_ok=index_name_ok,
            index_type_ok=index_type_ok
        )
