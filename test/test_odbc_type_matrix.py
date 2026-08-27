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

"""What each database's types become in xGT, one table per database.

The type a column arrives as depends on what the ODBC driver reports, which
differs between databases for the same logical type. A boolean is a good
example: sqlite reports it as a boolean, MariaDB as an integer and PostgreSQL
as text. Those differences are what breaks when the ODBC layer is upgraded, and
they are invisible when only one database is tested.

Every database that cannot be reached is skipped, so this runs with whatever is
available. Sqlite needs no server at all and so always runs.
"""

import os
import tempfile
import unittest
from datetime import date, datetime

import pyodbc
import xgt
from parameterized import parameterized_class

from xgt_connector import (ODBCConnector, SQLODBCDriver, SQLServerODBCDriver,
                           OracleODBCDriver)

_SQLITE_FILE = os.path.join(tempfile.mkdtemp(), 'type_matrix.db')

# Each entry is a database, the table to build in it, and what that table is
# expected to become in xGT. The expectations differ on purpose.
DATABASES = [
  {
    'name' : 'sqlite',
    'driver' : 'sql',
    'connection' : f'Driver={{SQLite3}};Database={_SQLITE_FILE};',
    'ddl' : ('CREATE TABLE matrix (b BOOLEAN, i INTEGER, f REAL, s TEXT, '
             'd DATE, t TIME, ts DATETIME)'),
    'insert' : ("INSERT INTO matrix VALUES (1, 42, 1.5, 'hello', '1989-05-06', "
                "'12:56:34', '1989-05-06 12:56:34')"),
    'xgt_types' : ['boolean', 'int', 'float', 'text', 'date', 'text', 'datetime'],
    'first_row' : [True, 42, 1.5, 'hello', date(1989, 5, 6), '12:56:34',
                   datetime(1989, 5, 6, 12, 56, 34)],
  },
  {
    'name' : 'mariadb',
    'driver' : 'sql',
    'connection' : ('Driver={MariaDB};Server=127.0.0.1;Port=3306;Database=test;'
                    'Uid=test;Pwd=foo;'),
    'ddl' : ('CREATE TABLE matrix (b BOOL, i BIGINT, f DOUBLE, s VARCHAR(64), '
             'd DATE, t TIME, ts DATETIME)'),
    'insert' : ("INSERT INTO matrix VALUES (1, 42, 1.5, 'hello', '1989-05-06', "
                "'12:56:34', '1989-05-06 12:56:34')"),
    # MariaDB has no boolean of its own, BOOL is a tinyint.
    'xgt_types' : ['int', 'int', 'float', 'text', 'date', 'text', 'datetime'],
    'first_row' : [1, 42, 1.5, 'hello', date(1989, 5, 6), '12:56:34',
                   datetime(1989, 5, 6, 12, 56, 34)],
  },
  {
    'name' : 'postgres',
    'driver' : 'sql',
    'connection' : ('Driver={PostgreSQL Unicode};Server=127.0.0.1;Port=5432;'
                    'Database=test;Uid=test;Pwd=foo;'),
    'ddl' : ('CREATE TABLE matrix (b BOOLEAN, i BIGINT, f DOUBLE PRECISION, '
             's VARCHAR(64), d DATE, t TIME, ts TIMESTAMP)'),
    'insert' : ("INSERT INTO matrix VALUES (true, 42, 1.5, 'hello', '1989-05-06', "
                "'12:56:34', '1989-05-06 12:56:34')"),
    # The PostgreSQL driver hands its boolean over as text rather than a boolean.
    'xgt_types' : ['text', 'int', 'float', 'text', 'date', 'text', 'datetime'],
    'first_row' : ['1', 42, 1.5, 'hello', date(1989, 5, 6), '12:56:34',
                   datetime(1989, 5, 6, 12, 56, 34)],
  },
  {
    'name' : 'sqlserver',
    'connection' : ('Driver={ODBC Driver 18 for SQL Server};Server=127.0.0.1,1433;'
                    'UID=sa;PWD=Str0ng!Passw0rd;TrustServerCertificate=yes;Database=master;'),
    'driver' : 'sqlserver',
    'ddl' : ('CREATE TABLE matrix (b BIT, i BIGINT, f FLOAT, s VARCHAR(64), '
             'd DATE, t TIME, ts DATETIME2)'),
    'insert' : ("INSERT INTO matrix VALUES (1, 42, 1.5, 'hello', '1989-05-06', "
                "'12:56:34', '1989-05-06 12:56:34')"),
    # A SQL Server TIME carries seven fractional digits, and arrives with them.
    'xgt_types' : ['boolean', 'int', 'float', 'text', 'date', 'text', 'datetime'],
    'first_row' : [True, 42, 1.5, 'hello', date(1989, 5, 6), '12:56:34.0000000',
                   datetime(1989, 5, 6, 12, 56, 34)],
  },
  {
    'name' : 'oracle',
    'driver' : 'oracle',
    'connection' : 'Driver={Oracle};DBQ=127.0.0.1:1521/FREEPDB1;UID=system;PWD=test;',
    # Oracle has no boolean and no time of day on its own, and its DATE carries
    # a time, so this table is shaped differently from the others.
    'ddl' : ('CREATE TABLE matrix (b NUMBER(1), i NUMBER(38,0), f BINARY_DOUBLE, '
             's VARCHAR2(64), d DATE, ts TIMESTAMP)'),
    'insert' : ("INSERT INTO matrix VALUES (1, 42, 1.5, 'hello', "
                "DATE '1989-05-06', TIMESTAMP '1989-05-06 12:56:34')"),
    # Only a NUMBER(38,0) converts to an int, a NUMBER(1) stays a float.
    'xgt_types' : ['float', 'int', 'float', 'text', 'datetime', 'datetime'],
    'first_row' : [1.0, 42, 1.5, 'hello', datetime(1989, 5, 6, 0, 0),
                   datetime(1989, 5, 6, 12, 56, 34)],
  },
  {
    'name' : 'db2',
    'driver' : 'sql',
    'connection' : ('Driver={Db2};Hostname=127.0.0.1;Port=50000;Database=testdb;'
                    'UID=db2inst1;PWD=passw0rd;Protocol=TCPIP;'),
    'ddl' : ('CREATE TABLE matrix (b SMALLINT, i BIGINT, f DOUBLE, s VARCHAR(64), '
             'd DATE, ts TIMESTAMP)'),
    'insert' : ("INSERT INTO matrix VALUES (1, 42, 1.5, 'hello', '1989-05-06', "
                "'1989-05-06 12:56:34')"),
    'xgt_types' : ['int', 'int', 'float', 'text', 'date', 'datetime'],
    'first_row' : [1, 42, 1.5, 'hello', date(1989, 5, 6),
                   datetime(1989, 5, 6, 12, 56, 34)],
  },
]

