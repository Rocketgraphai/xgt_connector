..
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

.. role:: nocap
   :class: nocap

.. |xgt| replace:: :nocap:`xGT`

.. _odbc:

ODBC Connector
==============

The extra ODBC connector module allows for connecting to databases that support ODBC.
The ODBC connector requires at least xGT 1.14.0.

The ODBC driver has been tested against Databricks, DB2, MySQL, MariaDB, Oracle, Snowflake, SAP ASE, and SAP IQ.
The driver regularly runs unit tests against MariaDB.
Some SQL specific drivers are available below for Oracle, Snowflake and SAP-based databases.
In general, SQL syntax varies between vendors, so transfer_to_xgt or transfer_to_odbc aren't guaranteed to work.
However, transfer_query_to_xgt will likely work with any vendor using the generic SQLODBCDriver.

Installation
------------

You can install the connector with dependencies for ODBC by executing this command:

.. code-block:: bash

   python -m pip install 'xgt_connector[odbc]'

.. _mapping-sql-label:

Mapping SQL Tables to Graphs
----------------------------

When transferring a table from SQL to xGT, the data must be mapped onto vertices and edge frames or as stand alone tables.

- **Vertices**: Use a key to connect edges.
- **Edges**: Use source and target keys from the edge row, along with a frame identifier, to connect to a specific row in the vertex frame.
- **Table**: Similar to an SQL table: does not connect with other frames.

When mapping a SQL table using the connector API, there are two ways to map data:

1. **Name to dictionary**
2. **Name to shorthand tuple**

Mappings are provided in tuple form to allow multiple types to be transferred in one call. These mappings take the forms:

- ``(SQL_TABLE, DICTIONARY)``
- ``(SQL_TABLE, [XGT_FRAME], [TUPLE])``

For multiple tables, an array of mappings is used. While dictionary mapping is more verbose, it offers clarity, especially for beginners, because all parameter names must be explicitly defined.

Dictionary Mapping
^^^^^^^^^^^^^^^^^^

In dictionary mappings, the type is determined by the keys provided. Available keys are:

- ``frame``
- ``key``
- ``source``
- ``target``
- ``source_key``
- ``target_key``

If the frame name is the same as the SQL table name, the frame key can be omitted.

- **Table types** may have ``frame``.
- **Vertex types** may have ``frame`` and require ``key``.
- **Edge types** may have ``frame`` and require ``source``, ``target``, ``source_key``, and ``target_key``.

Only these combinations are valid.

Dictionary Mapping Examples
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

  # Mapping a SQL table to an xGT table:
  ('sql_table_name', {'frame': 'xgt_table_name'})

  # Mapping a SQL table to an xGT vertex (key is a column in the xgt_vertex_user frame):
  ('sql_table_name', {'frame': 'xgt_vertex_user', 'key': 'username'})

  # Mapping a SQL table to a different xGT vertex (key is a column in the xgt_vertex_login frame):
  ('sql_different_table_name', {'frame': 'xgt_vertex_login', 'key': 'ip_address'})

  # Mapping a SQL table to an xGT edge (source_key and target_key are columns in the xgt_edge_connection frame):
  ('sql_table_name', {'frame': 'xgt_edge_connection', 'source': 'xgt_vertex_user', 'target': 'xgt_vertex_login', 'source_key': 'user_column', 'target_key': 'ip_column'})

Note that for the edge frame, ``source`` and ``target`` refer to vertex frame names, not columns within the frame.

Shorthand Tuple Mapping
^^^^^^^^^^^^^^^^^^^^^^^

To reduce verbosity, shorthand tuple mappings are available. The size of the tuple determines the xGT type:

- **Table mapping**: ``(SQL_TABLE, [XGT_FRAME])``
- **Vertex mapping**: ``(SQL_TABLE, [XGT_FRAME], (KEY,))``
- **Edge mapping**: ``(SQL_TABLE, [XGT_FRAME], (SOURCE, TARGET, SOURCE_KEY, TARGET_KEY))``

As before, the frame name can be omitted if it matches the SQL table name.

Shorthand Mapping Examples
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

  # Mapping a SQL table to an xGT table:
  ('sql_table_name', 'xgt_table_name')

  # Mapping a SQL table to an xGT vertex (key is a column in the xgt_vertex_user frame):
  ('sql_table_name', 'xgt_vertex_user', ('username',))

  # Mapping a SQL table to a different xGT vertex (key is a column in the xgt_vertex_login frame):
  ('sql_different_table_name', 'xgt_vertex_login', ('ip_address',))
  ('sql_table_name', 'xgt_edge_connection', ('xgt_vertex_user', 'xgt_vertex_login', 'user_column', 'ip_column'))


