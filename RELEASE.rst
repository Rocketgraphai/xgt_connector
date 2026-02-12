Release Notes
=============

2.6.6 (02-11-2026)
------------------

Changed
^^^^^^^
  - Added support for Python 3.14.

Fixed
^^^^^
  - Transfers not working with pandas 3.0.

2.6.5 (11-05-2025)
------------------

Changed
^^^^^^^
  - Give hints when column doesn't fit in buffer size.

2.6.4 (02-25-2025)
------------------

Changed
^^^^^^^
  - Renamed python module from trovares_connector to xgt_connector.

2.6.3 (02-12-2025)
------------------

New Features
^^^^^^^^^^^^
  - Add support for python 3.13.

Changed
^^^^^^^
  - Drop support for python 3.7 and 3.8.

2.6.2 (10-15-2024)
------------------

New Features
^^^^^^^^^^^^
  - Transfer query now returns row count and byte count of the transfer.

2.6.1 (10-02-2024)
------------------

Fixed
^^^^^
  - Allow for fully qualified names when mapping.

2.6.0 (02-20-2024)
------------------

New Features
^^^^^^^^^^^^
  - Added paramaters for column mapping.

2.5.0 (02-14-2024)
------------------

New Features
^^^^^^^^^^^^
  - Added type hints.

Fixed
^^^^^
  - pyarrow warning about schema parameter.

2.4.0 (02-06-2024)
------------------

New Features
^^^^^^^^^^^^
  - Added parameters for error suppression, row filtering, and duplicate vertex handling.

2.3.0 (12-18-2023)
------------------

New Features
^^^^^^^^^^^^
  - Added Snowflake specific ODBC driver with ANSI int conversion.
  - Add parameters for controlling max text/binary size when transferring from ODBC to xGT.

Fixed
^^^^^
  - When using easy edges, the type of the vertex will now conform to the edge type instead of assuming it is an int.

2.2.0 (12-07-2023)
------------------

Changed
^^^^^^^
  - Expand ODBC support to Databricks.
  - py2neo support deprecated.
  - Warn about using deprecated connectors.

2.1.0 (08-23-2023)
------------------

New Features
^^^^^^^^^^^^
  - Added support to change transaction size when transferring from ODBC to xGT.

2.0.0 (06-14-2023)
------------------

Changed
^^^^^^^
  - Require xGT 1.14.

Fixed
^^^^^
  - Warnings about deprecated functions.

1.7.0 (02-22-2023)
------------------

New Features
^^^^^^^^^^^^
  - Added SAP driver that supports downloading from SAP ASE.

1.6.0 (10-21-2022)
------------------

New Features
^^^^^^^^^^^^
  - Added Oracle driver that supports downloading from Oracle.
  - Added support for transferring arbitrary queries to xGT.

Fixed
^^^^^
  - Documentation errors.

1.5.2 (08-26-2022)
------------------

Changed
^^^^^^^
  - Reuse Arrow connection on xGT 1.11+.

1.5.1 (07-29-2022)
------------------

New Features
^^^^^^^^^^^^
  - Added null support when writing to ODBC applications.

1.5.0 (07-29-2022)
------------------

New Features
^^^^^^^^^^^^
  - Added query translator for Neo4j connector to better support running queries on data with multiple labels.

1.4.0 (07-26-2022)
------------------

New Features
^^^^^^^^^^^^
  - Added support for transferring data from xGT to applications that support ODBC.
  - Add MongoDB driver for improved MongoDB support.

Changed
^^^^^^^
  - Can now transfer tables/databases via ODBC without data.

Fixed
^^^^^
  - Fixed tables not dropping automatically on transfer for ODBC.

1.3.1 (07-11-2022)
------------------
Fixed
^^^^^
  - Fixed odbc import issue if ODBC not installed.

1.3.0 (07-08-2022)
------------------
New Features
^^^^^^^^^^^^
  - Added ODBC connector for transferring from applications that support ODBC to xGT.

1.2.1 (07-01-2022)
------------------
Fixed
^^^^^
  - Fixed python dependencies not installing on pip install.

1.2.0 (06-24-2022)
------------------

New Features
^^^^^^^^^^^^
  - Added support for unlabeled nodes.
  - Added support for mapping Neo4j labels and types to xGT.
  - Added option to disable auto-downloading edges' source and target vertices.

Changed
^^^^^^^
  - Improved download estimates for single relationships with multiple nodes.
  - Rename disable_apoc to enable_apoc.
  - Endpoints are now returned as a tuple of source and target instead of a string.
  - Documentation improvements.

1.1.0 (06-17-2022)
------------------

New Features
^^^^^^^^^^^^
  - Added support for point and list data types.

Changed
^^^^^^^
  - Documentation improvements.

Fixed
^^^^^
  - Transferring empty frame/graph causes divide by 0.
  - When transferring to Neo4j from xGT use the default namespace when all values are None.

1.0.0 (06-13-2022)
------------------

New Features
^^^^^^^^^^^^
  - Initial Release.
  - Added support for transferring graph data from Neo4j to xGT.
  - Added support for transferring graph data from xGT to Neo4j.
  - Provided methods for querying Neo4j's data schema.
