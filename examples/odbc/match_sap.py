#!/usr/bin/env python
# -*- coding: utf-8 -*- --------------------------------------------------===#
#
#  Copyright 2022-2025 Trovares Inc.
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

# This example creates a graph in SAP ASE/IQ SQL, transfers it to xGT, and
# runs a query on it in xGT.

from xgt_connector import ODBCConnector, SAPODBCDriver
import pyodbc
import xgt

xgt_server = xgt.Connection()

# This could be either your ASE or IQ driver.
connection_string = 'Driver={ASE};Database=test;Uid=sa;Pwd=test;Server=localhost;Port=5000;'
odbc_driver = SAPODBCDriver(connection_string)
c = ODBCConnector(xgt_server, odbc_driver)
pyodbc_driver = pyodbc.connect(connection_string, autocommit=True)
cursor = pyodbc_driver.cursor()

# Uncomment to delete the tables
"""
cursor.execute('DROP TABLE Person')
cursor.execute('DROP TABLE Knows')
pyodbc_driver.commit()
"""

# Create some tables in SAP ASE/IQ SQL.
# The table Person has 1 column called key.
cursor.execute('CREATE TABLE Person (KeyID INT)')
# The table Knows has 5 columns: Person1, Person2, Relationship, Prop1, and Prop2.
cursor.execute('CREATE TABLE Knows (Person1 INT, Person2 INT, Relationship VARCHAR(50), Prop1 INT, Prop2 INT)')
cursor.execute('INSERT INTO Person VALUES (0)')
for i in range(0, 10):
    cursor.execute(f'INSERT INTO Person VALUES ({i + 1})')
    cursor.execute(f'INSERT INTO Knows VALUES ({i}, {i + 1}, \'FRIENDS\', {i + 2}, 0)')
cursor.execute('INSERT INTO Knows VALUES (2, 0, \'PARTNERS\', 4, 1)')
pyodbc_driver.commit()
pyodbc_driver.close()

# Transfer vertices/edges from SQL to xGT:
c.transfer_to_xgt(tables=[('Person', ('KeyID',)),
                          ('Knows', ('Person', 'Person', 'Person1', 'Person2'))
                         ])
# Here we are specifying multiple tables with a mapping syntax to transfer.
# The mapping syntax is given in tuple form as (SQL_TABLE, (XGT_TYPE)) where the tuple format specifies how to map the table to an xGT type.
# The first tuple of tuples is for the Table Person given by (SQL_TABLE, (KEY_COL,)).
# This will create a Vertex frame in xGT titled SQL_TABLE and transfer the whole table to it.
# It will use KEY_COL as the xGT key.
# The second tuple of tuples is for the Table Person given by (SQL_TABLE, (XGT_SRC_FRAME, XGT_TRG_FRAME, SRC_KEY_COL, TRG_KEY_COL))
# This will create an Edge frame in xGT titled SQL_TABLE and transfer the whole table to it.
# It will use XGT_SRC_FRAME and XGT_TRG_FRAME as the Vertex frames for source and target.
# It will use SRC_KEY_COL and TRG_KEY_COL as the key columns for source and target.

xgt_server.drop_frame('Knows')
xgt_server.drop_frame('Person')

# Alternatively these can be transferred via arbitrary queries:
# This is the same as above except it is transferring via an SQL match where it can select any number of columns.
# Here only 1 mapping is specified per match and it will map from the SQL query to mapping.
# The mapping here is given as (XGT_FRAME_NAME, (XGT_TYPE)) where (XGT_TYPE) is the same format above.
# Transfer Person to XgtPerson.
c.transfer_query_to_xgt('SELECT * FROM Person', mapping=('XgtPerson', ('KeyID',)))

# Transfer Knows to XgtKnows. This will transfer all the columns returned by the query.
# So Person1, Person2, Relationship, Prop1, and Prop2.
c.transfer_query_to_xgt('SELECT * FROM Knows', mapping=('XgtKnows', ('XgtPerson', 'XgtPerson', 'Person1', 'Person2')))

xgt_server.drop_frame('XgtKnows')
xgt_server.drop_frame('XgtPerson')

# Alternatively you can create the vertices and vertex frames by specifying easy_edges when transferring edges.
# The key column for the vertex frames will be called key.
# Like before this will transfer all the columns.
print('\n')
c.transfer_query_to_xgt('SELECT * FROM Knows', mapping=('XgtKnows', ('XgtPerson', 'XgtPerson', 'Person1', 'Person2')), easy_edges=True)

print('The follow table data was transferred for the Edges with query, SELECT * FROM "Knows":')
print(xgt_server.get_frame('XgtKnows').get_data())
print('\n')

xgt_server.drop_frame('XgtKnows')
xgt_server.drop_frame('XgtPerson')

# You can run any query, so you can pull data from SAP ASE/IQ whatever way you wish.
# For instance, this would transfer 3 of the columns and change their order stored in ASE/IQ:
c.transfer_query_to_xgt('SELECT Relationship, Person1, Person2 FROM Knows', mapping=('XgtKnows', ('XgtPerson', 'XgtPerson', 'Person1', 'Person2')), easy_edges=True)

print('The follow table data was transferred for the Edges with query, SELECT Relationship, Person1, Person2 FROM Knows:')
print(xgt_server.get_frame('XgtKnows').get_data())
print('\n')

# Look for a loop
query = 'match(a)-->()-->()-->(a) return a.key'

# Get results with xGT
job = xgt_server.run_job(query)
print('xGT found the following nodes in a triangle: ' + ','.join(str(row[0]) for row in job.get_data()))
xgt_server.drop_namespace('odbc_test', force_drop=True)