Examples of these mappings used in the API are provided below.

API Usage Examples
------------------

These examples show typical usage patterns.

.. _copy_examples:

Copy a SQL table
^^^^^^^^^^^^^^^^

This example copies test_table from the test database into test_table on xGT.

.. code-block:: python

   import xgt
   from xgt_connector import ODBCConnector, SQLODBCDriver

   connection_string = 'Driver={MariaDB};Server=127.0.0.1;Port=3306;Database=test;Uid=test;Pwd=foo;'
   xgt_server = xgt.Connection()
   odbc_server = SQLODBCDriver(connection_string)
   conn = ODBCConnector(xgt_server, odbc_server)

   conn.transfer_to_xgt(['test_table'])

To map to a specific xGT table type pass a tuple of (SQL table, xGT table):

.. code-block:: python

   conn.transfer_to_xgt([('test_table', 'xgt_table')])

Or as a dictionary:

.. code-block:: python

   conn.transfer_to_xgt([('test_table', {'frame' : 'xgt_table'} )])

Copy a SQL table to vertices
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This example copy Person into the vertex frame Person.
The simplest way is to pass the key column as tuple with the table name.

.. code-block:: python

   import xgt
   from xgt_connector import ODBCConnector, SQLODBCDriver

   connection_string = 'Driver={MariaDB};Server=127.0.0.1;Port=3306;Database=test;Uid=test;Pwd=foo;'
   xgt_server = xgt.Connection()
   odbc_server = SQLODBCDriver(connection_string)
   conn = ODBCConnector(xgt_server, odbc_server)

   conn.transfer_to_xgt([('Person', ('ID',))])

The key here may be a column number.
To map to a specific xGT table type, pass a triple tuple of (SQL table, xGT vertex, key tuple):

.. code-block:: python

   conn.transfer_to_xgt([('Person', 'xgt_person', ('ID',))])

Dictionary remap:

.. code-block:: python

   conn.transfer_to_xgt([('Person', { 'frame' : 'xgt_person', 'key' : 'ID' })])

The frame may be omitted in the last example if the frame name is the same as SQL table.

Copy a SQL table to edges
^^^^^^^^^^^^^^^^^^^^^^^^^

This example copy Person into the vertex frame Person and the edge Friend into the edge frame Friend.
The simplest way is to pass the frames and source and target columns as tuple with the table name.

.. code-block:: python

   import xgt
   from xgt_connector import ODBCConnector, SQLODBCDriver

   connection_string = 'Driver={MariaDB};Server=127.0.0.1;Port=3306;Database=test;Uid=test;Pwd=foo;'
   xgt_server = xgt.Connection()
   odbc_server = SQLODBCDriver(connection_string)
   conn = ODBCConnector(xgt_server, odbc_server)

   conn.transfer_to_xgt([('Person', ('ID',)), ('Friend', ('Person', 'Person', 'src_key', 'trg_key'))])

The tuple format for the argument tuple is (Source Frame, Target Frame, Source Key, Target Key)

Similarly, a triple tuple may be given to rename:

.. code-block:: python

   conn.transfer_to_xgt([('Person', ('ID',)), ('Friend', 'xgt_friend', ('Person', 'Person', 'src_key', 'trg_key'))])

Or a dictionary:

.. code-block:: python

   conn.transfer_to_xgt([('Person', ('ID',)), ('Friend', {'frame' : 'xgt_friend', 'source': 'Person', 'target' : 'Person', 'source_key' : 'src_key', 'target_key' : 'trg_key'})])


Copy a SQL table to edges without a vertex table
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This example will create the corresponding vertex frame for the source and target with a key column named Key using the source and target keys when creating the edge.

.. code-block:: python

   import xgt
   from xgt_connector import ODBCConnector, SQLODBCDriver

   connection_string = 'Driver={MariaDB};Server=127.0.0.1;Port=3306;Database=test;Uid=test;Pwd=foo;'
   xgt_server = xgt.Connection()
   odbc_server = SQLODBCDriver(connection_string)
   conn = ODBCConnector(xgt_server, odbc_server)

   conn.transfer_to_xgt([('Friend', ('Person', 'Person', 'src_key', 'trg_key'))], easy_edges=True)

The easy_edges parameter would automatically create the Person vertices with a single column using the keys from the Friend edges.

Executing and transferring SQL commands
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This example shows executing a SQL command and transferring the results to xGT.
This functionality allows xGT to connect to any ODBC database and read data from it using their flavor of SQL.

