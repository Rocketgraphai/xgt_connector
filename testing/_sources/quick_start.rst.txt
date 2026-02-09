..
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

.. _quick_start:

Quick Start
===========

Installing
----------

In a separate terminal install the `Developer version of xGT with Docker <https://hub.docker.com/r/rocketgraph/xgt>`_ and run it:

.. code-block:: bash

   docker pull rocketgraph/xgt
   docker run --publish=4367:4367 rocketgraph/xgt

In another terminal install the connector:

.. code-block:: bash

   python -m pip install xgt_connector

Run a query
-----------

A simple example below shows connecting to Neo4j and xGT, transferring the whole graph database to xGT, running a query in xGT, and printing the results:

.. code-block:: python

   import xgt
   from xgt_connector import Neo4jConnector, Neo4jDriver

   # Connect to xGT and Neo4j.
   xgt_server = xgt.Connection()
   neo4j_server = Neo4jDriver(auth=('neo4j', 'foo'))
   conn = Neo4jConnector(xgt_server, neo4j_server)

   # Transfer the whole graph.
   conn.transfer_to_xgt()

   # Run the query.
   query = "match(a:foo) return a"
   job = xgt_server.run_job(query)

   # Print results.
   print("Results: ")
   for row in job.get_data():
       print(row)
