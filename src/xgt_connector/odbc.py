#!/usr/bin/env python
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

import arrow_odbc
import struct
import sys
import xgt
import pyarrow as pa
import pyarrow.flight as pf

from collections.abc import Iterable, Mapping, Sequence

Iter, Map, Seq, List, Dict = Iterable, Mapping, Sequence, list, dict

from arrow_odbc import read_arrow_batches_from_odbc
from arrow_odbc import insert_into_table
from typing import Optional, Union, TYPE_CHECKING
from xgt import SchemaMessages_pb2 as sch_proto
from .common import ProgressDisplay

# Convert the pyarrow type to an xgt type.
def _pyarrow_type_to_xgt_type(pyarrow_type):
    if pa.types.is_boolean(pyarrow_type):
        return xgt.BOOLEAN
    elif pa.types.is_timestamp(pyarrow_type) or pa.types.is_date64(pyarrow_type):
        return xgt.DATETIME
    elif pa.types.is_date(pyarrow_type):
        return xgt.DATE
    elif pa.types.is_time(pyarrow_type):
        return xgt.TIME
    elif pa.types.is_integer(pyarrow_type):
        return xgt.INT
    elif pa.types.is_float32(pyarrow_type) or \
         pa.types.is_float64(pyarrow_type) or \
         pa.types.is_decimal(pyarrow_type):
        return xgt.FLOAT
    elif pa.types.is_string(pyarrow_type):
        return xgt.TEXT
    else:
        raise xgt.XgtTypeError("Cannot convert pyarrow type " + str(pyarrow_type) + " to xGT type.")

def _infer_xgt_schema_from_pyarrow_schema(pyarrow_schema, conversions):
    schema = []
    for field in pyarrow_schema:
        if field.type in conversions:
            field = pa.field(field.name, conversions[field.type], field.nullable, field.metadata)
        schema.append(field)

    schema = pa.schema(schema)

    return [[c.name, _pyarrow_type_to_xgt_type(c.type)] for c in schema]

class SQLODBCDriver(object):
    def __init__(self, connection_string : str):
        """
        Initializes the driver class.

        Parameters
        ----------
        connection_string : str
            Standard ODBC connection string used for connecting to the ODBC applications.
            Example:
            'Driver={MariaDB};Server=127.0.0.1;Port=3306;Database=test;Uid=test;Pwd=foo;'
        """
        self._connection_string = connection_string
        self._schema_query = "SELECT * FROM {0} LIMIT 1;"
        self._data_query = "SELECT * FROM {0};"
        self._estimate_query="SELECT TABLE_ROWS FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{0}';"

    def _get_data_query(self, table, arrow_schema):
        return  self._data_query.format(table)

    def _conversions(self):
       return { }

    def _get_record_batch_schema(self, table, max_text_size, max_binary_size):
        reader = read_arrow_batches_from_odbc(
            query=self._schema_query.format(table),
            connection_string=self._connection_string,
            batch_size=1,
            max_text_size=max_text_size,
            max_binary_size=max_binary_size,
        )
        return reader.schema

class MongoODBCDriver(object):
    def __init__(self, connection_string : str , include_id : bool = False):
        """
        Initializes the driver class.

        Parameters
        ----------
        connection_string : str
            Standard ODBC connection string used for connecting to MongoDB.
            Example:
            'DSB=MongoDB;Database=test;Uid=test;Pwd=foo;'
        include_id : boolean
            Include the MongoDB id field when transferring from MongoDB.
            If the id field is included, writing data back to the database will update the columns
            instead of inserting new rows.
            By default false.
        """
        self._connection_string = connection_string
        self._schema_query = "SELECT * FROM {0} LIMIT 1;"
        self._data_query = "SELECT {0} FROM {1};"
        self._estimate_query = "SELECT TABLE_ROWS FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{0}';"
        self._include_id = include_id

    def _get_data_query(self, table, arrow_schema):
        cols = ','.join([x.name for x in arrow_schema])
        return  self._data_query.format(cols, table)

    def _conversions(self):
       return { }

    def _get_record_batch_schema(self, table, max_text_size, max_binary_size):
        reader = read_arrow_batches_from_odbc(
            query=self._schema_query.format(table),
            connection_string=self._connection_string,
            batch_size=1,
            max_text_size=max_text_size,
            max_binary_size=max_binary_size,
        )

        schema = reader.schema
        if not self._include_id:
            # Remove the _id column.
            return pa.schema([field for field in schema if field.name != '_id'])

        return schema

class OracleODBCDriver(object):
    def __init__(self, connection_string : str, upper_case_names : bool = False, ansi_conversion : bool = True):
        """
        Initializes the driver class.

        Parameters
        ----------
        connection_string : str
            Standard ODBC connection string used for connecting to Oracle.
            Example:
            'DSN={OracleODBC-19};Server=127.0.0.1;Port=1521;Uid=c##test;Pwd=test;DBQ=XE;'
        upper_case_names : bool
          Convert table names to uppercase similar to unqouted names behavior in Oracle queries.
          By default false.
        ansi_conversion : bool
          Convert Number(38,0) into int64s in xGT if true. Otherwise, they are stored as floats.
          This based on the ANSI int conversion Oracle does and reverses that. By default true.
        """
        self._connection_string = connection_string
        if upper_case_names:
            self._schema_query = "SELECT * FROM {0} WHERE ROWNUM <= 1"
            self._data_query = "SELECT * FROM {0}"
        else:
            self._schema_query = "SELECT * FROM \"{0}\" WHERE ROWNUM <= 1"
            self._data_query = "SELECT * FROM \"{0}\""
        self._estimate_query="SELECT NUM_ROWS FROM ALL_TABLES WHERE TABLE_NAME = '{0}'"
        self._ansi_conversion = ansi_conversion

    def _get_data_query(self, table, arrow_schema):
        return self._data_query.format(table)

    def _conversions(self):
        if self._ansi_conversion:
            return { pa.decimal128(38, 0) : pa.int64() }
        else:
            return { }

    def _get_record_batch_schema(self, table, max_text_size, max_binary_size):
        reader = read_arrow_batches_from_odbc(
            query=self._schema_query.format(table),
            connection_string=self._connection_string,
            batch_size=1,
            max_text_size=max_text_size,
            max_binary_size=max_binary_size,
        )
        return reader.schema

