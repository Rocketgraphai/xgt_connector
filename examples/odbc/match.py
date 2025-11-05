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

# This example creates a graph in SQL, transfers it to xGT, and
# runs a query on it in xGT.

from xgt_connector import ODBCConnector, SQLODBCDriver
import pyodbc
import xgt

xgt_server = xgt.Connection()

connection_string = 'Driver={MariaDB};Server=127.0.0.1;Port=3306;Database=test;Uid=test;Pwd=foo;'
odbc_driver = SQLODBCDriver(connection_string)
c = ODBCConnector(xgt_server, odbc_driver)
pyodbc_driver = pyodbc.connect(connection_string)
cursor = pyodbc_driver.cursor()

# Uncomment to delete the tables 
"""
cursor.execute('DROP TABLE IF EXISTS Knows')
cursor.execute('DROP TABLE IF EXISTS Person')
pyodbc_driver.commit()
"""

# Create a chain with with a loop in SQL. 
cursor.execute('CREATE TABLE Person (id INT)')
cursor.execute('CREATE TABLE Knows (Person1 INT, Person2 INT)')
cursor.execute('INSERT INTO Person VALUES (0)')
for i in range(0, 10):
    cursor.execute(f'INSERT INTO Person VALUES ({i + 1})')
    cursor.execute(f'INSERT INTO Knows VALUES ({i}, {i + 1})')
cursor.execute('INSERT INTO Knows VALUES (2, 0)')
pyodbc_driver.commit()
pyodbc_driver.close()

# Transfer edges from SQL to xGT
c.transfer_to_xgt(tables=[('Person', ('id',)), ('Knows', ('Person', 'Person', 'Person1', 'Person2'))])

# Alternatively these can be transfered via arbitrary queries:
"""
c.transfer_query_to_xgt('SELECT * FROM Person', mapping=('XgtPerson', ('id',)))
c.transfer_query_to_xgt('SELECT * FROM Knows', mapping=('XgtKnows', ('XgtPerson', 'XgtPerson', 'Person1', 'Person2')))
"""

# Look for the loop
query = 'match(a)-->()-->()-->(a) return a.id'

# Get results with xGT
job = xgt_server.run_job(query)
print('xGT found the following nodes in a triangle: ' + ','.join(str(row[0]) for row in job.get_data()))
xgt_server.drop_namespace('odbc_test', force_drop=True)
