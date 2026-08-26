# xgt_connector Package

[![CI](https://github.com/rocketgraphai/xgt_connector/actions/workflows/pytest.yml/badge.svg)](https://github.com/rocketgraphai/xgt_connector/actions/workflows/pytest.yml)
[![Available on Pypi](https://img.shields.io/pypi/v/xgt_connector)](https://pypi.python.org/pypi/xgt_connector)
[![Pypi Versions](https://img.shields.io/pypi/pyversions/xgt_connector)](https://pypi.python.org/pypi/xgt_connector)
[![License](https://img.shields.io/github/license/rocketgraphai/xgt_connector)](https://github.com/rocketgraphai/xgt_connector/blob/main/LICENSE)
<!-- [![Twitter Follow](https://img.shields.io/twitter/follow/TrovaresxGT)](https://twitter.com/TrovaresxGT) -->

This Python package is for connecting the Rocketgraph xGT graph analytics engine to other applications.
Rocketgraph xGT can [significantly speedup Neo4j queries](https://rocketgraph.com/benchmarks-neo4j/).

The default connector provided is for Neo4j or AuraDB.
The package also provides an optional ODBC connector for connecting to databases or applications that support ODBC.
Information about the ODBC connector can be found [in the documentation](https://rocketgraphai.github.io/xgt_connector/odbc). 

<table>
  <tr>
    <td><b>Homepage:</b></td>
    <td><a href="https://www.rocketgraph.com">rocketgraph.com</a></td>
  </tr>
  <tr>
    <td><b>Documentation:</b></td>
    <td><a href="https://rocketgraphai.github.io/xgt_connector/">rocketgraphai.github.io/xgt_connector</a></td>
  </tr>
  <tr>
    <td><b>General Help:</b></td>
    <td><a href="https://github.com/rocketgraphai/xgt_connector/discussions">github.com/rocketgraphai/xgt_connector/discussions</a></td>
  </tr>
</table>

## Requirements

 - [Neo4j Python](https://pypi.org/project/neo4j/)
 - [xGT Python](https://pypi.org/project/xgt/)
 - [Pyarrow](https://pypi.org/project/pyarrow/)
 - [Rocketgraph xGT](https://www.rocketgraph.com)

## Installation

You can install this python package by executing this command:

```bash
python -m pip install xgt_connector
```

If you want to use the ODBC connector, you can install the optional dependencies like so:
```bash
python -m pip install 'xgt_connector[odbc]'
```

For faster transfers out of Neo4j, the `fast` extra adds a compiled bolt codec:
```bash
python -m pip install 'xgt_connector[fast]'
```
Pass `batch_size` to `Neo4jConnector` to use it.

If you don't have Rocketgraph xGT, you can install and run the [Developer version](https://hub.docker.com/r/rocketgraphai/xgt) from Docker:

```bash
docker pull rocketgraph/xgt
docker run --publish=4367:4367 rocketgraph/xgt
```
## Using the xgt_connector

From any Python environment, simply importing both `xgt` and `xgt_connector` is all that is needed to operate this connector.

A simple example below shows connecting to Neo4j and xGT, transferring the whole graph database to xGT, running a query in xGT, and printing the results:

```python
import xgt
from xgt_connector import Neo4jConnector, Neo4jDriver

# Connect to xGT and Neo4j.
xgt_server = xgt.Connection()
xgt_server.set_default_namespace('neo4j')
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
```

## API

The available properties are:

  - neo4j_relationship_types
  - neo4j_node_labels
  - neo4j_property_keys
  - neo4j_node_type_properties
  - neo4j_rel_type_properties
  - neo4j_nodes
  - neo4j_edges

The available methods are:

  - get_xgt_schemas
  - create_xgt_schemas
  - copy_data_to_xgt
  - transfer_to_xgt
  - transfer_to_neo4j

## Examples

Some examples can be found here:

  - [Python examples](https://github.com/rocketgraphai/xgt_connector/tree/main/examples)
  - [Jupyter notebooks](https://github.com/rocketgraphai/xgt_connector/tree/main/jupyter)