class SAPODBCDriver(object):
    def __init__(self, connection_string : str):
        """
        Initializes the driver class.

        Parameters
        ----------
        connection_string : str
            Standard ODBC connection string used for connecting to the ODBC applications.
            Example:
            'Driver={AES};Server=127.0.0.1;Port=3306;Database=test;Uid=test;Pwd=foo;'
        """
        self._connection_string = connection_string
        self._schema_query = "SELECT TOP 1 * FROM {0};"
        self._data_query = "SELECT * FROM {0};"
        self._estimate_query="SELECT TABLE_ROWS FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{0}';"

    def _get_data_query(self, table, arrow_schema):
        return  self._data_query.format(table)

    def _conversions(self):
       return { }

    def _get_record_batch_schema(self, table, max_text_size, max_binary_size):
        reader = read_arrow_batches_from_odbc(
            query=self._schema_query.format(table),
            connection_string=self._connection_string,
            batch_size=1,
            max_text_size=max_text_size,
            max_binary_size=max_binary_size,
        )
        return reader.schema

class SnowflakeODBCDriver(object):
    def __init__(self, connection_string : str, ansi_conversion : bool = True):
        """
        Initializes the driver class.

        Parameters
        ----------
        connection_string : str
            Standard ODBC connection string used for connecting to Snowflake.
            Example:
            'DSN=snowflake;Database=test;Warehouse=test;Uid=test;Pwd=test;'
        ansi_conversion : bool
          Convert Number(38,0) into int64s in xGT if true. Otherwise, they are stored as floats.
          This based on the ANSI int conversion Snowflake does and reverses that. By default true.
        """
        self._connection_string = connection_string
        self._schema_query = "SELECT * FROM {0} LIMIT 1;"
        self._data_query = "SELECT * FROM {0};"
        self._estimate_query="SELECT TABLE_ROWS FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{0}';"
        self._ansi_conversion = ansi_conversion

    def _get_data_query(self, table, arrow_schema):
        return self._data_query.format(table)

    def _conversions(self):
        if self._ansi_conversion:
            return { pa.decimal128(38, 0) : pa.int64() }
        else:
            return { }

    def _get_record_batch_schema(self, table, max_text_size, max_binary_size):
        reader = read_arrow_batches_from_odbc(
            query=self._schema_query.format(table),
            connection_string=self._connection_string,
            batch_size=1,
            max_text_size=max_text_size,
            max_binary_size=max_binary_size,
        )
        return reader.schema

ODBCDriverTypes = Union[SQLODBCDriver, MongoODBCDriver, OracleODBCDriver,
                        SAPODBCDriver, SnowflakeODBCDriver]

