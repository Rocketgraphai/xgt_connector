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

.. xgt_connector documentation master file, created by
   sphinx-quickstart on Fri Apr 29 15:54:24 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. role:: nocap
   :class: nocap

.. |xgt| replace:: :nocap:`xGT`

|xgt| Connector
===============

This Python package is for connecting the `Rocketgraph xGT <https://www.rocketgraph.com/>`_ graph analytics engine with various applications.
Rocketgraph xGT can `significantly speedup Neo4j queries <https://rocketgraph.com/benchmarks-neo4j/>`_.

The connector `source code <http://github.com/rocketgraphai/xgt_connector/>`_ is available on github.

A basic guide is provided below.
For a quick start see :ref:`quick_start`.

The default connector provided is for connecting to Neo4j or AuraDB.
The package also provides an optional :ref:`odbc` for connecting to databases or applications that support ODBC.

Installation
------------

You can install this python package by executing this command:

.. code-block:: bash

   python -m pip install xgt_connector

If you don't have Rocketgraph xGT, it is available through the AWS Marketplace or you can use the `Developer version of xGT with Docker <https://hub.docker.com/r/rocketgraph/xgt>`_:

.. code-block:: bash

   docker pull rocketgraph/xgt
   docker run --publish=4367:4367 rocketgraph/xgt

For requirements and optional components see :ref:`requirements`.

Using the |xgt| Connector
-------------------------

From any Python environment, simply importing both `xgt` and `xgt_connector` is all that is needed to operate this connector.

.. code-block:: python

   import xgt
   from xgt_connector import Neo4jConnector

Examples
--------

These examples show typical usage patterns.

Copy entire graph from Neo4j to Rocketgraph |xgt|
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This example uses two properties of the connector object that return a list of all of the node labels (vertex types) and all of the relationship types (edge types) in the Neo4j data.
All of these data frames are created in Rocketgraph xGT and then all of the data is copied from Neo4j to xGT.

.. code-block:: python

   import xgt
   from xgt_connector import Neo4jConnector, Neo4jDriver

   xgt_server = xgt.Connection()
   neo4j_server = Neo4jDriver(auth=('neo4j', 'foo'))
   conn = Neo4jConnector(xgt_server, neo4j_server)

   conn.transfer_to_xgt(vertices=conn.neo4j_node_labels,
                        edges=conn.neo4j_relationship_types)

Similarly if no vertices or edges are provided, the transfer will use all of them.

.. code-block:: python

   conn.transfer_to_xgt()

Copy a portion of a graph based on node labels and/or relationship types
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In this example, only some of the node labels (vertex types) and some of the relationship types (edge types) are copied into Rocketgraph xGT.
Using this idiom requires knowing some schema information about the graph data stored in Neo4j.

.. code-block:: python

   import xgt
   from xgt_connector import Neo4jConnector, Neo4jDriver

   xgt_server = xgt.Connection()
   neo4j_server = Neo4jDriver(auth=('neo4j', 'foo'))
   conn = Neo4jConnector(xgt_server, neo4j_server)

   nodes_to_copy = ['Person']
   edges_to_copy = ['KNOWS']
   conn.transfer_to_xgt(vertices=nodes_to_copy, edges=edges_to_copy)

When transferring, vertex types will be auto-inferred and transferred with edge types.
The code below would auto-transfer the Person node.

.. code-block:: python

   conn.transfer_to_xgt(edges=edges_to_copy)

This feature can be disabled by setting `import_edge_nodes` to False.

Appending data
^^^^^^^^^^^^^^

By default a transfer will drop any associated frame on xGT.
To append to a frame, set `append` to True on the transfer.

.. code-block:: python

   conn.transfer_to_xgt(vertices=['Person'], append=True)

When appending edges to existing vertices, care must be taken to not import the nodes as well.

.. code-block:: python

   conn.transfer_to_xgt(edges=['Person'], append=True, import_edge_nodes=False)

Mapping Neo4j labels and types
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When transferring, labels and relationship types are automatically mapped to the same name in xGT.
The exception is that unlabeled vertices are mapped to the frame "unlabeled" because xGT doesn't support empty names.
It's possible to change the mapping of any label or relationship type by passing a pair where the first element represents the Neo4j label or relationship type and the second represents the xGT type.

An example of changing the mapping of Person and KNOWS, but not Job:

.. code-block:: python

   conn.transfer_to_xgt(vertices=[('Person', 'p'), 'Job'], edges=[('KNOWS', 'k')])

In addition the unlabeled nodes in Neo4j are named '' and this can be used to map these to a custom xGT type:

.. code-block:: python

   conn.transfer_to_xgt(vertices=[('', 'my_empty_type')])

Connecting to AuraDB
^^^^^^^^^^^^^^^^^^^^
The connector can connect to AuraDB instances by setting the hostname and appropriate protocol:

