# -*- coding: utf-8 -*- --------------------------------------------------===#
#
#  Copyright 2022-2026 Trovares Inc. dba Rocketgraph.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#===----------------------------------------------------------------------===#

"""Tests for the parts of the ODBC drivers that need no database.

The queries each driver issues and the type mappings it applies are decided
without talking to anything, so they can be checked for every supported
database rather than only for the one CI can run. Only the schema queries reach
out, and those are answered here with a stand in, which leaves the query text
and the handling of the schema under test.
"""

import unittest
import pyarrow as pa
import xgt

import xgt_connector.odbc as odbc
from xgt_connector import (SQLODBCDriver, MongoODBCDriver, OracleODBCDriver,
                           SAPODBCDriver, SnowflakeODBCDriver)

CONNECTION = 'Driver={Fake};Server=127.0.0.1;Uid=test;Pwd=foo;'

class _FakeReader():
  def __init__(self, schema):
    self.schema = schema

class _RecordingOdbc():
  """Stands in for read_arrow_batches_from_odbc, recording what it was asked."""
  def __init__(self, schema):
    self._schema = schema
    self.queries = []
    self.kwargs = []

  def __call__(self, query, connection_string, batch_size = None, **kwargs):
    self.queries.append(query)
    self.kwargs.append(dict(kwargs, batch_size = batch_size,
                            connection_string = connection_string))
    return _FakeReader(self._schema)

class TestPyarrowToXgtTypes(unittest.TestCase):
  def test_types_map_to_xgt(self):
    cases = [
        (pa.bool_(), xgt.BOOLEAN),
        (pa.int8(), xgt.INT), (pa.int16(), xgt.INT),
        (pa.int32(), xgt.INT), (pa.int64(), xgt.INT),
        (pa.uint32(), xgt.INT),
        (pa.float32(), xgt.FLOAT), (pa.float64(), xgt.FLOAT),
        (pa.decimal128(38, 0), xgt.FLOAT),
        (pa.string(), xgt.TEXT),
        (pa.date32(), xgt.DATE),
        (pa.date64(), xgt.DATETIME),
        (pa.timestamp('us'), xgt.DATETIME),
        (pa.time64('us'), xgt.TIME),
    ]
    for pyarrow_type, expected in cases:
      assert odbc._pyarrow_type_to_xgt_type(pyarrow_type) == expected, pyarrow_type

  def test_unsupported_type_raises(self):
    for pyarrow_type in [pa.binary(), pa.list_(pa.int64()), pa.null()]:
      with self.assertRaises(xgt.XgtTypeError):
        odbc._pyarrow_type_to_xgt_type(pyarrow_type)

  def test_conversions_are_applied_before_mapping(self):
    schema = pa.schema([('a', pa.decimal128(38, 0)), ('b', pa.string())])
    # Without a conversion a Number(38,0) is a float in xGT.
    assert odbc._infer_xgt_schema_from_pyarrow_schema(schema, { }) == \
        [['a', xgt.FLOAT], ['b', xgt.TEXT]]
    # The ansi conversion of the Oracle and Snowflake drivers makes it an int.
    conversions = { pa.decimal128(38, 0) : pa.int64() }
    assert odbc._infer_xgt_schema_from_pyarrow_schema(schema, conversions) == \
        [['a', xgt.INT], ['b', xgt.TEXT]]

  def test_conversion_of_another_precision_is_left_alone(self):
    # Only the exact type converts, a Number(38,2) is still a float.
    schema = pa.schema([('a', pa.decimal128(38, 2))])
    conversions = { pa.decimal128(38, 0) : pa.int64() }
    assert odbc._infer_xgt_schema_from_pyarrow_schema(schema, conversions) == \
        [['a', xgt.FLOAT]]

