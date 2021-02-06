import unittest

import pandas as pd

# Schemas
from pyft.df_utils.validate import DataFrameSchema, Column

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
    index_name='test_index_name_1',
    index_type='integer',
    columns=[
        TEST_COL_1,
        TEST_COL_2,
        TEST_COL_3,
        TEST_COL_4
    ],
    extra_cols_ok=True,
    description='A schema with an integer index that permits extra columns.'
)

TEST_SCHEMA_2 = DataFrameSchema(
    index_name='test_index_name_2',
    index_type='datetime',
    columns=[
        TEST_COL_1,
        TEST_COL_2,
        TEST_COL_3,
        TEST_COL_4
    ],
    extra_cols_ok=False,
    description='A schema with a datetime index that does not permit extra columns.'
)

class ValidateDataFrameTestCase(unittest.TestCase):
    def test_something(self):
        self.assertEqual(True, False)


if __name__ == '__main__':
    unittest.main()