.. code-block:: python

   import xgt
   from xgt_connector import ODBCConnector, SQLODBCDriver

   connection_string = 'Driver={MariaDB};Server=127.0.0.1;Port=3306;Database=test;Uid=test;Pwd=foo;'
   xgt_server = xgt.Connection()
   odbc_server = SQLODBCDriver(connection_string)
   conn = ODBCConnector(xgt_server, odbc_server)

   conn.transfer_query_to_xgt('SELECT * From SqlTable', mapping = ('Friend', ('Person', 'Person', 'src_key', 'trg_key'), easy_edges=True)

This would transfer the whole SqlTable to the xGT Friend edges.
Similar to above the Person vertices would be automatically created.
The mapping parameter is similar to the examples above except it takes single mapping instead of a list.
See :ref:`copy_examples`.
This specifies the frame and type you want the table to map to.

Appending data
^^^^^^^^^^^^^^

By default a transfer will drop any associated frame on xGT.
To append to a frame, set `append` to True on the transfer.

.. code-block:: python

   conn.transfer_to_xgt(['Person'], append=True)

Other parameters when transferring to |xgt|
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* The parameter `batch_size` can be used to set the amount of rows to transfer at once.
* The parameter `transaction_size` number of rows to treat as a single transaction to xGT.
* The parameter `suppress_errors` if True, will ingest all valid rows and return an error with rows not ingested.
* The parameter `on_duplicate_keys` changes the behavior how duplicate vertex keys are handles.
* The parameter `row_filter` takes a Cypher fragment that modifies incoming data.
* The parameter `column_mapping` takes a dictionary of frame column names mapped to either column position or name.

For details about the parameters see: :py:meth:`~xgt_connector.ODBCConnector.transfer_to_xgt` or :py:meth:`~xgt_connector.ODBCConnector.transfer_query_to_xgt`.

For row filtering see the `xGT Documentation <https://docs.rocketgraph.com/user_ref/graphanalytics/tql_fragments.html>`_.
The column names will correspond to the names of the columns coming from the database table.
For instance the row filter would look something like `WHERE a.key = 1 RETURN toString(a.key), a.name"` where `key` and `name` are two columns from table.

For error suppression, the first 10 errors are shown in the error message.
Additional errors can be seen like so:

.. code-block:: python

  try:
    c.transfer_to_xgt(..., suppress_errors=True)
  except xgt.XgtIOError as e:
    error_rows = e.job.get_ingest_errors()

Connecting to Databricks
^^^^^^^^^^^^^^^^^^^^^^^^

After installing `Databricks' ODBC driver <https://www.databricks.com/spark/odbc-drivers-download>`_, connect like so:

.. code-block:: python

   import xgt
   from xgt_connector import ODBCConnector, SQLODBCDriver

   connection_string="DSN=databricks;Database=test;AuthMech=3;Uid=token;Pwd=f98b2a5c1d34e7890abf123456defabc6789;"
   xgt_server = xgt.Connection()
   odbc_server = SQLODBCDriver(connection_string)
   conn = ODBCConnector(xgt_server, odbc_server)

   conn.transfer_to_xgt([('my_table', 'test_table')])

This would transfer the table, `my_table`, under the `test` database to the xGT table named `test_table`.

Connecting to DB2
^^^^^^^^^^^^^^^^^

After installing `IBM's ODBC driver <https://www.ibm.com/support/pages/db2-odbc-cli-driver-download-and-installation-information>`_, connect like so:

.. code-block:: python

   import xgt
   from xgt_connector import ODBCConnector, SQLODBCDriver

   connection_string="DSN=db2;Database=test;UID=test;PWD=test;"
   xgt_server = xgt.Connection()
   odbc_server = SQLODBCDriver(connection_string)
   conn = ODBCConnector(xgt_server, odbc_server)

   conn.transfer_to_xgt([('my_table', 'test_table')])

This would transfer the table, `my_table`, under the `test` database to the xGT table named `test_table`.
With DB2 make sure you are using the correct driver.
On 64-bit systems make sure you are using the libdb2o.so driver.
The 32-bit driver does not work correctly with 64-bit systems, and will only transfer part of the data.

Connecting to Snowflake
^^^^^^^^^^^^^^^^^^^^^^^

After installing `Snowflake's ODBC driver <https://docs.snowflake.com/en/user-guide/odbc.html>`_, connect like so:

.. code-block:: python

   import xgt
   from xgt_connector import ODBCConnector, SnowflakeODBCDriver

   connection_string="DSN=snowflake;Database=test;Warehouse=test;Uid=test;Pwd=test;"
   xgt_server = xgt.Connection()
   odbc_server = SnowflakeODBCDriver(connection_string)
   conn = ODBCConnector(xgt_server, odbc_server)

   conn.transfer_to_xgt([('my_schema.my_table', 'test_table')])

This would transfer the table, `my_table`, in the `my_schema` schema, under the `test` database to the xGT table named `test_table`.

Connecting to MongoDB
^^^^^^^^^^^^^^^^^^^^^

This example uses MongoDB 5 with CData's MongoDB ODBC driver.

.. code-block:: python

   import xgt
   from xgt_connector import ODBCConnector, MongoODBCDriver

   connection_string="DSN=MongoDB;Database=test;Uid=test;Pwd=test;"
   xgt_server = xgt.Connection()
   odbc_server = MongoODBCDriver(connection_string)
   conn = ODBCConnector(xgt_server, odbc_server)

   conn.transfer_to_xgt([('my_collection', 'test_table')])

This would transfer the collection, `my_collection`, under the `test` database to the xGT table named `test_table`.
The driver provides a parameter, include_id, that by default is false.
This parameter removes the _id field returned by the driver.
If this field is present when saving to MongoDB, it will replace documents with corresponding _ids in the database.

Connecting to Oracle
^^^^^^^^^^^^^^^^^^^^

This example uses Oracle XE with their ODBC driver.

.. code-block:: python

   import xgt
   from xgt_connector import ODBCConnector, OracleODBCDriver

   connection_string = 'DSN={OracleODBC-19};Server=127.0.0.1;Port=1521;Uid=c##test;Pwd=test;DBQ=XE;'
   xgt_server = xgt.Connection()
   odbc_server = OracleODBCDriver(connection_string)
   conn = ODBCConnector(xgt_server, odbc_server)

   conn.transfer_to_xgt([('test_table')])

This would transfer the table, `test_table`, to the xGT table named `test_table`.
The driver provides two parameters, upper_case_names and ansi_conversion.
The upper_case_names parameter will treat names of tables like unquoted Oracle SQL does.
By default this is false.
And the ansi_conversion parameter, will convert Number(38,0) Oracle types into int64.
By default this is true.

The Oracle driver only support transferring data from Oracle to xGT.
It doesn't support transferring data from xGT to Oracle.
Binary types are no supported for Oracle.
Interval types likely don't work through ODBC as well.

Connecting to SAP ASE/IQ
^^^^^^^^^^^^^^^^^^^^^^^^

This example uses SAP ASE/IQ with their ODBC driver.

.. code-block:: python

   import xgt
   from xgt_connector import ODBCConnector, SAPODBCDriver

   connection_string = 'DSN={ASE};Server=127.0.0.1;Port=5000;Uid=test;Pwd=test;Database=test;'
   xgt_server = xgt.Connection()
   odbc_server = SAPODBCDriver(connection_string)
   conn = ODBCConnector(xgt_server, odbc_server)

   conn.transfer_to_xgt([('test_table')])

This would transfer the table, `test_table`, to the xGT table named `test_table`.
Transferring data from xGT to SAP ASE/IQ also works.

Transferring data from |xgt| to ODBC
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This example copies test_table from xGT to a test database.

.. code-block:: python

   import xgt
   from xgt_connector import ODBCConnector, SQLODBCDriver

   connection_string = 'Driver={MariaDB};Server=127.0.0.1;Port=3306;Database=test;Uid=test;Pwd=foo;'
   xgt_server = xgt.Connection()
   odbc_server = SQLODBCDriver(connection_string)
   conn = ODBCConnector(xgt_server, odbc_server)

   conn.transfer_to_odbc(tables=['test_table'])

To map to a specific xGT table type pass a tuple of (xGT frame, SQL table):

.. code-block:: python

   conn.transfer_to_odbc(tables=[('xgt_table', 'sql_table')])

The parameter `batch_size` can be used to set the amount of rows to transfer at once.
Parameters for transferring edges and vertices exist as well.
Some limitations exist.
See below for more details.

Additional Examples
^^^^^^^^^^^^^^^^^^^

More detailed examples can be found in :ref:`jupyter` or on github:

* `Python Examples <https://github.com/rocketgraphai/xgt_connector/tree/main/examples/odbc>`_
* `Jupyter Notebooks <https://github.com/rocketgraphai/xgt_connector/tree/main/jupyter/odbc>`_

Limitations
-----------

* When transferring to a database, the table must already be created.
* Transfer sizes/times are estimates and may not be available.
* The Databricks and Oracle drivers don't support transferring from xGT to them.
* Transferring from xGT to MarieDB with None for floats is not supported.
* Binary data types not supported.

API Details
-----------

.. currentmodule:: xgt_connector

.. autosummary::
  :toctree:

  ODBCConnector
  SQLODBCDriver
  MongoODBCDriver
  OracleODBCDriver
  SAPODBCDriver
  SnowflakeODBCDriver