class TestDriverQueries(unittest.TestCase):
  SCHEMA = pa.schema([('_id', pa.string()), ('num', pa.int64()),
                      ('name', pa.string())])

  def setUp(self):
    self._original = odbc.read_arrow_batches_from_odbc
    self.recorder = _RecordingOdbc(self.SCHEMA)
    odbc.read_arrow_batches_from_odbc = self.recorder

  def tearDown(self):
    odbc.read_arrow_batches_from_odbc = self._original

  def _schema_query_of(self, driver, table = 'people'):
    driver._get_record_batch_schema(table, None, None)
    assert len(self.recorder.queries) == 1, self.recorder.queries
    return self.recorder.queries[0]

  def test_sql_queries(self):
    driver = SQLODBCDriver(CONNECTION)
    assert driver._get_data_query('people', self.SCHEMA) == 'SELECT * FROM people;'
    assert self._schema_query_of(driver) == 'SELECT * FROM people LIMIT 1;'
    assert driver._conversions() == { }

  def test_sap_uses_top_rather_than_limit(self):
    driver = SAPODBCDriver(CONNECTION)
    assert driver._get_data_query('people', self.SCHEMA) == 'SELECT * FROM people;'
    assert self._schema_query_of(driver) == 'SELECT TOP 1 * FROM people;'
    assert driver._conversions() == { }

  def test_oracle_quotes_names_unless_upper_cased(self):
    driver = OracleODBCDriver(CONNECTION)
    assert driver._get_data_query('people', self.SCHEMA) == 'SELECT * FROM "people"'
    assert self._schema_query_of(driver) == 'SELECT * FROM "people" WHERE ROWNUM <= 1'

  def test_oracle_upper_case_names_drops_the_quotes(self):
    driver = OracleODBCDriver(CONNECTION, upper_case_names = True)
    assert driver._get_data_query('PEOPLE', self.SCHEMA) == 'SELECT * FROM PEOPLE'
    assert self._schema_query_of(driver, 'PEOPLE') == \
        'SELECT * FROM PEOPLE WHERE ROWNUM <= 1'

  def test_oracle_ansi_conversion(self):
    assert OracleODBCDriver(CONNECTION)._conversions() == \
        { pa.decimal128(38, 0) : pa.int64() }
    assert OracleODBCDriver(CONNECTION, ansi_conversion = False)._conversions() == { }

  def test_snowflake_ansi_conversion(self):
    driver = SnowflakeODBCDriver(CONNECTION)
    assert driver._get_data_query('people', self.SCHEMA) == 'SELECT * FROM people;'
    assert self._schema_query_of(driver) == 'SELECT * FROM people LIMIT 1;'
    assert driver._conversions() == { pa.decimal128(38, 0) : pa.int64() }
    assert SnowflakeODBCDriver(CONNECTION, ansi_conversion = False)._conversions() == { }

  def test_mongo_names_the_columns_it_wants(self):
    # Mongo is asked for named columns so that the id can be left out.
    driver = MongoODBCDriver(CONNECTION)
    schema = pa.schema([('num', pa.int64()), ('name', pa.string())])
    assert driver._get_data_query('people', schema) == 'SELECT num,name FROM people;'
    assert self._schema_query_of(driver) == 'SELECT * FROM people LIMIT 1;'
    assert driver._conversions() == { }

  def test_mongo_drops_the_id_column_by_default(self):
    driver = MongoODBCDriver(CONNECTION)
    schema = driver._get_record_batch_schema('people', None, None)
    assert schema.names == ['num', 'name']

  def test_mongo_keeps_the_id_column_when_asked(self):
    driver = MongoODBCDriver(CONNECTION, include_id = True)
    schema = driver._get_record_batch_schema('people', None, None)
    assert schema.names == ['_id', 'num', 'name']

  def test_size_limits_are_passed_through(self):
    driver = SQLODBCDriver(CONNECTION)
    driver._get_record_batch_schema('people', 1024, 2048)
    passed = self.recorder.kwargs[0]
    assert passed['max_text_size'] == 1024
    assert passed['max_binary_size'] == 2048
    assert passed['connection_string'] == CONNECTION

class TestEstimateQueries(unittest.TestCase):
  def test_every_driver_has_a_row_estimate_query(self):
    drivers = [SQLODBCDriver(CONNECTION), MongoODBCDriver(CONNECTION),
               OracleODBCDriver(CONNECTION), SAPODBCDriver(CONNECTION),
               SnowflakeODBCDriver(CONNECTION)]
    for driver in drivers:
      query = driver._estimate_query.format('people')
      assert 'people' in query, (driver, query)
      assert query.lower().startswith('select'), (driver, query)

  def test_oracle_estimates_from_all_tables(self):
    # Oracle has no INFORMATION_SCHEMA, it uses ALL_TABLES instead.
    query = OracleODBCDriver(CONNECTION)._estimate_query.format('PEOPLE')
    assert query == "SELECT NUM_ROWS FROM ALL_TABLES WHERE TABLE_NAME = 'PEOPLE'"
