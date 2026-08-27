# xgt_connector Package

[![CI](https://github.com/rocketgraphai/xgt_connector/actions/workflows/pytest.yml/badge.svg)](https://github.com/rocketgraphai/xgt_connector/actions/workflows/pytest.yml)
[![Available on Pypi](https://img.shields.io/pypi/v/xgt_connector)](https://pypi.python.org/pypi/xgt_connector)
[![Pypi Versions](https://img.shields.io/pypi/pyversions/xgt_connector)](https://pypi.python.org/pypi/xgt_connector)
[![License](https://img.shields.io/github/license/rocketgraphai/xgt_connector)](https://github.com/rocketgraphai/xgt_connector/blob/main/LICENSE)
<!-- [![Twitter Follow](https://img.shields.io/twitter/follow/TrovaresxGT)](https://twitter.com/TrovaresxGT) -->

Move data into the Rocketgraph xGT graph analytics engine from the database you
already have, and back again. Rocketgraph xGT can
[significantly speed up Neo4j queries](https://rocketgraph.com/benchmarks-neo4j/).

### 📖 [Read the documentation](https://rocketgraphai.github.io/xgt_connector/)

The reference for every class, method and option lives there, along with a
[quick start](https://rocketgraphai.github.io/xgt_connector/quick_start.html)
and a guide to the [ODBC connector](https://rocketgraphai.github.io/xgt_connector/odbc).

| | |
| --- | --- |
| **Homepage** | [rocketgraph.com](https://www.rocketgraph.com) |
| **Documentation** | [rocketgraphai.github.io/xgt_connector](https://rocketgraphai.github.io/xgt_connector/) |
| **Questions** | [GitHub Discussions](https://github.com/rocketgraphai/xgt_connector/discussions) |
| **Changelog** | [RELEASE.rst](https://github.com/rocketgraphai/xgt_connector/blob/main/RELEASE.rst) |

## What it connects to

**Neo4j** is the default connector, and works with Neo4j 4.4 through the current
release, as well as AuraDB.

**ODBC** is an optional connector for anything that speaks it. There are drivers
for the dialects that need one:

| Driver | For |
| --- | --- |
| `SQLODBCDriver` | MySQL, MariaDB, PostgreSQL, SQLite, Databricks, and most others |
| `SQLServerODBCDriver` | Microsoft SQL Server |
| `OracleODBCDriver` | Oracle |
| `SAPODBCDriver` | SAP ASE and SAP IQ |
| `SnowflakeODBCDriver` | Snowflake |
| `MongoODBCDriver` | MongoDB, through an ODBC driver for it |

## Installation

```bash
python -m pip install xgt_connector
```

The ODBC connector needs its own dependencies:

```bash
python -m pip install 'xgt_connector[odbc]'
```

A running Rocketgraph xGT server is what everything here transfers into. If you
don't have one, the [Developer version](https://hub.docker.com/r/rocketgraphai/xgt)
runs in Docker:

```bash
docker pull rocketgraph/xgt
docker run --publish=4367:4367 rocketgraph/xgt
```

## Using the connector

Importing `xgt` and `xgt_connector` is all that is needed. This connects to Neo4j
and xGT, copies the whole graph across, runs a query and prints the results:

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

Transfer a chosen part of the graph rather than all of it:

```python
conn.transfer_to_xgt(vertices=['Person'], edges=['KNOWS'])
```

### From a SQL database

The ODBC connector works the same way. Give it a connection string and the
tables to bring across:

```python
import xgt
from xgt_connector import ODBCConnector, SQLODBCDriver

connection_string = 'Driver={MariaDB};Server=127.0.0.1;Port=3306;Database=test;Uid=test;Pwd=foo;'
xgt_server = xgt.Connection()
conn = ODBCConnector(xgt_server, SQLODBCDriver(connection_string))

# Bring a table across as an xGT table.
conn.transfer_to_xgt([('my_table', 'test_table')])
```

A SQL table can also be mapped onto vertex and edge frames rather than a plain
table, so that rows become a graph. Swap `SQLODBCDriver` for the driver of your
database from the table above, and see the
[ODBC guide](https://rocketgraphai.github.io/xgt_connector/odbc) for the mapping
forms, writing back with `transfer_to_odbc`, and per database notes.

## Performance

Bolt sends each row of a result as its own message, so a transfer that reads a
row at a time spends most of it on per row overhead rather than on the data. The
connector has Neo4j group `batch_size` rows into each message instead, which is
on by default.

Raising `batch_size` transfers faster, at the cost of Neo4j holding a larger
batch. Transferring 500,000 nodes of five properties each ran at these rates:

| `batch_size` | Speedup over a row at a time |
| --- | --- |
| 250 | 2.8x |
| 1000 (default) | 7.1x |
| 5000 | 10.9x |
| 20000 | 12.5x |

```python
conn = Neo4jConnector(xgt_server, neo4j_server, batch_size=20000)
```

The gain flattens out past 20,000 rows. `batch_size=None` reads a row at a time,
as releases before 3.0.0 did.

The optional [`neo4j-rust-ext`](https://pypi.org/project/neo4j-rust-ext/) package
replaces the bolt codec of the Neo4j driver with a compiled one, roughly halving
the time again:

```bash
python -m pip install 'xgt_connector[fast]'
```

It needs no code change, and is only worth installing together with batching:
decoding is not what a row at a time transfer spends its time on. See
[the documentation](https://rocketgraphai.github.io/xgt_connector/#transferring-larger-graphs)
for the full numbers.

None of this applies to the ODBC connector, which reads arrow batches straight
from the driver and hands them to xGT without building a python object per row.
`batch_size` there controls how many rows the ODBC driver buffers, and the
default suits most tables.

## API

Both connectors share the same shape. `transfer_to_xgt` is the one call most
uses need; the others are there when the schema and the copy want handling
separately.

| | |
| --- | --- |
| `get_xgt_schemas` | Work out what the frames in xGT should look like |
| `create_xgt_schemas` | Create them |
| `copy_data_to_xgt` | Copy the rows |
| `transfer_to_xgt` | All three at once |

`Neo4jConnector` also has `transfer_to_neo4j` and `translate_query`, and
`ODBCConnector` has `transfer_to_odbc` and `transfer_query_to_xgt`.

`Neo4jConnector` exposes what it learned about the Neo4j schema through
`neo4j_node_labels`, `neo4j_relationship_types`, `neo4j_property_keys`,
`neo4j_node_type_properties`, `neo4j_rel_type_properties`, `neo4j_nodes` and
`neo4j_edges`.

Every parameter is described in the
[API reference](https://rocketgraphai.github.io/xgt_connector/#api-details).

## Examples

  - [Python examples](https://github.com/rocketgraphai/xgt_connector/tree/main/examples)
  - [Jupyter notebooks](https://github.com/rocketgraphai/xgt_connector/tree/main/jupyter)