@parameterized_class(DATABASES)
class TestODBCTypeMatrix(unittest.TestCase):
  maxDiff = None

  @classmethod
  def setup_class(cls):
    try:
      cls.odbc = pyodbc.connect(cls.connection, autocommit = True)
    except Exception as e:
      raise unittest.SkipTest(f'{cls.name} not reachable over ODBC: {e}')
    cls.xgt = xgt.Connection()
    try:
      cls.xgt.create_namespace('matrix')
    except Exception:
      pass
    cls.xgt.set_default_namespace('matrix')
    if cls.driver == 'sqlserver':
      odbc_driver = SQLServerODBCDriver(cls.connection)
    elif cls.driver == 'oracle':
      odbc_driver = OracleODBCDriver(cls.connection, upper_case_names = True)
    else:
      odbc_driver = SQLODBCDriver(cls.connection)
    cls.conn = ODBCConnector(cls.xgt, odbc_driver)

  @classmethod
  def teardown_class(cls):
    cursor = cls.odbc.cursor()
    try:
      cursor.execute('DROP TABLE matrix')
    except Exception:
      pass
    cls.xgt.drop_namespace('matrix', force_drop = True)

  def setup_method(self, method):
    cursor = self.odbc.cursor()
    try:
      cursor.execute('DROP TABLE matrix')
    except Exception:
      pass
    cursor.execute(self.ddl)
    cursor.execute(self.insert)
    # A row of nulls, which is where drivers most often differ.
    nulls = ','.join(['NULL'] * len(self.xgt_types))
    cursor.execute(f'INSERT INTO matrix VALUES ({nulls})')
    try:
      self.xgt.drop_frame('matrix')
    except Exception:
      pass

  def test_types_arrive_as_expected(self):
    schemas = self.conn.get_xgt_schemas(tables = ['matrix'])
    types = [type for _name, type in schemas['tables']['matrix']['xgt_schema']]
    assert types == self.xgt_types, (self.name, types)

  def test_values_round_trip(self):
    self.conn.transfer_to_xgt(tables = ['matrix'])
    frame = self.xgt.get_frame('matrix')
    assert frame.num_rows == 2
    rows = sorted(frame.get_data(), key = lambda row: row[0] is None)
    assert rows[0] == self.first_row, (self.name, rows[0])

  def test_nulls_survive(self):
    self.conn.transfer_to_xgt(tables = ['matrix'])
    rows = self.xgt.get_frame('matrix').get_data()
    nulls = [row for row in rows if all(value is None for value in row)]
    assert len(nulls) == 1, (self.name, rows)