class ODBCConnector(object):
    def __init__(self, xgt_server : xgt.Connection, odbc_driver : ODBCDriverTypes):
        """
        Initializes the connector class.

        Parameters
        ----------
        xgt_server : xgt.Connection
            Connection object to xGT.
        odbc_driver : SQLODBCDriver
            Connection object to ODBC.
        """
        self._xgt_server = xgt_server
        self._default_namespace = xgt_server.get_default_namespace()
        self._driver = odbc_driver

    def get_xgt_schemas(self, tables : Iter[str] = None, max_text_size : int = None,
                        max_binary_size : int = None) -> Dict:
        """
        Retrieve a dictionary containing the schema information for all of
        the tables requested and their mappings.

        Parameters
        ----------
        tables : iterable
            List of requested tables.
        max_text_size : int
            The upper limit on the buffers used when transferring ODBC variable-length text fields.
            When using VARCHAR from a database, if a limit isn't set for the length of the strings
            like VARCHAR(255), the schema size of each string entry could be whatever the max size of
            database uses for each entry when reporting to ODBC. For instance, each string in Snowflake
            has an upper limit of 16MB length. This means when allocating the buffers to store the ODBC
            batch_size would be 16MB multiplied by the batch_size. This parameter will impose a limit on
            each string length when transferring. Default is determined by the database.
        max_binary_size : int
            The upper limit on the buffers used when transferring ODBC variable-length binary fields.
            When using VARBINARY from a database, if a limit isn't set for the length of binary data
            like VARBINARY(255), the schema size of each binary entry could be whatever the max size of
            database uses for each entry when reporting to ODBC. This parameter will impose a limit on
            each binary field length when transferring. Default is determined by the database.

        Returns
        -------
        dict
            Dictionary containing the schema information of the tables,
            vertices, and edges requested.
        """
        if tables is None:
            tables = [ ]
        mapping_vertices = { }
        mapping_edges = { }
        mapping_tables = { }
        result = {'vertices' : dict(), 'edges' : dict(), 'tables' : dict()}

        for val in tables:
            self.__get_mapping(val, mapping_tables, mapping_vertices, mapping_edges)

        for table in mapping_tables:
            schema = self.__extract_xgt_table_schema(table, mapping_tables, max_text_size, max_binary_size)
            result['tables'][table] = schema

        for table in mapping_vertices:
            schema = self.__extract_xgt_table_schema(table, mapping_vertices, max_text_size, max_binary_size)
            result['vertices'][table] = schema

        for table in mapping_edges:
            schema = self.__extract_xgt_table_schema(table, mapping_edges, max_text_size, max_binary_size)
            result['edges'][table] = schema

        return result

    def create_xgt_schemas(self, xgt_schemas : Map, append : bool = False,
                           force : bool = False, easy_edges : bool = False) -> None:
        """
        Creates table, vertex and/or edge frames in Rocketgraph xGT.

        This function first infers the schemas for all of the needed frames in xGT to
        store the requested data.
        Then those frames are created in xGT.

        Parameters
        ----------
        xgt_schemas : dict
            Dictionary containing schema information for vertex and edge frames
            to create in xGT.
            This dictionary can be the value returned from the
            :py:meth:`~ODBCConnector.get_xgt_schemas` method.
        append : boolean
            Set to true when the xGT frames are already created and holding data
            that should be appended to.
            Set to false when the xGT frames are to be newly created (removing
            any existing frames with the same names prior to creation).
        force : boolean
            Set to true to force xGT to drop edges when a vertex frame has dependencies.
        easy_edges : boolean
            Set to true to create a basic vertex class with key column for any edges
            without corresponding vertex frames.

        Returns
        -------
            None
        """
        if not append:
            if easy_edges:
                for edge, schema in xgt_schemas['edges'].items():
                    src = schema['mapping']['source']
                    trg = schema['mapping']['target']
                    if src not in xgt_schemas['vertices']:
                        v_key = schema['mapping']['source_key']
                        v_type = 'int'
                        for element in schema['xgt_schema']:
                            if v_key == element[0]:
                                v_type = element[1]
                        xgt_schemas['vertices'][src] = { 'xgt_schema': [['key', v_type]], 'temp_creation' : True, 'mapping' : { 'frame' : src, 'key' : 'key' } }
                    if trg not in xgt_schemas['vertices']:
                        v_key = schema['mapping']['target_key']
                        v_type = 'int'
                        for element in schema['xgt_schema']:
                            if v_key == element[0]:
                                v_type = element[1]
                        xgt_schemas['vertices'][trg] = { 'xgt_schema': [['key', v_type]], 'temp_creation' : True, 'mapping' : { 'frame' : trg, 'key' : 'key' } }
            for _, schema in xgt_schemas['tables'].items():
                self._xgt_server.drop_frame(schema['mapping']['frame'])

            for _, schema in xgt_schemas['edges'].items():
                self._xgt_server.drop_frame(schema['mapping']['frame'])

            for _, schema in xgt_schemas['vertices'].items():
                try:
                    self._xgt_server.drop_frame(schema['mapping']['frame'])
                except xgt.XgtFrameDependencyError as e:
                    if force:
                        # Would be better if this could be done without doing this.
                        edge_frames = str(e).split(':')[-1].split(' ')[1:]
                        for edge in edge_frames:
                            self._xgt_server.drop_frame(edge)
                        self._xgt_server.drop_frame(schema['mapping']['frame'])
                    else:
                        raise e

            for table, schema in xgt_schemas['tables'].items():
                self._xgt_server.create_table_frame(name = schema['mapping']['frame'], schema = schema['xgt_schema'])

            remove_list = []
            for vertex, schema in xgt_schemas['vertices'].items():
                key = schema['mapping']['key']
                if isinstance(key, int):
                    key = schema['xgt_schema'][key][0]
                self._xgt_server.create_vertex_frame(name = schema['mapping']['frame'], schema = schema['xgt_schema'], key = key)
                if 'temp_creation' in schema:
                    remove_list.append(vertex)

            for vertex in remove_list:
                xgt_schemas['vertices'].pop(vertex)

            for edge, schema in xgt_schemas['edges'].items():
                src = schema['mapping']['source']
                trg = schema['mapping']['target']
                src_key = schema['mapping']['source_key']
                trg_key = schema['mapping']['target_key']
                if isinstance(src_key, int):
                    src_key = schema['xgt_schema'][src_key][0]
                if isinstance(trg_key, int):
                    trg_key = schema['xgt_schema'][trg_key][0]
                self._xgt_server.create_edge_frame(name = schema['mapping']['frame'], schema = schema['xgt_schema'],
                                                   source = src, target = trg, source_key = src_key, target_key = trg_key)

    def transfer_to_xgt(self, tables : Iter = None, append : bool = False, force : bool = False,
                        easy_edges : bool = False, batch_size : int = 10000, transaction_size : int = 0,
                        max_text_size : int = None, max_binary_size : int = None,
                        column_mapping : Optional[Map[str, Union[str, int]]] = None,
                        suppress_errors : bool = False, row_filter : str = None, on_duplicate_keys : str = "error") -> None:
        """
        Copies data from the ODBC application to Rocketgraph xGT.

        This function first infers the schemas for all of the needed frames in xGT to
        store the requested data.
        Then those frames are created in xGT.
        Finally, all of the tables, vertices, and all of the edges are copied,
        one frame at a time, from the ODBC application to xGT.

        Parameters
        ----------
        tables : Iterable
            List of requested tables names.
            May be a tuple specify a mapping to xGT types. See documentation: :ref:`mapping-sql-label` or `Web Docs <https://rocketgraphai.github.io/xgt_connector/odbc/index.html#mapping-sql-tables-to-graphs>`_.
        append : boolean
            Set to true when the xGT frames are already created and holding data
            that should be appended to.
            Set to false when the xGT frames are to be newly created (removing
            any existing frames with the same names prior to creation).
        force : boolean
            Set to true to force xGT to drop edges when a vertex frame has dependencies.
        easy_edges : boolean
            Set to true to create a basic vertex class wtih key column for any edges
            without corresponding vertex frames.
        batch_size : int
            Number of rows to transfer at once. Defaults to 10000.
        transaction_size : int
            Number of rows to treat as a single transaction to xGT. Defaults to 0.
            Should be a multiple of the batch size and greater than the batch size.
            0 means treat all rows as a single transaction.
        max_text_size : int
            The upper limit on the buffers used when transferring ODBC variable-length text fields.
            When using VARCHAR from a database, if a limit isn't set for the length of the strings
            like VARCHAR(255), the schema size of each string entry could be whatever the max size of
            database uses for each entry when reporting to ODBC. For instance, each string in Snowflake
            has an upper limit of 16MB length. This means when allocating the buffers to store the ODBC
            batch_size would be 16MB multiplied by the batch_size. This parameter will impose a limit on
            each string length when transferring. Default is determined by the database.
        max_binary_size : int
            The upper limit on the buffers used when transferring ODBC variable-length binary fields.
            When using VARBINARY from a database, if a limit isn't set for the length of binary data
            like VARBINARY(255), the schema size of each binary entry could be whatever the max size of
            database uses for each entry when reporting to ODBC. This parameter will impose a limit on
            each binary field length when transferring. Default is determined by the database.
        column_mapping : dictionary
            Maps the frame column names to SQL columns for the ingest. The key of
            each element is a frame column name. The value is either the name of the
            SQL column (from the table) or the table column index.
        suppress_errors : bool
            If true, will continue to insert data if an ingest error is encountered,
            placing the first 1000 errors in the job history. If false, stops on
            first error and raises.  Defaults to False.
        row_filter : str
            TQL fragment used to filter, modify and parameterize the raw data from
            the input to produce the row data fed to the frame.
        on_duplicate_keys : {‘error’, ‘skip’, 'skip_same'}, default 'error'
            Specifies what to do upon encountering a duplicate vertex key.
            Only works for vertex frames. Is ignored for table and edge frames.
            Allowed values are :
            - 'error', raise an Exception when a duplicate key is found.
            - 'skip', skip duplicate keys without raising.
            - 'skip_same', skip duplicate keys if the row is exactly the same without raising.

        Returns
        -------
            None
        """
        if transaction_size > 0 and (transaction_size < batch_size or transaction_size % batch_size != 0):
            raise ValueError("Transaction size needs to be a multiple of the batch size and >= the batch size of " + str(batch_size))
        xgt_schema = self.get_xgt_schemas(tables, max_text_size, max_binary_size)
        self.create_xgt_schemas(xgt_schema, append, force, easy_edges)
        self.copy_data_to_xgt(xgt_schema, batch_size, transaction_size,
                              max_text_size, max_binary_size, column_mapping,
                              suppress_errors, row_filter, on_duplicate_keys)

    def transfer_query_to_xgt(self, query : str = None, mapping : Union[Map, tuple] = None, append : bool = False,
                              force : bool = False, easy_edges : bool = False, batch_size : int = 10000,
                              transaction_size : int = 0, max_text_size : int = None,
                              max_binary_size : int = None, column_mapping : Optional[Map[str, Union[str, int]]] = None,
                              suppress_errors : bool = False,
                              row_filter : str = None, on_duplicate_keys : str = "error") -> None:
        """
        Copies data from the ODBC application to Rocketgraph xGT.

        This function first infers the schemas for the query.
        Then it maps to the type specificed in mapping.
        Finally, the data is copied from the ODBC application to xGT.

        Parameters
        ----------
        query : string
            SQL query to execute and insert into xGT. Syntax depends on the SQL syntax of the database you are connecting to.
        mapping :
            May be a tuple specify a mapping to xGT types. See documentation: :ref:`mapping-sql-label` or `Web Docs <https://rocketgraphai.github.io/xgt_connector/odbc/index.html#mapping-sql-tables-to-graphs>`_.
        append : boolean
            Set to true when the xGT frames are already created and holding data
            that should be appended to.
            Set to false when the xGT frames are to be newly created (removing
            any existing frames with the same names prior to creation).
        force : boolean
            Set to true to force xGT to drop edges when a vertex frame has dependencies.
        easy_edges : boolean
            Set to true to create a basic vertex class with key column for any edges
            without corresponding vertex frames.
        batch_size : int
            Number of rows to transfer at once. Defaults to 10000.
        transaction_size : int
            Number of rows to treat as a single transaction to xGT. Defaults to 0.
            Should be a multiple of the batch size and greater than the batch size.
            0 means treat all rows as a single transaction.
        max_text_size : int
            The upper limit on the buffers used when transferring ODBC variable-length text fields.
            When using VARCHAR from a database, if a limit isn't set for the length of the strings
            like VARCHAR(255), the schema size of each string entry could be whatever the max size of
            database uses for each entry when reporting to ODBC. For instance, each string in Snowflake
            has an upper limit of 16MB length. This means when allocating the buffers to store the ODBC
            batch_size would be 16MB multiplied by the batch_size. This parameter will impose a limit on
            each string length when transferring. Default is determined by the database.
        max_binary_size : int
            The upper limit on the buffers used when transferring ODBC variable-length binary fields.
            When using VARBINARY from a database, if a limit isn't set for the length of binary data
            like VARBINARY(255), the schema size of each binary entry could be whatever the max size of
            database uses for each entry when reporting to ODBC. This parameter will impose a limit on
            each binary field length when transferring. Default is determined by the database.
        column_mapping : dictionary
            Maps the frame column names to SQL columns for the ingest. The key of
            each element is a frame column name. The value is either the name of the
            SQL column (from the table) or the table column index.
        suppress_errors : bool
            If true, will continue to insert data if an ingest error is encountered,
            placing the first 1000 errors in the job history. If false, stops on
            first error and raises.  Defaults to False.
        row_filter : str
            TQL fragment used to filter, modify and parameterize the raw data from
            the input to produce the row data fed to the frame.
        on_duplicate_keys : {‘error’, ‘skip’, 'skip_same'}, default 'error'
            Specifies what to do upon encountering a duplicate vertex key.
            Only works for vertex frames. Is ignored for table and edge frames.
            Allowed values are :
            - 'error', raise an Exception when a duplicate key is found.
            - 'skip', skip duplicate keys without raising.
            - 'skip_same', skip duplicate keys if the row is exactly the same without raising.

        Returns
        -------
            array of transfer information in the form of [row count, byte count]
        """
        if transaction_size > 0 and (transaction_size < batch_size or transaction_size % batch_size != 0):
            raise ValueError("Transaction size needs to be a multiple of batch size and >= the batch size of " + str(batch_size))
        return self.__copy_query_data_to_xgt(query, mapping, append, force, easy_edges,
                                             batch_size, transaction_size, max_text_size, max_binary_size,
                                             column_mapping, suppress_errors, row_filter, on_duplicate_keys)

    def copy_data_to_xgt(self, xgt_schemas : Map, batch_size : int = 10000, transaction_size : int = 0,
                         max_text_size : int = None, max_binary_size : int = None,
                         column_mapping : Optional[Map[str, Union[str, int]]] = None,
                         suppress_errors : bool = False, row_filter : str = None,
                         on_duplicate_keys : str = "error") -> None:
        """
        Copies data from the ODBC application to the requested table, vertex and/or edge frames
        in Rocketgraph xGT.

        This function copies data from the ODBC application to xGT for all of the tables, vertices
        and edges, one frame at a time.

        Parameters
        ----------
        xgt_schemas : dict
            Dictionary containing schema information for table, vertex and edge frames
            to create in xGT.
            This dictionary can be the value returned from the
            :py:meth:`~ODBCConnector.get_xgt_schemas` method.
        batch_size : int
            Number of rows to transfer at once. Defaults to 10000.
        transaction_size : int
            Number of rows to treat as a single transaction to xGT. Defaults to 0.
            Should be a multiple of the batch size and greater than the batch size.
            0 means treat all rows as a single transaction.
        max_text_size : int
            The upper limit on the buffers used when transferring ODBC variable-length text fields.
            When using VARCHAR from a database, if a limit isn't set for the length of the strings
            like VARCHAR(255), the schema size of each string entry could be whatever the max size of
            database uses for each entry when reporting to ODBC. For instance, each string in Snowflake
            has an upper limit of 16MB length. This means when allocating the buffers to store the ODBC
            batch_size would be 16MB multiplied by the batch_size. This parameter will impose a limit on
            each string length when transferring. Default is determined by the database.
        max_binary_size : int
            The upper limit on the buffers used when transferring ODBC variable-length binary fields.
            When using VARBINARY from a database, if a limit isn't set for the length of binary data
            like VARBINARY(255), the schema size of each binary entry could be whatever the max size of
            database uses for each entry when reporting to ODBC. This parameter will impose a limit on
            each binary field length when transferring. Default is determined by the database.
        column_mapping : dictionary
            Maps the frame column names to SQL columns for the ingest. The key of
            each element is a frame column name. The value is either the name of the
            SQL column (from the table) or the table column index.
        suppress_errors : bool
            If true, will continue to insert data if an ingest error is encountered,
            placing the first 1000 errors in the job history. If false, stops on
            first error and raises.  Defaults to False.
        row_filter : str
            TQL fragment used to filter, modify and parameterize the raw data from
            the input to produce the row data fed to the frame.
        on_duplicate_keys : {‘error’, ‘skip’, 'skip_same'}, default 'error'
            Specifies what to do upon encountering a duplicate vertex key.
            Only works for vertex frames. Is ignored for table and edge frames.
            Allowed values are :
            - 'error', raise an Exception when a duplicate key is found.
            - 'skip', skip duplicate keys without raising.
            - 'skip_same', skip duplicate keys if the row is exactly the same without raising.

        Returns
        -------
            None
        """
        estimate = 0
        def estimate_size(table):
            estimate = 0
            reader = read_arrow_batches_from_odbc(
                query=self._driver._estimate_query.format(table),
                connection_string=self._driver._connection_string,
                batch_size=batch_size,
                max_text_size=max_text_size,
                max_binary_size=max_binary_size,
            )
            for batch in reader:
                for _, row in batch.to_pydict().items():
                    for item in row:
                        if isinstance(item, int):
                            estimate += item
            return estimate
        try:
            for table, schema in xgt_schemas['tables'].items():
                estimate += estimate_size(table)
            for table, schema in xgt_schemas['vertices'].items():
                estimate += estimate_size(table)
            for table, schema in xgt_schemas['edges'].items():
                estimate += estimate_size(table)
        except Exception as e:
            pass

        with ProgressDisplay(estimate) as progress_bar:
            for table, schema in xgt_schemas['tables'].items():
                self.__copy_data(self._driver._get_data_query(
                    table, schema['arrow_schema']), schema['mapping']['frame'],
                    schema['arrow_schema'], progress_bar, batch_size,
                    transaction_size, max_text_size, max_binary_size,
                    column_mapping, suppress_errors, row_filter,
                    on_duplicate_keys)
            for table, schema in xgt_schemas['vertices'].items():
                self.__copy_data(self._driver._get_data_query(
                    table, schema['arrow_schema']), schema['mapping']['frame'],
                    schema['arrow_schema'], progress_bar, batch_size,
                    transaction_size, max_text_size, max_binary_size,
                    column_mapping, suppress_errors, row_filter,
                    on_duplicate_keys)
            for table, schema in xgt_schemas['edges'].items():
                self.__copy_data(self._driver._get_data_query(
                    table, schema['arrow_schema']), schema['mapping']['frame'],
                    schema['arrow_schema'], progress_bar, batch_size,
                    transaction_size, max_text_size, max_binary_size,
                    column_mapping, suppress_errors, row_filter,
                    on_duplicate_keys)

    def transfer_to_odbc(self, vertices : Iter[str] = None,
                         edges : Iter[str] = None,
                         tables : Iter[str] = None, namespace : str = None,
                         batch_size : int = 10000) -> None:
        """
        Copies data from Rocketgraph xGT to an ODBC application.

        Parameters
        ----------
        vertices : iterable
            List of requested vertex frame names.
            May be a tuple specifying: (xgt_frame_name, database_table_name).
        edges : iterable
            List of requested edge frame names.
            May be a tuple specifying: (xgt_frame_name, database_table_name).
        tables : iterable
            List of requested table frame names.
            May be a tuple specifying: (xgt_frame_name, database_table_name).
        namespace : str
            Namespace for the selected frames.
            If none will use the default namespace.
        batch_size : int
            Number of rows to transfer at once. Defaults to 10000.

        Returns
        -------
            None
        """
        if isinstance(self._driver, OracleODBCDriver):
            raise XgtNotImplementedError("Oracle not supported for transferring to.")
        xgt_server = self._xgt_server
        if namespace == None:
            namespace = self._default_namespace
        if vertices == None and edges == None and tables == None:
            vertices = [(frame.name, frame.name) for frame in xgt_server.get_frames(namespace=namespace, frame_type='vertex')]
            edges = [(frame.name, frame.name) for frame in xgt_server.get_frames(namespace=namespace, frame_type='edge')]
            tables = [(frame.name, frame.name) for frame in xgt_server.get_frames(namespace=namespace, frame_type='table')]
            namespace = None
        if vertices == None:
            vertices = []
        if edges == None:
            edges = []
        if tables == None:
            tables = []

        final_vertices = []
        final_edges = []
        final_tables = []

        for vertex in vertices:
            if isinstance(vertex, str):
                final_vertices.append((vertex, vertex))
            else:
                final_vertices.append(vertex)
        for edge in edges:
            if isinstance(edge, str):
                final_edges.append((edge, edge))
            else:
                final_edges.append(edge)
        for table in tables:
            if isinstance(table, str):
                final_tables.append((table, table))
            else:
                final_tables.append(table)

        estimate = 0

        for vertex in final_vertices:
            estimate += xgt_server.get_frame(vertex[0]).num_rows
        for edge in final_edges:
            estimate += xgt_server.get_frame(edge[0]).num_rows
        for table in final_tables:
            estimate += xgt_server.get_frame(table[0]).num_rows

        with ProgressDisplay(estimate) as progress_bar:
            for table in final_vertices + final_edges + final_tables:
                frame, table = table
                reader = self.__arrow_reader(frame)
                batch_reader = reader.to_reader()

                _, target_schema = self.__get_xgt_schema(table)
                schema = reader.schema
                final_schema = [xgt_field.with_name(database_field.name) for database_field, xgt_field in zip(target_schema, schema)]
                final_schema = pa.schema(final_schema)
                schema = final_schema
                final_names = [database_field.name for database_field in target_schema]
                def iter_record_batches():
                    for batch in batch_reader:
                        table = pa.Table.from_pandas(batch.to_pandas(integer_object_nulls=True, date_as_object=True, timestamp_as_object=True))
                        new_schema = pa.schema([
                            (field.name, pa.string() if pa.types.is_large_string(field.type) else field.type)
                            for field in table.schema
                        ])
                        table = table.cast(new_schema).rename_columns(final_names).to_batches()
                        for batch in table:
                            yield batch
                            progress_bar.show_progress(batch.num_rows)

                final_reader = pa.ipc.RecordBatchReader.from_batches(schema, iter_record_batches())
                insert_into_table(
                    connection_string=self._driver._connection_string,
                    chunk_size=batch_size,
                    table=table,
                    reader=final_reader,
                )

    def __build_flight_path(self, frame_name, column_mapping = None,
                            suppress_errors = False, row_filter = None,
                            on_duplicate_keys = 'error'):
        if '__' in frame_name:
            # Split by '__' and use the first part as the namespace
            namespace, name = frame_name.split('__', 1)
        else:
            # Use the default namespace if no '__' is found
            namespace, name = self._default_namespace, frame_name

        path = (namespace, name)

        self.__validate_column_mapping(column_mapping)
        if row_filter is None and column_mapping is not None:
            map_values = ".map_column_names=[" + \
                ','.join(f"{key}:{value}" for key, value in column_mapping.items()
                    if isinstance(value, str)) + "]"
            path += (map_values,)
            map_values = ".map_column_ids=[" + \
                ','.join(f"{key}:{value}" for key, value in column_mapping.items()
                    if isinstance(value, int)) + "]"
            path += (map_values,)

        suppress_errors_option = ".suppress_errors=" + str(suppress_errors).lower()
        on_duplicate_keys_option = ".on_duplicate_keys=" + str(on_duplicate_keys).lower()
        path += (suppress_errors_option,)
        path += (on_duplicate_keys_option,)

        if row_filter is not None:
            row_filter_value = f'.row_filter="{row_filter}"'
            path += (row_filter_value,)

        return path

    def __arrow_writer(self, frame_name, schema, column_mapping, suppress_errors, row_filter, on_duplicate_keys):
        arrow_conn = self._xgt_server.arrow_conn
        flight_path = self.__build_flight_path(frame_name, column_mapping, suppress_errors, row_filter, on_duplicate_keys)
        writer, metadata = arrow_conn.do_put(
            pf.FlightDescriptor.for_path(*flight_path),
            schema)
        return (writer, metadata)

    def __arrow_reader(self, frame_name):
        arrow_conn = self._xgt_server.arrow_conn
        return arrow_conn.do_get(pf.Ticket(self._default_namespace + '__' + frame_name))

    def __copy_data(self, query_for_extract, frame, schema, progress_bar, batch_size,
                    transaction_size, max_text_size, max_binary_size, column_mapping,
                    suppress_errors, row_filter, on_duplicate_keys):
        try:
            reader = read_arrow_batches_from_odbc(
                query=query_for_extract,
                connection_string=self._driver._connection_string,
                batch_size=batch_size,
                max_text_size=max_text_size,
                max_binary_size=max_binary_size,
            )
            count = 0
            writer, metadata = self.__arrow_writer(frame, schema, column_mapping, suppress_errors, row_filter, on_duplicate_keys)
            for batch in reader:
                # Process arrow batches
                writer.write(batch)
                progress_bar.show_progress(batch.num_rows)
                count += batch.num_rows
                # Start a new transaction
                if transaction_size > 0 and count >= transaction_size:
                    count = 0
                    if (suppress_errors):
                        self.__check_for_error(frame, schema, writer, metadata)
                    writer.close()
                    writer, metadata = self.__arrow_writer(frame, schema, column_mapping, suppress_errors, row_filter, on_duplicate_keys)

            if (suppress_errors):
                self.__check_for_error(frame, schema, writer, metadata)

            writer.close()
        except arrow_odbc.error.Error as e:
            if "too large to be written" in str(e):
                raise RuntimeError(
                    f"{e}\nHint: Try building the query yourself with transfer_query_to_xgt and casting oversized columns with CAST(column AS VARCHAR(n)) "
                    "or changing the schema of the table to use a fixed size VARCHAR(n). "
                    "Variable text width columns sometimes report incorrect maximum sizes from drivers. "
                ) from e
            raise

    def __check_for_error(self, frame, schema, writer, metadata):
        # Write an empty batch with metadata to indicate we are done.
        empty = [[]] * len(schema)
        empty_batch = pa.RecordBatch.from_arrays(empty, schema = schema)
        metadata_end = struct.pack('<i', 0)
        writer.write_with_metadata(empty_batch, metadata_end)
        buf = metadata.read()
        job_proto = sch_proto.JobStatus()
        if buf is not None:
          job_proto.ParseFromString(buf.to_pybytes())

        job = xgt.Job(self._xgt_server, job_proto)
        job_data = job.get_ingest_errors()

        if job_data is not None and len(job_data) > 0:
          raise xgt.XgtIOError(self.__create_ingest_error_message(frame, job), job = job)

    def __create_ingest_error_message(self, name, job):
        num_errors = job.total_ingest_errors

        error_string = ('Errors occurred when inserting data into frame '
                        f'{name}.\n')

        error_string += f'  {num_errors} line'
        if num_errors > 1:
          error_string += 's'

        error_string += (' had insertion errors.\n'
                         '  Lines without errors were inserted into the frame.\n'
                         '  To see the number of rows in the frame, run "'
                         f'{name}.num_rows".\n'
                         '  To see the data in the frame, run "'
                         f'{name}.get_data()".\n'
                         '  To see additional errors:\n'
                         '    try:\n'
                         '      foo.transfer_to_xgt(...)\n'
                         '    except xgt.XgtIOError as e:\n'
                         '      error_rows = e.job.get_ingest_errors()\n'
                         '      print(error_rows)\n')

        extra_text = ''
        if num_errors > 10:
          extra_text = ' first 10'

        error_string += (f'Errors associated with the{extra_text} lines '
                         'that could not be inserted are shown below:')

        # Only print the first 10 messages.
        for error in job.get_ingest_errors(0, 10):
          delim = ','

          # Will process a list of strings. Convert to this format.
          if isinstance(error, str):
            error_cols = error.split(delim)
          elif isinstance(error, list):
            error_cols = [str(elem) for elem in error]
          else:
            raise xgt.XgtIOError("Error processing ingest error message.")

          # The first comma separated fields of the error string are the error
          # description, file name, and line number.
          error_explanation = "" if len(error_cols) < 1 else error_cols[0]
          error_file_name = "odbc_transfer"
          error_line_number = "" if len(error_cols) < 3 else error_cols[2]

          # The second part of the error string contains the line that caused the
          # error. The line contains comma separated fields so we need to re-join
          # these comma separated portions to get back the line.
          line_with_error = \
              "" if len(error_cols) < 4 else delim.join(error_cols[3:])

          error_string += f"\n {error_explanation}"

        return error_string

    def __get_xgt_schema(self, table, max_text_size = None, max_binary_size = None):
        schema = self._driver._get_record_batch_schema(table, max_text_size, max_binary_size)
        return (_infer_xgt_schema_from_pyarrow_schema(schema, self._driver._conversions()), schema)

    def __extract_xgt_table_schema(self, table, mapping, max_text_size, max_binary_size):
        xgt_schema, arrow_schema = self.__get_xgt_schema(table, max_text_size, max_binary_size)
        return {'xgt_schema' : xgt_schema, 'arrow_schema' : arrow_schema, 'mapping' : mapping[table]}

    def __get_mapping(self, val, mapping_tables, mapping_vertices, mapping_edges):
        if isinstance(val, str):
            mapping_tables[val] = {'frame' : val}
        elif isinstance(val, tuple):
            # ('table', X, ...)
            if isinstance(val[1], str):
                # ('table', (...), ...)
                if len(val) == 3:
                    # ('table', (), ...)
                    if len(val[2]) == 1:
                        mapping_vertices[val[0]] = {'frame' : val[1], 'key' : val[2][0]}
                    # ('table', (,), ...)
                    elif len(val[2]) == 4:
                        mapping_edges[val[0]] = {'frame' : val[1], 'source' : val[2][0],
                                                 'target' : val[2][1], 'source_key' : val[2][2],
                                                 'target_key' : val[2][3]}
                else:
                    mapping_tables[val[0]] = {'frame' : val[1]}
            elif isinstance(val[1], tuple) and len(val[1]) == 1:
                mapping_vertices[val[0]] = {'frame' : val[0], 'key' : val[1][0]}
            elif isinstance(val[1], tuple) and len(val[1]) == 4:
                mapping_edges[val[0]] = {'frame' : val[0], 'source' : val[1][0],
                                         'target' : val[1][1], 'source_key' : val[1][2],
                                         'target_key' : val[1][3]}
            elif isinstance(val[1], dict):
                if len(val[1]) == 1:
                    mapping_tables[val[0]] = val[1]
                elif len(val[1]) == 2:
                    mapping_vertices[val[0]] = val[1]
                elif len(val[1]) == 5:
                    mapping_edges[val[0]] = val[1]
                else:
                    raise ValueError("Dictionary format incorrect for " + str(val[0]))
            else:
                raise ValueError("Argument format incorrect for " + str(val))

    def __copy_query_data_to_xgt(self, query, mapping, append, force, easy_edges,
                                 batch_size, transaction_size, max_text_size, max_binary_size,
                                 column_mapping, suppress_errors, row_filter, on_duplicate_keys):
        try:
            estimate = 0
            mapping_vertices = { }
            mapping_edges = { }
            mapping_tables = { }
            result = {'vertices' : dict(), 'edges' : dict(), 'tables' : dict()}
            self.__get_mapping(mapping, mapping_tables, mapping_vertices, mapping_edges)

            with ProgressDisplay(estimate) as progress_bar:
                reader = read_arrow_batches_from_odbc(
                    query=query,
                    connection_string=self._driver._connection_string,
                    batch_size=batch_size,
                    max_text_size=max_text_size,
                    max_binary_size=max_binary_size,
                )
                arrow_schema = reader.schema
                xgt_schema = _infer_xgt_schema_from_pyarrow_schema(arrow_schema, self._driver._conversions())
                for table in mapping_tables:
                    schema = {'xgt_schema' : xgt_schema, 'arrow_schema' : arrow_schema, 'mapping' : mapping_tables[table]}
                    result['tables'][table] = schema
                    frame = schema['mapping']['frame']

                for table in mapping_vertices:
                    schema = {'xgt_schema' : xgt_schema, 'arrow_schema' : arrow_schema, 'mapping' : mapping_vertices[table]}
                    result['vertices'][table] = schema
                    frame = schema['mapping']['frame']

                for table in mapping_edges:
                    schema = {'xgt_schema' : xgt_schema, 'arrow_schema' : arrow_schema, 'mapping' : mapping_edges[table]}
                    result['edges'][table] = schema
                    frame = schema['mapping']['frame']

                self.create_xgt_schemas(result, append, force, easy_edges)
                writer, metadata = self.__arrow_writer(frame, arrow_schema, column_mapping, suppress_errors, row_filter, on_duplicate_keys)
                count = 0
                bytes_transferred = 0
                row_count = 0
                for batch in reader:
                    bytes_transferred += sum(column.nbytes for column in batch)
                    # Process arrow batches
                    writer.write(batch)
                    progress_bar.show_progress(batch.num_rows)
                    count += batch.num_rows
                    row_count += batch.num_rows
                    # Start a new transaction
                    if transaction_size > 0 and count >= transaction_size:
                        count = 0
                        if (suppress_errors):
                            self.__check_for_error(frame, arrow_schema, writer, metadata)
                        writer.close()
                        writer, metadata = self.__arrow_writer(frame, arrow_schema, column_mapping, suppress_errors, row_filter, on_duplicate_keys)

                if (suppress_errors):
                    self.__check_for_error(frame, arrow_schema, writer, metadata)
                writer.close()

                return row_count, bytes_transferred
        except arrow_odbc.error.Error as e:
            if "too large to be written" in str(e):
                raise RuntimeError(
                    f"{e}\nHint: Try casting oversized columns with CAST(column AS VARCHAR(n)) "
                    "or changing the schema of the table to use a fixed size VARCHAR(n). "
                    "Variable text width columns sometimes report incorrect maximum sizes from drivers. "
                ) from e
            raise

    def __validate_column_mapping(self, column_mapping):
        error_msg = ('The data type of "column_mapping" is incorrect. '
                     'Expects a dictionary with string keys and string '
                     'or integer values.')
        if column_mapping is not None:
            if not isinstance(column_mapping, Mapping):
                raise TypeError(error_msg)
            for frame_col, file_col in column_mapping.items():
                if not isinstance(file_col, (str, int)):
                    raise TypeError(error_msg)
                if not isinstance(frame_col, str):
                    raise TypeError(error_msg)