.. code-block:: python

   import xgt
   from xgt_connector import Neo4jConnector, Neo4jDriver
   from neo4j import GraphDatabase

   xgt_server = xgt.Connection()
   # The protocol would be the part before ://. Usually this is neo4j+s.
   neo4j_server = Neo4jDriver(protocol='neo4j+s', hostname='hostname <something like ashdjs43.databases.neo4j.io>', auth=('neo4j', 'foo'))
   conn = Neo4jConnector(xgt_server, neo4j_server)


Using various Neo4j drivers
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The connector supports passing a xgt_connector.Neo4jDriver, neo4j.BoltDriver, or a neo4j.Neo4jDriver.
The Rocketgraph Neo4jDriver provides support for connecting to the Neo4j server through a combination of choices such as http, arrow, bolt, or other drivers.
These additional drivers can provide much faster performance than the default neo4j.Neo4jDriver, but may require the optional components as explained in :ref:`requirements`.

Some examples of connecting:

.. code-block:: python

   import xgt
   from xgt_connector import Neo4jConnector, Neo4jDriver
   from neo4j import GraphDatabase

   xgt_server = xgt.Connection()

   neo4j_driver = GraphDatabase.driver("bolt://localhost", auth=('neo4j', 'foo'))

   # Using Neo4j's Python driver.
   conn = Neo4jConnector(xgt_server, neo4j_driver)

   # Using Neo4j's Python driver with a specific database.
   conn = Neo4jConnector(xgt_server, (neo4j_driver, 'my_database'))

   # Using the Rocketgraph Neo4j driver with bolt.
   neo4j_driver = Neo4jDriver(auth=('neo4j', 'foo'))
   conn = Neo4jConnector(xgt_server, neo4j_driver, database='my_database')

These additional connectors will connect to Neo4j with a combination of connections currently and may have some limitations.

Additional Examples
^^^^^^^^^^^^^^^^^^^

More detailed examples can be found in :ref:`jupyter` or on github:

* `Python Examples <https://github.com/rocketgraphai/xgt_connector/tree/main/examples/neo4j>`_
* `Jupyter Notebooks <https://github.com/rocketgraphai/xgt_connector/tree/main/jupyter/neo4j>`_

Limitations
-----------

Doesn't support the following:

* Multiple types for a single property.

Other limitations:

* Duration data type is converted into an integer representing nanoseconds.
* Multiple labels on a single node will translate into multiple nodes in xGT.
* Multiple node types for a single relationship type will translate the single relationship into multiple distinct relationship types.
  See below for more details.
* Point data type is converted into a list.
* Unlabeled vertices are supported, but will be typed with the name "unlabeled" by default.
* Transfer times are estimates based on Neo4j's count stores and may be inaccurate especially for edges going to multiple node labels.

Single relationship with multiple node conversion
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

xGT is schema based and requires an edge to have distinct types.
Neo4j is schema-less so can have multiple node types per edge type.
In the case where the are multiple node types for single edge type, the connector will convert the single edge type in Neo4j into multiple edge types in xGT.
xGT will take the original edge type and create edge types in the format: source_label + _ + edge_label + _ target_label.
This only occurs for these cases.

An example would be the following schema in Neo4j:

.. code-block:: cypher

  (:A)-[:PART_OF]->(:B)-[:PART_OF]->(:C)-[:PART_OF]->(:D)

Would get converted to the following when transferring to xGT:

.. code-block:: cypher

  (:A)-[:A_PART_OF_B]->(:B)-[:B_PART_OF_C]->(:C)-[:C_PART_OF_D]->(:D)

In addition, multiple labels on a single node will cause a similar behavior:

.. code-block:: cypher

  (:A:B)-[:PART_OF]->(:C)

Would get converted to the following when transferring to xGT:

.. code-block:: cypher

  (:A)-[:A_PART_OF_C]->(:C), (:B)-[:B_PART_OF_C]->(:C)

Translating Cypher queries
^^^^^^^^^^^^^^^^^^^^^^^^^^

Because of the translation of names from Relationship Types in Neo4j to Edge Frame names in xGT, Cypher queries that work in Neo4j may not work in xGT.
To aid in translating Cypher from the Neo4j version to the inferred graph schema in xGT, there is a `query_translate` method in the `Neo4jConnector` class (see :ref:`API_details`).


Additional Topics
-----------------

The following topics provide additional material.

.. toctree::
  :maxdepth: 2
  :caption: Additional Topics

  quick_start.rst
  jupyter/index.rst
  odbc/index.rst
  requirements.rst
  RELEASE.rst

.. _API_details:

API Details
-----------

.. currentmodule:: xgt_connector

.. automodule:: xgt_connector
  :no-members:
  :no-inherited-members:
  :noindex:

.. autosummary::
  :toctree:
  :caption: Python API

  Neo4jConnector
  Neo4jDriver
