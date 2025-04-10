..
   # -*- coding: utf-8 -*- --------------------------------------------------===#
   #
   #  Copyright 2022-2023 Trovares Inc.
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

.. _requirements:

Requirements
============

* `Neo4j Python package <https://pypi.org/project/neo4j/>`_ >= 4.4.1
* `xGT Python package <https://pypi.org/project/xgt/>`_ >= 1.14.0
* `Pyarrow package <https://pypi.org/project/pyarrow/>`_ >= 7.0.0
* `Rocketgraph xGT <https://www.rocketgraph.com>`_ >= 1.14.0

The Python packages can be installed through pip:

.. code-block:: bash

   python -m pip install xgt neo4j pyarrow

If you don't have Rocketgraph xGT, you can install and run the `Developer version <https://hub.docker.com/r/rocketgraph/xgt>`_ from Docker:

.. code-block:: bash

   docker pull rocketgraph/xgt
   docker run --publish=4367:4367 rocketgraph/xgt

Optional
--------

* `APOC <https://github.com/neo4j-contrib/neo4j-apoc-procedures>`_
   Improves schema querying.
   Available as an option to be turned on with the connector.

ODBC
^^^^

To use the optional ODBC connection features, the following packages are required:

* `Arrow ODBC <https://pypi.org/project/arrow_odbc/>`_
* `Pandas <https://pypi.org/project/pandas/>`_
* ODBC Driver for your database and an ODBC Driver manager such unixODBC.
