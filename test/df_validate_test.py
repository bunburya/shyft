import unittest
from datetime import datetime

import pandas as pd

from shyft.df_utils.validate import DataFrameSchema, Column

# Make test schemas
from test.test_common import BaseDataFrameValidateTestCase

TEST_COL_1 = Column(
    name='first_column',
    type='number',
    mandatory=True,
    nullable=False,
    description='A column that is mandatory, numeric and not nullable.'
)

TEST_COL_2 = Column(
    name='second_column',
    type='string',
    mandatory=True,
    nullable=True,
    description='A column that is mandatory, textual and nullable.'
)

TEST_COL_3 = Column(
    name='third_column',
    type='datetime',
    mandatory=False,
    nullable=False,
    description='A column that is optional, consists of datetimes and is not nullable.'
)

TEST_COL_4 = Column(
    name='fourth_column',
    type='timedelta',
    mandatory=False,
    nullable=True,
    description='A column that is optional, consists of timedeltas and is nullable.'
)

TEST_SCHEMA_1 = DataFrameSchema(
    columns=[
        TEST_COL_1,
        TEST_COL_2,
        TEST_COL_3,
        TEST_COL_4
    ],
    index_name='test_index_name_1',
    index_type='integer',
    extra_cols_ok=True,
    description='A schema with an integer index that permits extra columns.'
)

TEST_SCHEMA_2 = DataFrameSchema(
    columns=[
        TEST_COL_1,
        TEST_COL_2,
        TEST_COL_3,
        TEST_COL_4
    ],
    index_name='test_index_name_2',
    index_type='datetime',
    extra_cols_ok=False,
    description='A schema with a datetime index that does not permit extra columns.'
)

TEST_SCHEMA_3 = DataFrameSchema(
    columns=[
        TEST_COL_1,
        TEST_COL_2,
        TEST_COL_3,
    ],
    extra_cols_ok=False,
    description='A schema with three columns that is agnostic as to name and type of index.'
)

# Make test DataFrames

datetimes = []
timedeltas = []
for year in (2013, 2014):
    for month in (2, 4, 6, 8):
        dt = datetime(year=year, month=month, day=1)
        datetimes.append(dt)
        timedeltas.append(datetime.now() - dt)


# Should
# - pass TEST_SCHEMA_1
# - fail TEST_SCHEMA_2 (bad index name and type)
# - fail TEST_SCHEMA_3 (fourth column)
TEST_DF_1 = pd.DataFrame([{
    'test_index_name_1': i,
    'first_column': i + 0.5,  # float
    'second_column': f'test_string_{i}',
    'third_column': datetimes[i],
    'fourth_column': timedeltas[i]
} for i in range(8)]).set_index('test_index_name_1')

# Should
# - fail TEST_SCHEMA_1 (bad index name and type)
# - pass TEST_SCHEMA_2
# - fail TEST_SCHEMA_3 (fourth column)
TEST_DF_2 = pd.DataFrame([{
    'test_index_name_2': datetimes[i],
    'first_column': i + 1,  # int
    'second_column': f'test_string_{i}' if (i % 2) else None,  # ok because Column is nullable
    'third_column': datetimes[i],
    'fourth_column': timedeltas[i]
} for i in range(8)]).set_index('test_index_name_2')

# Should
# - pass TEST_SCHEMA_1
# - fail TEST_SCHEMA_2 (bad index name and type)
# - pass TEST_SCHEMA_3
TEST_DF_3 = pd.DataFrame([{
    'test_index_name_1': i,
    'first_column': i + 0.5,
    'second_column': f'test_string_{i}',
    'third_column': datetimes[i]
} for i in range(8)]).set_index('test_index_name_1')

# Should fail all schemes for lack of mandatory column (and, in the case of TEST_SCHEMA_2, also bad index)
TEST_DF_4 = pd.DataFrame([{
    'test_index_name_1': i,
    'second_column': f'test_string_{i}',
    'third_column': datetimes[i],
} for i in range(8)]).set_index('test_index_name_1')

# Should fail all schemas for null values in first column (and, in the case of TEST_SCHEMA_2, also bad index)
TEST_DF_5 = pd.DataFrame([{
    'test_index_name_1': i,
    'first_column': i + 0.5 if (i % 2) else None,
    'second_column': f'test_string_{i}',
    'third_column': datetimes[i],
} for i in range(8)]).set_index('test_index_name_1')

class ValidateDataFrameTestCase(BaseDataFrameValidateTestCase):

    # TODO: Test ColumnList and copying.

    def test_df_01(self):
        """TEST_DF_1"""
        self.assert_dataframe_valid(TEST_DF_1, TEST_SCHEMA_1)
        self.assert_dataframe_invalid(TEST_DF_1, TEST_SCHEMA_2)
        self.assert_dataframe_invalid(TEST_DF_1, TEST_SCHEMA_3)

    def test_df_02(self):
        """TEST_DF_2"""
        self.assert_dataframe_invalid(TEST_DF_2, TEST_SCHEMA_1)
        self.assert_dataframe_valid(TEST_DF_2, TEST_SCHEMA_2)
        self.assert_dataframe_invalid(TEST_DF_2, TEST_SCHEMA_3)

    def test_df_03(self):
        """TEST_DF_3"""
        self.assert_dataframe_valid(TEST_DF_3, TEST_SCHEMA_1)
        self.assert_dataframe_invalid(TEST_DF_3, TEST_SCHEMA_2)
        self.assert_dataframe_valid(TEST_DF_3, TEST_SCHEMA_3)

    def test_df_04(self):
        """TEST_DF_4"""
        self.assert_dataframe_invalid(TEST_DF_4, TEST_SCHEMA_1)
        self.assert_dataframe_invalid(TEST_DF_4, TEST_SCHEMA_2)
        self.assert_dataframe_invalid(TEST_DF_4, TEST_SCHEMA_3)

    def test_df_05(self):
        """TEST_DF_5"""
        self.assert_dataframe_invalid(TEST_DF_5, TEST_SCHEMA_1)
        self.assert_dataframe_invalid(TEST_DF_5, TEST_SCHEMA_2)
        self.assert_dataframe_invalid(TEST_DF_5, TEST_SCHEMA_3)


if __name__ == '__main__':
    unittest.main()
