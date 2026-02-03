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

import datetime
import pyarrow as pa
import pyarrow.flight as pf

import neo4j
import xgt
import os
import time
import warnings
from enum import Enum
from ..common import ProgressDisplay
from ..common import BasicArrowClientAuthHandler

from .query_translator import QueryTranslator

class Neo4jDriver(object):
    def __init__(self, host = 'localhost',
                       bolt_port = 7687, http_port = 7474,
                       arrow_port = 9999, auth = None,
                       database = neo4j.DEFAULT_DATABASE,
                       driver = 'neo4j-bolt',
                       protocol = 'neo4j',
                       http_protocol = 'http',
                       verbose = False):
        """
        Initializes the driver class.

        Parameters
        ----------
        host : str
            Host address of the Neo4j server.
        bolt_port : int
            Bolt port of the Neo4j server.
        http_port : int
            HTTP port of the Neo4j server.
            Used with HTTP drivers.
        arrow_port : int
            Arrow port of the Neo4j server.
            Used with Arrow driver.
        auth : neo4j.Auth
            Authentication details.
        database : str
            Neo4j database to connect to.
        driver : str
            Driver to use for transferring data from Neo4j.
            Options include 'neo4j-bolt', 'py2neo-bolt', 'py2neo-http', and 'neo4j-arrow'.
            Some connections, such as schema querying will still go through 'neo4j-bolt',
            but all data transferring will use the method selected here.
            'neo4j-arrow' is considered very experimental.
            See the documentation for requirements for using.
        protocol : str
            Protocol used when connecting to Neo4j through bolt.
            Acceptable values include: neo4j, neo4j+s, neo4j+ssc, bolt, bolt+s, and bolt+ssc.
        http_protocol : str
            Protocol used when connecting to Neo4j through http with http drivers.
            Acceptable values include: http, https, http+s, http+ssc.
        verbose : bool
            Print detailed information during calls.
        """
        if not isinstance(host, (neo4j.Neo4jDriver, neo4j.BoltDriver)):
            self._host = host
            self._bolt_port = bolt_port
            self._http_port = http_port
            self._arrow_port = arrow_port
            self._auth = auth
            self._protocol = protocol
            self._http_protocol = http_protocol
            # neo4j arrow can't take none as a parameter for the database.
            self._database_arrow = 'neo4j' if database == None else database
            driver_passed_in = False
        else:
            driver_passed_in = True

        self._database = database
        self.__verbose = verbose

        # These are just kept as separate variables because they may be needed
        self._neo4j_driver = None
        self._py2neo_driver = None
        self._arrow_driver = None

        if self.__verbose:
            print('Using ' + driver + ' for transfers of data.')

        if driver_passed_in:
            self._neo4j_driver = host
        else:
            self._neo4j_driver = neo4j.GraphDatabase.driver(f"{self._protocol}://{self._host}",
                                                            auth=self._auth)
        if driver == 'neo4j-bolt':
            pass
        elif driver == 'py2neo-bolt':
            from py2neo import Graph
            warnings.warn("Py2neo support will be dropped in next major release.", FutureWarning)
            self._py2neo_driver = Graph(
                self._protocol + "://" + self._host + ":" +str(bolt_port),
                auth=auth, name=database)
        elif driver == 'py2neo-http':
            from py2neo import Graph
            warnings.warn("Py2neo support will be dropped in next major release.", FutureWarning)
            self._py2neo_driver = Graph(
                self._http_protocol + "://" + self._host + ":" +str(http_port),
                auth=auth, name=database)
        elif driver == 'neo4j-arrow':
            import neo4j_arrow as na
            warnings.warn("Neo4j arrow support will be dropped in next major release.", FutureWarning)
            self._arrow_driver = na.Neo4jArrow(self._auth[0],
                                               self._auth[1])
        else:
            raise ValueError(f"Unknown driver, {driver}.")

    @classmethod
    def from_Neo4jDriver(self, neo4j_driver,
                         database = neo4j.DEFAULT_DATABASE):
        return Neo4jDriver(neo4j_driver, database = database)

    @property
    def bolt(self) -> neo4j.Neo4jDriver:
        """
        Retrieve the Python bolt driver connected to the Neo4j database.

        Returns
        -------
        neo4j.Neo4jDriver
          The Python bolt driver object that is connected to the Neo4j database.
        """
        return self._neo4j_driver

    def query(self, query, write=True, use_neo4j_always=False):
        """
        Runs the query on Neo4j as returns the results.

        Parameters
        ----------
        write : write
          If true, the query can write to the database.
          By default this is True.

        use_neo4j_always : bool
          If true uses the neo4j.Neo4jDriver to run the query.
          Otherwise will attempt to use a faster driver if set such as py2neo.
          By default this is False.

        Returns
        -------
        object
          Closure object with results.
        """
        if not use_neo4j_always and self._py2neo_driver is not None:
            return self.py2neo_run_closure(self, query, write)
        else:
            return self.neo4j_run_closure(self, query, write)

    class py2neo_run_closure():
        def __init__(self, connector, query, write):
            if write:
                self._result = connector._py2neo_driver.run(query)
            else:
                self._result = connector._py2neo_driver.query(query)

        def __enter__(self):
            return self

        def __exit__(self, exc_type,exc_value, exc_traceback):
            pass

        def result(self):
            return self._result

        def finalize(self):
            pass

    class neo4j_run_closure():
        def __init__(self, connector, query, write):
            self._query = query
            self._connector = connector
            self._closed = False
            if write:
                self._session = self._connector._neo4j_driver.session(database=self._connector._database,
                                                                      default_access_mode=neo4j.WRITE_ACCESS)
            else:
                self._session = self._connector._neo4j_driver.session(database=self._connector._database,
                                                                      default_access_mode=neo4j.READ_ACCESS)
        def __enter__(self):
            return self

        def __exit__(self, exc_type,exc_value, exc_traceback):
            self.finalize()

        def result(self):
            return self._session.run(self._query)

        def finalize(self):
            for result in self.result():
                pass
            if not self._closed:
                self._session.close()
                self._close = True

class Neo4jConnector(object):
    _NEO4J_TYPE_TO_XGT_TYPE = {
        'INTEGER': (xgt.INT,),
        'Long': (xgt.INT,),
        'FLOAT': (xgt.FLOAT,),
        'Double': (xgt.FLOAT,),
        'STRING': (xgt.TEXT,),
        'String': (xgt.TEXT,),
        'Boolean': (xgt.BOOLEAN,),
        'Date': (xgt.DATE,),
        'Time': (xgt.TIME,),
        'DateTime': (xgt.DATETIME,),
        'LocalTime': (xgt.TIME,),
        'LocalDateTime': (xgt.DATETIME,),
        'Duration': (xgt.INT,),
        'Point': (xgt.LIST, xgt.FLOAT, 1),
        'BooleanArray': (xgt.LIST, xgt.BOOLEAN, 1),
        'LongArray': (xgt.LIST, xgt.INT, 1),
        'DoubleArray': (xgt.LIST, xgt.FLOAT, 1),
        'StringArray': (xgt.LIST, xgt.TEXT, 1),
        'DateArray': (xgt.LIST, xgt.DATE, 1),
        'TimeArray': (xgt.LIST, xgt.TIME, 1),
        'DateTimeArray': (xgt.LIST, xgt.DATETIME, 1),
        'LocalTimeArray': (xgt.LIST, xgt.TIME, 1),
        'LocalDateTimeArray': (xgt.LIST, xgt.DATETIME, 1),
        'DurationArray': (xgt.LIST, xgt.INT, 1),
        'PointArray': (xgt.LIST, xgt.FLOAT, 2),
    }

    _NEO4J_TYPE_TO_ARROW_TYPE = {
        'INTEGER': pa.int64(),
        'Long': pa.int64(),
        'FLOAT': pa.float32(),
        'Double': pa.float32(),
        'STRING': pa.string(),
        'String': pa.string(),
        'Boolean': pa.bool_(),
        'Date': pa.date32(),
        'Time': pa.time64('us'),
        'DateTime': pa.timestamp('us'),
        'LocalTime': pa.time64('us'),
        'LocalDateTime': pa.timestamp('us'),
        'Duration': pa.int64(),
        'Point': pa.list_(pa.float32()),
        'BooleanArray': pa.list_(pa.bool_()),
        'LongArray': pa.list_(pa.int64()),
        'DoubleArray': pa.list_(pa.float32()),
        'StringArray': pa.list_(pa.utf8()),
        'DateArray': pa.list_(pa.date32()),
        'TimeArray': pa.list_(pa.time64('us')),
        'DateTimeArray': pa.list_(pa.timestamp('us')),
        'LocalTimeArray': pa.list_(pa.time64('us')),
        'LocalDateTimeArray': pa.list_(pa.timestamp('us')),
        'DurationArray': pa.list_(pa.int64()),
        'PointArray': pa.list_(pa.list_(pa.float32())),
    }

    class _Labels(Enum):
        HAS_BOTH = 0,
        BOTH_EMPTY = 1,
        SOURCE_EMPTY = 2,
        TARGET_EMPTY = 3

        @classmethod
        def get_label_type(cls, has_source, has_target):
            if has_source and has_target:
                return cls.HAS_BOTH
            elif has_source:
                return cls.TARGET_EMPTY
            elif has_target:
                return cls.SOURCE_EMPTY
            else:
                return cls.BOTH_EMPTY

    def __init__(self, xgt_server,
                       neo4j_driver,
                       verbose = False,
                       enable_apoc = True):
        """
        Initializes the connector class.

        Parameters
        ----------
        xgt_server : xgt.Connection
            Connection object to xGT.
        neo4j_driver : neo4j.Neo4jDriver, neo4j.BoltDriver, tuple(neo4j.Neo4jDriver, database), tuple(neo4j.BoltDriver, database), or xgt_connector.Neo4jDriver
            Connection object to Neo4j.
        verbose : bool
            Print detailed information during calls.
        enable_apoc : bool
            If the connector finds APOC, it will use that to improve schema queries.
            If set to True this enables that feature.
            By default this is True.
        """

        self._xgt_server = xgt_server
        if isinstance(neo4j_driver, (neo4j.Neo4jDriver, neo4j.BoltDriver)):
            self._neo4j_driver = Neo4jDriver.from_Neo4jDriver(neo4j_driver)
        elif isinstance(neo4j_driver, tuple):
            if not isinstance(neo4j_driver[0], (neo4j.Neo4jDriver, neo4j.BoltDriver)):
                raise TypeError("Tuple expected to contain Neo4jDriver or BoltDriver")
            self._neo4j_driver = Neo4jDriver.from_Neo4jDriver(neo4j_driver[0], neo4j_driver[1])
        else:
            self._neo4j_driver = neo4j_driver
        self.__verbose = verbose
        self._default_namespace = xgt_server.get_default_namespace()

        self._neo4j_has_apoc = False if not enable_apoc else self.__neo4j_check_for_apoc()
        if self.__verbose and self._neo4j_has_apoc:
            print("Using apoc to query schema.")

        self._neo4j_relationship_types = None
        self._neo4j_node_type_properties = None
        self._neo4j_rel_type_properties = None
        self._neo4j_property_keys = None
        self._neo4j_node_labels = None

    def __str__(self) -> str:
        result = ""
        result += f"Neo4j Node Labels: {self.neo4j_node_labels}\n\n"
        result += f"Neo4j Relationship Types: {self.neo4j_relationship_types}\n\n"
        result += f"Neo4j Property Keys: {self.neo4j_property_keys}\n\n"
        result += f"Neo4j Schema nodes: {self.neo4j_nodes}\n\n"
        result += f"Neo4j Schema edges: {self.neo4j_edges}\n\n"
        return result

    @property
    def xgt_server(self):
        """Retrieve the xGT driver used to connect to the xGT server."""
        return self._xgt_server

    @property
    def neo4j_driver(self):
        """Retrieve the Neo4j driver used to connect to the neo4j database."""
        return self._neo4j_driver

    @property
    def neo4j_relationship_types(self) -> list():
        """
        Retrieve a list of the Neo4j relationship types.

        Returns
        -------
        list
          List of the string names of relationship types in the connected Neo4j.
        """
        return self.__neo4j_relationship_types()

    @property
    def neo4j_node_labels(self) -> list():
        """
        Retrieve a list of the Neo4j node labels.

        Returns
        -------
        list
          List of the string names of node labels in the connected Neo4j.
        """
        return self.__neo4j_node_labels()

    @property
    def neo4j_property_keys(self) -> list():
        """
        Retrieve a list of the Neo4j property keys.

        Returns
        -------
        list
          List of the string names of property keys in the connected Neo4j.
        """
        return self.__neo4j_property_keys()

    @property
    def neo4j_node_type_properties(self) -> list():
        """
        Retrieve a list of the property types attached to the nodes in Neo4j.

        Each element of this list is a dictionary describing the property,
        including its name, its possible data types, and which node labels
        it may be attached to.

        Returns
        -------
        list
          List of the string names of node property types in the connected Neo4j.
        """

        return self.__neo4j_node_type_properties()

    @property
    def neo4j_rel_type_properties(self) -> list():
        """
        Retrieve a list of the property types attached to the relationships in
        Neo4j.

        Each element of this list is a dictionary describing the property,
        including its name, its possible data types, and which relationship(s)
        it may be attached to.

        Returns
        -------
        list
          List of the string names of relationship property types in the
          connected Neo4j.
        """
        return self.__neo4j_rel_type_properties()

    @property
    def neo4j_nodes(self) -> dict():
        """
        Retrieve a dictionary of the node labels (types) mapped to a
        description of the node's schema.

        Each dictionary entry has a key, which is the node label, and a value
        that is a dictionary of property-names mapped to property-types.

        Returns
        -------
        dict
          Dictionary mapping the node labels to a description of the
          node's schema.
        """
        return self.__neo4j_nodes()

    @property
    def neo4j_edges(self) -> dict():
        """
        Retrieve a dictionary of the edges (relationships) mapped to a
        description of the edge's metadata, including its property schema and
        its endpoint node labels (for both source and target).

        Returns
        -------
        dict
          Dictionary mapping the edge names to a description of the
          edge's schema and edge endpoints.
        """
        return self.__neo4j_edges()

    def get_xgt_schemas(self, vertices = None, edges = None,
                        neo4j_id_name = 'neo4j_id',
                        neo4j_source_node_name = 'neo4j_source',
                        neo4j_target_node_name = 'neo4j_target',
                        import_edge_nodes = True) -> dict():
        """
        Retrieve a dictionary containing the schema information for all of
        the nodes/vertices and all of the edges requested.
        If both vertices and edges is None, it will retrieve them all.

        Parameters
        ----------
        vertices : iterable
            List of requested node labels (vertex frame names) as a string or tuple.
            To map to a specific from a Neo4j label to an xGT frame use a tuple like so:
            ('neo4j_name', 'xgt_name').
        edges : iterable
            List of requested relationship type (edge frame) names or tuple.
            To map to a specific from a Neo4j type to an xGT frame use a tuple like so:
            ('neo4j_name', 'xgt_name').
            Any vertices not given for an edge will be automatically requested unless disabled.
        neo4j_id_name : str
            The name of the xGT column holding the Neo4j node's ID value.
        neo4j_source_node_name : str
            The name of the xGT column holding the source node's ID value.
        neo4j_source_node_name: str
            The name of the xGT column holding the target node's ID value.
        import_edge_nodes : boolean
            Add vertices from edge if not explicitly listed.
            By default True.

        Returns
        -------
        dict
            Dictionary containing the schema information of all the nodes/
            vertices and all of the edges requested.
        """
        result = {'vertices' : dict(), 'edges' : dict()}

        self.__update_cache_state()

        if vertices is None and edges is None:
           vertices = [vertex for vertex in self.__neo4j_node_labels(False)]
           edges = [edge for edge in self.__neo4j_relationship_types(False)]
        elif edges is None:
            edges = [ ]
        elif vertices is None:
            vertices = [ ]

        mapping_vertices = { }
        mapping_edges = { }
        for val in vertices:
            if isinstance(val, str):
                if val != '':
                    mapping_vertices[val] = val
                else:
                    mapping_vertices[val] = self.__xgt_unlabeled_vertex_name()
            elif isinstance(val, tuple):
                mapping_vertices[val[0]] = val[1]

        for val in edges:
            if isinstance(val, str):
                mapping_edges[val] = val
            elif isinstance(val, tuple):
                mapping_edges[val[0]] = val[1]

        # Any vertices not given for an edge will be added to vertices.
        for edge in mapping_edges:
            if edge not in self.__neo4j_relationship_types(False):
                raise ValueError(f"Neo4j Relationship {edge} is not found.")
            schemas = self.__extract_xgt_edge_schemas(edge, mapping_vertices, mapping_edges,
                neo4j_source_node_name, neo4j_target_node_name, import_edge_nodes, False)
            result['edges'][edge] = schemas

        for vertex in mapping_vertices:
            if vertex != self.__neo4j_unlabeled_vertex_name() and vertex not in self.__neo4j_node_labels(False):
                raise ValueError(f"Neo4j Node Label {vertex} is not found.")
            table_schema = self.__extract_xgt_vertex_schema(vertex, neo4j_id_name, mapping_vertices[vertex], False)
            result['vertices'][vertex] = table_schema
            if self.__verbose:
                print(f"xGT graph schema for vertex {vertex}: {table_schema}")

        return result

    def create_xgt_schemas(self, xgt_schemas, append = False,
                           force = False) -> None:
        """
        Creates vertex and/or edge frames in Rocketgraph xGT.

        This function first infers the schemas for all of the needed frames in xGT to
        store the requested data.
        Then those frames are created in xGT.

        Parameters
        ----------
        xgt_schemas : dict
            Dictionary containing schema information for vertex and edge frames
            to create in xGT.
            This dictionary can be the value returned from the
            :py:meth:`~Neo4jConnector.get_xgt_schemas` method.
        append : boolean
            Set to true when the xGT frames are already created and holding data
            that should be appended to.
            Set to false when the xGT frames are to be newly created (removing
            any existing frames with the same names prior to creation).
        force : boolean
            Set to true to force xGT to drop edges when a vertex frame has dependencies.

        Returns
        -------
            None
        """
        if not append:
            for edge in xgt_schemas['edges']:
                schemas = xgt_schemas['edges'][edge]
                if (len(schemas) == 1):
                    self._xgt_server.drop_frame(schemas[0]['xgt_name'])
                # Frame name refers to multiple edges:
                elif (len(schemas) > 1):
                    for schema in schemas:
                        multi_edge_name = self.__edge_name_transform(schema['xgt_name'], schema['xgt_source'], schema['xgt_target'], True)
                        self._xgt_server.drop_frame(multi_edge_name)

            for vertex in xgt_schemas['vertices']:
                schema = xgt_schemas['vertices'][vertex]
                try:
                    self._xgt_server.drop_frame(schema['xgt_name'])
                except xgt.XgtFrameDependencyError as e:
                    if force:
                        # Would be better if this could be done without doing this.
                        edge_frames = str(e).split(':')[-1].split(' ')[1:]
                        for edge in edge_frames:
                            self._xgt_server.drop_frame(edge)
                        self._xgt_server.drop_frame(vertex)
                    else:
                        raise e

        for vertex, schema in xgt_schemas['vertices'].items():
            table_schema = schema['schema']
            key = schema['key']
            create_frame = True
            vname = schema['xgt_name']
            if append:
                try:
                    frame = self._xgt_server.get_frame(vname)
                    if frame.schema != table_schema:
                        raise ValueError(
                            f"Vertex Frame {vname} has a schema {frame.schema}"
                            + f" that is incompatible with Neo4j: {table_schema}"
                        )
                    create_frame = False
                except:
                    pass
            if create_frame:
                self._xgt_server.create_vertex_frame(
                    name = vname, schema = table_schema,
                    key = key, attempts = 5,
                )

        for edge, schema_list in xgt_schemas['edges'].items():
            transform = True if len(schema_list) > 1 else False
            for schema in schema_list:
                table_schema = schema['schema']
                if self.__verbose:
                    print(f"xGT graph schema for edge {edge}: {table_schema}")
                name = self.__edge_name_transform(schema['xgt_name'], schema['xgt_source'], schema['xgt_target'], transform)
                self._xgt_server.create_edge_frame(
                        name = name, schema = table_schema,
                        source = schema['xgt_source'],
                        source_key = schema['source_key'],
                        target = schema['xgt_target'],
                        target_key = schema['target_key'],
                        attempts = 5,
                    )

        return None

    def copy_data_to_xgt(self, xgt_schemas) -> None:
        """
        Copies data from Neo4j to the requested vertex and/or edge frames
        in Rocketgraph xGT.

        This function copies data from Neo4j to xGT for all of the nodes and
        all of the relationships, one frame at a time.

        Parameters
        ----------
        xgt_schemas : dict
            Dictionary containing schema information for vertex and edge frames
            to create in xGT.
            This dictionary can be the value returned from the
            :py:meth:`~Neo4jConnector.get_xgt_schemas` method.

        Returns
        -------
            None
        """
        def xlate_result_property(attr, attr_type) -> str:
            if self._neo4j_driver._arrow_driver is not None and (attr_type == 'datetime' or attr_type == 'date' or attr_type == 'time'):
                return f", toString(v.{a}) as {a}"
            return f", v.{a} AS {a}"
        # Use the count store to get totals.
        estimated_counts = 0
        for vertex in xgt_schemas['vertices']:
            # On transfer on unlabeled vertices we can't get accurate
            # estimates so assume every vertex.
            if vertex == '':
                q = f"MATCH (v) RETURN count(v)"
                with self._neo4j_driver.query(q, False) as query:
                    for record in query.result():
                        estimated_counts = record[0]
                break
            q = f"MATCH (v:{vertex}) RETURN count(v)"
            with self._neo4j_driver.query(q, False) as query:
                for record in query.result():
                    estimated_counts += record[0]
        for edge, schema_list in xgt_schemas['edges'].items():
            for schema in schema_list:
                source = schema['source']
                target = schema['target']
                match_type = schema['empty_labels']
                # We can't use both source and target, because that won't use
                # the count store.
                if match_type == self._Labels.SOURCE_EMPTY:
                    q = f"MATCH ()-[e:{edge}]->(:{target}) RETURN count(e)"
                elif match_type == self._Labels.TARGET_EMPTY:
                    q = f"MATCH (:{source})-[e:{edge}]->() RETURN count(e)"
                else:
                    q = f"MATCH ()-[e:{edge}]->() RETURN count(e)"
                with self._neo4j_driver.query(q, False) as query:
                    for record in query.result():
                        estimated_counts += record[0]

        with ProgressDisplay(estimated_counts) as progress_bar:
            for vertex, schema in xgt_schemas['vertices'].items():
                if self.__verbose:
                    print(f'Copy data for vertex {vertex} into schema: {schema}')
                table_schema = schema['schema']
                attributes = {_:t for _, t, *_unused_ in table_schema}
                key = schema['key']
                if vertex != '':
                    query = f"MATCH (v:{vertex}) RETURN id(v) AS {key}"  # , {', '.join(attributes)}"
                else:
                    query = f"MATCH (v) where size(labels(v)) = 0 RETURN id(v) AS {key}"  # , {', '.join(attributes)}"
                for a in attributes:
                    if a != key:
                        query += xlate_result_property(a, attributes[a]) # f", v.{a} AS {a}"
                # Is an empty vertex type if None:
                if schema['neo4j_schema'] is not None:
                    self.__copy_data(query, schema['xgt_name'], schema['neo4j_schema'], progress_bar)
            for edge, schema_list in xgt_schemas['edges'].items():
                if self.__verbose:
                    print(f'Copy data for node {edge} into schema: {schema_list}')
                transform = True if len(schema_list) > 1 else False
                for schema in schema_list:
                    name = self.__edge_name_transform(schema['xgt_name'], schema['xgt_source'], schema['xgt_target'], transform)
                    table_schema = schema['schema']
                    attributes = {_:t for _, t, *_unused_ in table_schema}
                    source = schema['source']
                    source_key = schema['source_key']
                    target = schema['target']
                    target_key = schema['target_key']
                    match_type = schema['empty_labels']
                    if match_type == self._Labels.HAS_BOTH:
                        query = f"MATCH (u:{source})-[e:{edge}]->(v:{target}) RETURN"
                    elif match_type == self._Labels.BOTH_EMPTY:
                        query = f"MATCH (u)-[e:{edge}]->(v) where size(labels(u)) = 0 and size(labels(v)) = 0 RETURN"
                    elif match_type == self._Labels.SOURCE_EMPTY:
                        query = f"MATCH (u)-[e:{edge}]->(v:{target}) where size(labels(u)) = 0 RETURN"
                    elif match_type == self._Labels.TARGET_EMPTY:
                        query = f"MATCH (u:{source})-[e:{edge}]->(v) where size(labels(v)) = 0 RETURN"
                    query += f" id(u) AS {source_key}"
                    query += f", id(v) AS {target_key}"
                    for a in attributes:
                        if a != source_key and a != target_key:
                            query += f", e.{a} AS {a}"
                    self.__copy_data(query, name, schema['neo4j_schema'], progress_bar)
        return  None

    def transfer_to_xgt(self, vertices = None, edges = None,
                        neo4j_id_name = 'neo4j_id',
                        neo4j_source_node_name = 'neo4j_source',
                        neo4j_target_node_name = 'neo4j_target',
                        append = False, force = False,
                        import_edge_nodes = True) -> None:
        """
        Copies data from Neo4j to Rocketgraph xGT.

        This function first infers the schemas for all of the needed frames in xGT to
        store the requested data.
        Then those frames are created in xGT.
        Finally, all of the nodes and all of the relationships are copied,
        one frame at a time, from Neo4j to xGT.
        If both vertices and edges is None, it will retrieve them all.

        Parameters
        ----------
        vertices : iterable
            List of requested node labels (vertex frame names) as a string or tuple.
            To map to a specific from a Neo4j label to an xGT frame use a tuple like so:
            ('neo4j_name', 'xgt_name').
        edges : iterable
            List of requested relationship type (edge frame) names or tuple.
            To map to a specific from a Neo4j type to an xGT frame use a tuple like so:
            ('neo4j_name', 'xgt_name').
            Any vertices not given for an edge will be automatically requested unless disabled.
        neo4j_id_name : str
            The name of the xGT column holding the Neo4j node's ID value.
        neo4j_source_node_name : str
            The name of the xGT column holding the source node's ID value.
        neo4j_source_node_name : str
            The name of the xGT column holding the target node's ID value.
        append : boolean
            Set to true when the xGT frames are already created and holding data
            that should be appended to.
            Set to false when the xGT frames are to be newly created (removing
            any existing frames with the same names prior to creation).
        force : boolean
            Set to true to force xGT to drop edges when a vertex frame has dependencies.
        import_edge_nodes : boolean
            Add vertices from edge if not explicitly listed.
            By default True.

        Returns
        -------
            None
        """
        xgt_schema = self.get_xgt_schemas(vertices, edges,
                neo4j_id_name, neo4j_source_node_name, neo4j_target_node_name,
                import_edge_nodes)
        self.create_xgt_schemas(xgt_schema, append, force)
        self.copy_data_to_xgt(xgt_schema)
        return None

    def transfer_to_neo4j(self, vertices = None, edges = None, namespace = None,
                          edge_keys = False, vertex_keys = False):
        """
        Copies data from Rocketgraph xGT to Neo4j.

        All of the nodes and all of the relationships are copied,
        one frame at a time, from xGT to Neo4j.
        If both vertices and edges is None, it will retrieve them all.

        Parameters
        ----------
        vertices : iterable
            List of requested node labels (vertex frame names).
        edges : iterable
            List of requested relationship type (edge frame) names.
            Any vertices not given for an edge will be automatically requested.
        namespace : str
            Namespace for the selected frames.
            If none will use the default namespace.
        edge_keys : boolean
            If true will transfer edge key columns.
        vertex_keys : boolean
            If true will transfer vertex key columns.

        Returns
        -------
            None
        """
        xgt_server = self._xgt_server
        if namespace == None:
            namespace = self._default_namespace
        if vertices == None and edges == None:
            vertices = [frame.name for frame in xgt_server.get_frames(namespace=namespace, frame_type='vertex')]
            edges = [frame.name for frame in xgt_server.get_frames(namespace=namespace, frame_type='edge')]
            namespace = None
        elif vertices == None:
            vertices = []
        elif edges == None:
            edges = []

        id_neo4j_map = { }

        for edge in edges:
            edge_frame = xgt_server.get_frame(edge)
            vertices.append(edge_frame.source_name)
            vertices.append(edge_frame.target_name)

        def convert(value):
            if value is None:
                return 'Null'
            elif isinstance(value, str):
                return '"' + value + '"'
            elif isinstance(value, datetime.datetime):
                format_string = 'datetime({{year:{0},month:{1},day:{2},hour:{3},minute:{4},second:{5},microsecond:{6}}})'
                return format_string.format(value.year, value.month, value.day, value.hour, value.minute, value.second, value.microsecond)
            elif isinstance(value, datetime.date):
                return 'date({{year:{0},month:{1},day:{2}}})'.format(value.year, value.month, value.day)
            elif isinstance(value, datetime.time):
                return 'time({{hour:{0},minute:{1},second:{2},microsecond:{3}}})'.format(value.hour, value.minute, value.second, value.microsecond)
            elif isinstance(value, list):
                if len(value) > 0:
                    if isinstance(value[0], datetime.datetime):
                        format_string = 'datetime({{year:{0},month:{1},day:{2},hour:{3},minute:{4},second:{5},microsecond:{6}}})'
                        return '[' + ','.join([format_string.format(x.year, x.month, x.day, x.hour, x.minute, x.second, x.microsecond) for x in value]) + ']'
                    elif isinstance(value[0], datetime.date):
                        format_string = 'date({{year:{0},month:{1},day:{2}}})'
                        return '[' + ','.join([format_string.format(x.year, x.month, x.day) for x in value]) + ']'
                    elif isinstance(value[0], datetime.time):
                        format_string = 'time({{hour:{0},minute:{1},second:{2},microsecond:{3}}})'
                        return '[' + ','.join([format_string.format(x.hour, x.minute, x.second, x.microsecond) for x in value]) + ']'
                    elif isinstance(value[0], list):
                        if len(value[0]) == 2:
                            format_string = 'point({{x:{0},y:{1}}})'
                            return '[' + ','.join([format_string.format(x[0], x[1]) for x in value]) + ']'
                        elif len(value[0]) == 3:
                            format_string = 'point({{x:{0},y:{1},z:{2}}})'
                            return '[' + ','.join([format_string.format(x[0], x[1], x[2]) for x in value]) + ']'
                        else:
                            raise ValueError("List of list not supported in Neo4j.")

                return str(value)
            else:
                return str(value)

        count_map = { }
        estimated_counts = 0
        for vertex in vertices:
            if vertex in count_map:
                continue
            count_map[vertex] = True
            estimated_counts += xgt_server.get_frame(vertex).num_rows
        for edge in edges:
            estimated_counts += xgt_server.get_frame(edge).num_rows

        with ProgressDisplay(estimated_counts) as progress_bar:
            for vertex in vertices:
                if vertex in id_neo4j_map:
                    continue
                id_neo4j_map[vertex] = { }
                vertex_frame = xgt_server.get_frame(vertex)
                create_string = 'create (a:' + vertex + '{{{0}}}) return ID(a)'

                schema = vertex_frame.schema
                reader = self.__arrow_reader(vertex)

                labels = [val[0] for val in schema]

                for i, value in enumerate(schema):
                    if value[0] == vertex_frame.key:
                        key_pos = i
                        break

                with self._neo4j_driver.bolt.session(
                        database=self._neo4j_driver._database,
                        default_access_mode=neo4j.WRITE_ACCESS) as session:
                    while (True):
                        try:
                            chunk = reader.read_chunk().data
                            rows = [None] * chunk.num_rows
                            for i in range(chunk.num_rows):
                                rows[i] = []
                            for i, x in enumerate(chunk):
                                for j, y in enumerate(x):
                                    rows[j].append(y.as_py())
                            tx = session.begin_transaction()
                            for row in rows:
                                elements = ",".join(labels[i] + ':' + convert(row[i], ) for i in range(len(row)) if vertex_keys or i != key_pos)
                                result = tx.run(create_string.format(elements))
                                for val in result:
                                    id_neo4j_map[vertex][row[key_pos]] = val[0]
                                progress_bar.show_progress(1)
                            tx.commit()
                            tx.close()
                        except StopIteration:
                            break

            for edge in edges:
                edge_frame = xgt_server.get_frame(edge)
                source = edge_frame.source_name
                target = edge_frame.target_name
                source_frame = xgt_server.get_frame(source)
                target_frame = xgt_server.get_frame(target)
                source_map = id_neo4j_map[source]
                target_map = id_neo4j_map[target]
                create_string = 'match (a:' + source + '), (b:' + target + ') where ID(a) = {0} and ID(b) = {1} create (a)-[:' + edge + '{{{2}}}]->(b)'

                schema = edge_frame.schema
                reader = self.__arrow_reader(edge)
                labels = [val[0] for val in schema]

                for i, value in enumerate(schema):
                    if value[0] == edge_frame.source_key:
                        src_key_pos = i
                        break

                for i, value in enumerate(schema):
                    if value[0] == edge_frame.target_key:
                        trg_key_pos = i
                        break

                with self._neo4j_driver.bolt.session(database=self._neo4j_driver._database,
                                                     default_access_mode=neo4j.WRITE_ACCESS) as session:
                    while (True):
                        try:
                            chunk = reader.read_chunk().data
                            rows = [None] * chunk.num_rows
                            for i in range(chunk.num_rows):
                                rows[i] = []
                            for i, x in enumerate(chunk):
                                for j, y in enumerate(x):
                                    rows[j].append(y.as_py())
                            tx = session.begin_transaction()
                            for row in rows:
                                elements = ",".join(labels[i] + ':' + convert(row[i]) for i in range(len(row)) if edge_keys or (i != src_key_pos and i != trg_key_pos))
                                tx.run(create_string.format(source_map[row[src_key_pos]], target_map[row[trg_key_pos]], elements))
                                progress_bar.show_progress(1)
                            tx.commit()
                            tx.close()
                        except StopIteration:
                            break

    def translate_query(self, query:str) -> str:
        """
        Translate a Cypher query to be ready to run in Rocketgraph xGT.

        It is sometimes necessary to make alterations to naming of graph components
        as part of the automatic graph schema creation from a Neo4j database to 
        hold data in a Rocketgraph xGT server.  One example of this is when a
        relationship type consists of some edges from one source node label and
        other edges from a different source node label.

        Given a Cypher query that formulated to run against a Neo4j database, there
        may be some changes required in order to run that same query against a
        Rocketgraph xGT server holding a graph schema that has been auto-generated.

        Parameters
        ----------
        query : str
          A Cypher query that can be run against the Neo4j database that is
          part of this connector instance.

        Returns
        -------
        str
          Translated Cypher query.
        """
        query_translator = QueryTranslator(self.get_xgt_schemas(),
                                           verbose = self.__verbose)
        if self.__verbose:
            print("Built query translator instance")
        return query_translator.translate(query)

    def __neo4j_check_for_apoc(self):
        try:
            with self._neo4j_driver.query("RETURN apoc.version()", False) as query:
                query.result()
                return True
        except Exception as e:
            pass
        return False

    def __neo4j_property_keys(self, flush_cache = True):
        if flush_cache:
            with self._neo4j_driver.query("CALL db.propertyKeys() YIELD propertyKey RETURN propertyKey", False) as query:
                self._neo4j_property_keys = list([record["propertyKey"] for record in query.result()])
                self._neo4j_property_keys.sort()
        return self._neo4j_property_keys

    def __neo4j_node_type_properties(self, flush_cache = True):
        if flush_cache:
            fields = ('nodeType', 'nodeLabels', 'propertyName', 'propertyTypes', 'mandatory')
            if self._neo4j_has_apoc:
                q="CALL apoc.meta.nodeTypeProperties() YIELD nodeType, nodeLabels, propertyName, propertyTypes, mandatory RETURN *"
                with self._neo4j_driver.query(q, False) as query:
                    self._neo4j_node_type_properties = [{_ : record[_] for _ in fields} for record in query.result()]
                # Get unlabeled nodes. APOC has a bug...
                q="CALL db.schema.nodeTypeProperties() YIELD nodeType, nodeLabels, propertyName, propertyTypes, mandatory RETURN *"
                with self._neo4j_driver.query(q, False) as query:
                    self._neo4j_node_type_properties += [{_ : record[_] for _ in fields} for record in query.result() if record['nodeType'] == '']
            else:
                q="CALL db.schema.nodeTypeProperties() YIELD nodeType, nodeLabels, propertyName, propertyTypes, mandatory RETURN *"
                with self._neo4j_driver.query(q, False) as query:
                    self._neo4j_node_type_properties = [{_ : record[_] for _ in fields} for record in query.result()]
        return self._neo4j_node_type_properties

    def __neo4j_rel_type_properties(self, flush_cache = True):
        if flush_cache:
            fields = ('relType', 'propertyName', 'propertyTypes', 'mandatory')
            if self._neo4j_has_apoc:
                q="CALL apoc.meta.relTypeProperties() YIELD relType, propertyName, propertyTypes, mandatory RETURN *"
                with self._neo4j_driver.query(q, False) as query:
                    self._neo4j_rel_type_properties = [{_ : record[_] for _ in fields} for record in query.result()]
                # Get edges attached to unlabeled nodes. APOC has a bug...
                found = {record['relType'] : True for record in self._neo4j_rel_type_properties }
                q="CALL db.schema.relTypeProperties() YIELD relType, propertyName, propertyTypes, mandatory RETURN *"
                with self._neo4j_driver.query(q, False) as query:
                    self._neo4j_rel_type_properties += [{_ : record[_] for _ in fields} for record in query.result() if record['relType'] not in found]
            else:
                q="CALL db.schema.relTypeProperties() YIELD relType, propertyName, propertyTypes, mandatory RETURN *"
                with self._neo4j_driver.query(q, False) as query:
                    self._neo4j_rel_type_properties = [{_ : record[_] for _ in fields} for record in query.result()]
        return self._neo4j_rel_type_properties

    def __add_neo4j_schema_connectivity_to_neo4j_edges(self) -> None:
        def extract_node_info(node):
            labels = node.labels
            if len(labels) == 1:
                return list(labels)[0]
            return labels
        if self._neo4j_has_apoc:
            q="CALL apoc.meta.graph()"
        else:
            q="CALL db.schema.visualization() YIELD nodes, relationships RETURN *"
        # TODO(landwehrj) Can schema be done with py2neo?
        with self._neo4j_driver.query(q, False, True) as query:
            for record in query.result():
                has_multiple_relations = len(record['relationships']) > 1
                for e in record['relationships']:
                    nodes = e.nodes
                    source = nodes[0]
                    target = nodes[1]
                    e_type = e.type

                    source_name = extract_node_info(source)
                    target_name = extract_node_info(target)

                    if not self._neo4j_has_apoc and has_multiple_relations:
                        # Neo4j does not return the correct schema for multi-edges
                        # without APOC so we need to do additional queries to filter fake edges:
                        # See https://github.com/neo4j/neo4j/issues/9726
                        schema_exists = False
                        q = f"MATCH (:{source_name})-[e:{e_type}]->(:{target_name}) return count(e) > 0"
                        with self._neo4j_driver.query(q, False) as query:
                            for result in query.result():
                                schema_exists = result[0]

                        if (not schema_exists):
                            continue
                    if self.__verbose:
                        print(f"Edge Connectivity: {e}")
                        print(f" -> type => {e_type}")
                        print(f" -> source nodes => {source}")
                        print(f" -> target nodes => {nodes[1]}")
                        print(f"  -> Edge {e_type}: {self._neo4j_edges[e_type]}\n")
                    if 'endpoints' not in self._neo4j_edges[e_type]:
                        self._neo4j_edges[e_type]['endpoints'] = set()
                        self._neo4j_edges[e_type]['sources'] = set()
                        self._neo4j_edges[e_type]['targets'] = set()
                    self._neo4j_edges[e_type]['endpoints'].add(
                        (extract_node_info(source), extract_node_info(target)))
                    self._neo4j_edges[e_type]['sources'].add(extract_node_info(source))
                    self._neo4j_edges[e_type]['targets'].add(extract_node_info(target))

        vertices = [vertex for vertex in self.__neo4j_node_labels(False)]
        for e_type in self._neo4j_edges:
            if 'endpoints' not in self._neo4j_edges[e_type]:
                # We have an edge with one or more non-typed vertex.
                # These aren't picked up be Neo4j or APOC with the above methods.

                self._neo4j_edges[e_type]['endpoints'] = set()
                self._neo4j_edges[e_type]['sources'] = set()
                self._neo4j_edges[e_type]['targets'] = set()

                for v in vertices:
                    if v == self.__neo4j_unlabeled_vertex_name():
                        continue
                    schema_exists = False
                    q = f"MATCH (:{v})-[e:{e_type}]->() return count(e) > 0"
                    with self._neo4j_driver.query(q, False) as query:
                        for result in query.result():
                            schema_exists = result[0]

                    if (schema_exists):
                        self._neo4j_edges[e_type]['sources'].add(v)
                        self._neo4j_edges[e_type]['endpoints'].add((v, None))

                    q = f"MATCH ()-[e:{e_type}]->(:{v}) return count(e) > 0"
                    with self._neo4j_driver.query(q, False) as query:
                        for result in query.result():
                            schema_exists = result[0]

                    if (schema_exists):
                        self._neo4j_edges[e_type]['targets'].add(v)
                        self._neo4j_edges[e_type]['endpoints'].add((None, v))

            # Failed to find any relevant nodes for this edge.
            if len(self._neo4j_edges[e_type]['endpoints']) == 0:
                self._neo4j_edges[e_type]['endpoints'].add((None, None))

        return None

    def __neo4j_nodes(self, flush_cache = True):
        if flush_cache:
            nodes = dict()
            for prop in self.__neo4j_node_type_properties(flush_cache):
                labels = prop['nodeLabels']
                propTypes = prop['propertyTypes']
                if propTypes is not None and len(propTypes) == 1:
                        propTypes = propTypes[0]
                for name in labels:
                    if name not in nodes:
                        nodes[name] = dict()
                    if propTypes is not None:
                        nodes[name][prop['propertyName']] = propTypes
                if len(labels) == 0:
                    name = self.__neo4j_unlabeled_vertex_name()
                    if name not in nodes:
                        nodes[name] = dict()
                    if propTypes is not None:
                        nodes[name][prop['propertyName']] = propTypes
            self._neo4j_nodes = nodes
        return self._neo4j_nodes

    def __neo4j_edges(self, flush_cache = True) -> dict():
        if flush_cache:
          self.__update_cache_state()
        return self._neo4j_edges

    def __neo4j_process_nodes(self, nodes):
        res = dict()
        for n in nodes:
            if self.__verbose:
                print(f"__neo4j_process_nodes: {n}")

            propName = n['propertyName']
            propType = n['propertyTypes']
            if propType is not None and len(propType) == 1:
                propType = propType[0]
            for name in n['nodeLabels']:
                if name not in res:
                    res[name] = dict()
                if propName is not None and propName not in res[name]:
                    res[name][propName] = propType
            if len(n['nodeLabels']) == 0:
                name = self.__neo4j_unlabeled_vertex_name()
                if name not in res:
                    res[name] = dict()
                if propName is not None and propName not in res[name]:
                    res[name][propName] = propType
        return res

    def __neo4j_process_edges(self, edges):
        res = dict()
        for e in edges:
            if self.__verbose:
                print(f"__neo4j_process_edges: {e}")
            relType = e['relType']
            propName = e['propertyName']
            propType = e['propertyTypes']
            if relType[0:2] == ':`' and relType[-1] == '`':
                relType = relType[2:-1]
            if propType is not None and len(propType) == 1:
                propType = propType[0]
            if relType not in res:
                res[relType] = {'schema' : dict()}
            if propName is not None:
                res[relType]['schema'][propName] = propType
        return res

    def __extract_xgt_vertex_schema(self, vertex, neo4j_id_name, xgt_vertex_name, flush_cache = True):
        if flush_cache:
            self.__update_cache_state()
        if vertex in self.__neo4j_nodes(False):
            neo4j_node = self.__neo4j_nodes(False)[vertex]
            neo4j_node_attributes = list(neo4j_node.keys())
            if neo4j_id_name in neo4j_node:
                raise ValueError(
                        f"Neo4j ID name {neo4j_id_name} is an attribute of node {neo4j_node}")
        schema = [[key, *self.__neo4j_type_to_xgt_type(type)]
                  for key, type in neo4j_node.items()]
        neo4j_schema = [[key, type] for key, type in neo4j_node.items()]
        schema.insert(0, [neo4j_id_name, xgt.INT])
        neo4j_schema.insert(0, [neo4j_id_name, 'INTEGER'])
        return {'schema' : schema, 'neo4j_schema' : neo4j_schema,
                'key' : neo4j_id_name, 'xgt_name' : xgt_vertex_name}

    def __extract_xgt_edge_schema(self, edge, source, target,
                                  neo4j_source_node_name,
                                  neo4j_target_node_name,
                                  xgt_edge_name,
                                  xgt_source_name,
                                  xgt_target_name,
                                  flush_cache = True):
        if flush_cache:
          self.__update_cache_state()
        result = dict()
        if edge not in self.__neo4j_relationship_types(False):
            raise ValueError(f"Edge {edge} is not a known relationship type")
        edge_info = self.__neo4j_edges(False)[edge]
        if self.__verbose:
            print(f"xGT graph schema for edge {edge}: {edge_info}")
        info_schema = edge_info['schema']
        edge_endpoints = edge_info['endpoints']
        endpoints = (source, target)
        if source != None and target != None and endpoints not in edge_endpoints:
            raise ValueError(f"Edge Type {edge} with endpoints: {endpoints} not found.")
        has_source = True
        has_target = True
        if source == None:
            source = self.__neo4j_unlabeled_vertex_name()
            has_source = False
        if target == None:
            target = self.__neo4j_unlabeled_vertex_name()
            has_target = False

        schema = [[key, *self.__neo4j_type_to_xgt_type(type)]
                  for key, type in info_schema.items()]
        neo4j_schema = [[key, type] for key, type in info_schema.items()]
        schema.insert(0, [neo4j_target_node_name, xgt.INT])
        schema.insert(0, [neo4j_source_node_name, xgt.INT])
        neo4j_schema.insert(0, [neo4j_target_node_name, 'INTEGER'])
        neo4j_schema.insert(0, [neo4j_source_node_name, 'INTEGER'])
        return {'schema' : schema, 'neo4j_schema' : neo4j_schema,
                'source' : source, 'target' : target,
                'source_key' : neo4j_source_node_name,
                'target_key' : neo4j_target_node_name,
                'empty_labels' : self._Labels.get_label_type(has_source, has_target),
                'xgt_name' : xgt_edge_name, 'xgt_source' : xgt_source_name,
                'xgt_target' : xgt_target_name}

    def __extract_xgt_edge_schemas(self, edge, vertices, edges, neo4j_source_node_name,
                                   neo4j_target_node_name,
                                   import_edge_nodes = True, flush_cache = True):
        if flush_cache:
          self.__update_cache_state()
        schemas = []
        neo4j_edge = self.__neo4j_edges(False)[edge]
        for source, target in neo4j_edge['endpoints']:
            source_name = source
            target_name = target
            if import_edge_nodes:
                if source != None and source not in vertices:
                    vertices[source] = source
                if target != None and target not in vertices:
                    vertices[target] = target
            if source == None or target == None:
                vname = self.__neo4j_unlabeled_vertex_name()
                if source == None:
                    source_name = vname
                if target == None:
                    target_name = vname
                if import_edge_nodes:
                    if not vname in vertices:
                        vertices[vname] = self.__xgt_unlabeled_vertex_name()
            if source_name in vertices:
                source_name = vertices[source_name]
            elif source_name == self.__neo4j_unlabeled_vertex_name():
                source_name = self.__xgt_unlabeled_vertex_name()

            if target_name in vertices:
                target_name = vertices[target_name]
            elif target_name == self.__neo4j_unlabeled_vertex_name():
                target_name = self.__xgt_unlabeled_vertex_name()

            result = self.__extract_xgt_edge_schema(edge,
                source, target, neo4j_source_node_name,
                neo4j_target_node_name, edges[edge], source_name,
                target_name, flush_cache)
            if result is not None:
                schemas.append(result)

        return schemas

    def __neo4j_type_to_xgt_type(self, prop_type):
        if isinstance(prop_type, list):
                raise ValueError(
                    f"Multiple types for property not supported.")
        elif prop_type in self._NEO4J_TYPE_TO_XGT_TYPE:
            return self._NEO4J_TYPE_TO_XGT_TYPE[prop_type]
        raise TypeError(f'The "{prop_type}" Neo4j type is not yet supported')

    def __arrow_writer(self, frame_name, schema):
        try:
            arrow_conn = self._xgt_server.arrow_conn
        except AttributeError:
            # Using xgt 1.10 without arrow_conn
            arrow_conn = pf.FlightClient((self._xgt_server.host, self._xgt_server.port))
            arrow_conn.authenticate(BasicArrowClientAuthHandler())
        writer, _ = arrow_conn.do_put(
            pf.FlightDescriptor.for_path(self._default_namespace, frame_name),
            schema)
        return writer

    def __arrow_reader(self, frame_name):
        try:
            arrow_conn = self._xgt_server.arrow_conn
        except AttributeError:
            # Using xgt 1.10 without arrow_conn
            arrow_conn = pf.FlightClient((self._xgt_server.host, self._xgt_server.port))
            arrow_conn.authenticate(BasicArrowClientAuthHandler())
        return arrow_conn.do_get(pf.Ticket(self._default_namespace + '__' + frame_name))

    def __copy_data(self, cypher_for_extract, frame, neo4j_schema, progress_bar):
        if self._neo4j_driver._py2neo_driver is not None:
            self.__py2neo_copy_data(cypher_for_extract, neo4j_schema, frame, progress_bar)
        elif self._neo4j_driver._arrow_driver is not None:
            self.__arrow_copy_data(cypher_for_extract, frame, progress_bar)
        else:
            self.__bolt_copy_data(cypher_for_extract, neo4j_schema, frame, progress_bar)

    def __bolt_copy_data(self, cypher_for_extract, neo4j_schema, frame, progress_bar):
        with self._neo4j_driver.bolt.session(database=self._neo4j_driver._database,
                                             default_access_mode=neo4j.READ_ACCESS) as session:
            schema = pa.schema([])
            # With xGT 10.1 we need to change double to float
            # so we infer the schema manually.
            for i, value in enumerate(neo4j_schema):
                arrow_type = self._NEO4J_TYPE_TO_ARROW_TYPE[value[1]]
                schema = schema.append(pa.field('col' + str(i), arrow_type))

            result = session.run(cypher_for_extract)
            first_record = result.peek()
            data = [None] * len(first_record)

            block_size = 10000
            for i in range(len(first_record)):
                data[i] = [None] * block_size

            xgt_writer = self.__arrow_writer(frame, schema)
            chunk_count = 0
            def convert_duration(val):
                return (val.months * 2628288 + val.days * 86400 +
                        val.seconds) * 10**9 + val.nanoseconds
            for record in result:
                for i, val in enumerate(record):
                    if isinstance(val, (neo4j.time.Date, neo4j.time.Time,
                                        neo4j.time.DateTime)):
                        data[i][chunk_count] = val.to_native()
                    elif isinstance(val, neo4j.time.Duration):
                        # For months this average seconds in a month.
                        data[i][chunk_count] = convert_duration(val)
                    elif isinstance(val, list):
                        if isinstance(val[0], (neo4j.time.Date, neo4j.time.Time,
                                               neo4j.time.DateTime)):
                            data[i][chunk_count] = [x.to_native() for x in val]
                        elif isinstance(val[0], neo4j.time.Duration):
                            data[i][chunk_count] = [convert_duration(x) for x in val]
                        else:
                            data[i][chunk_count] = val
                    else:
                        data[i][chunk_count] = val
                chunk_count = chunk_count + 1
                if chunk_count == block_size:
                    batch = pa.RecordBatch.from_arrays(data, schema=schema)
                    xgt_writer.write(batch)
                    progress_bar.show_progress(chunk_count)
                    chunk_count = 0

            if chunk_count > 0:
                for j in range(len(data)):
                    data[j] = data[j][:-(block_size - chunk_count)]
                batch = pa.RecordBatch.from_arrays(data, schema=schema)
                xgt_writer.write(batch)
                progress_bar.show_progress(chunk_count)

            xgt_writer.close()

    def __py2neo_copy_data(self, cypher_for_extract, neo4j_schema, frame, progress_bar):
        schema = pa.schema([])
        # With xGT 10.1 we need to change double to float
        # so we infer the schema manually.
        for i, value in enumerate(neo4j_schema):
            arrow_type = self._NEO4J_TYPE_TO_ARROW_TYPE[value[1]]
            schema = schema.append(pa.field('col' + str(i), arrow_type))

        result = self._neo4j_driver._py2neo_driver.query(cypher_for_extract)
        data = [None] * len(result.keys())

        block_size = 10000
        for i in range(len(result.keys())):
            data[i] = [None] * block_size

        xgt_writer = self.__arrow_writer(frame, schema)
        chunk_count = 0
        # Types Used by py2neo
        from interchange.time import Date, Time, DateTime, Duration
        def convert_duration(val):
            return (val.months * 2628288 + val.days * 86400 +
                    val.seconds) * 10**9 + int(val.subseconds * 10**9)
        for record in result:
            for i, val in enumerate(record):
                if isinstance(val, (Date, Time, DateTime)):
                    data[i][chunk_count] = val.to_native()
                elif isinstance(val, Duration):
                    # For months this average seconds in a month.
                    data[i][chunk_count] = convert_duration(val)
                elif isinstance(val, list):
                    if isinstance(val[0], (Date, Time, DateTime)):
                        data[i][chunk_count] = [x.to_native() for x in val]
                    elif isinstance(val[0], Duration):
                        data[i][chunk_count] = [convert_duration(x) for x in val]
                    else:
                        data[i][chunk_count] = val
                else:
                    data[i][chunk_count] = val
            chunk_count = chunk_count + 1
            if chunk_count == block_size:
                batch = pa.RecordBatch.from_arrays(data, schema=schema)
                xgt_writer.write(batch)
                progress_bar.show_progress(chunk_count)
                chunk_count = 0

        if chunk_count > 0:
            for j in range(len(data)):
                data[j] = data[j][:-(block_size - chunk_count)]
            batch = pa.RecordBatch.from_arrays(data, schema=schema)
            xgt_writer.write(batch)
            progress_bar.show_progress(chunk_count)

        xgt_writer.close()

    def __arrow_copy_data(self, cypher_for_extract, frame, progress_bar):
        ticket = self._neo4j_driver._arrow_driver.cypher(cypher_for_extract,
                                                         self._neo4j_driver._database_arrow)
        ready = self._neo4j_driver._arrow_driver.wait_for_job(ticket, timeout=60)
        if not ready:
            raise Exception('something is wrong...did you submit a job?')
        neo4j_reader = self._neo4j_driver._arrow_driver.stream(ticket).to_reader()
        xgt_writer = self.__arrow_writer(frame, neo4j_reader.schema)
        # move data from Neo4j to xGT in chunks
        while (True):
            try:
                batch = neo4j_reader.read_next_batch()
                xgt_writer.write(batch)
                progress_bar.show_progress(batch.num_rows)
            except StopIteration:
                break
        xgt_writer.close()

    def __neo4j_relationship_types(self, flush_cache = True) -> list():
        if flush_cache:
          self.__update_cache_state()
        if self._neo4j_relationship_types is None:
            self._neo4j_relationship_types = list(self._neo4j_edges.keys())
            self._neo4j_relationship_types.sort()
        return self._neo4j_relationship_types

    def __neo4j_node_labels(self, flush_cache = True) -> list():
        if flush_cache:
          self.__update_cache_state()
        if self._neo4j_node_labels is None:
            self._neo4j_node_labels = list(self._neo4j_nodes.keys())
            self._neo4j_node_labels.sort()
        return self._neo4j_node_labels

    def __edge_name_transform(self, edge, source, target, transform_name):
        if transform_name:
            return source + '_' + edge + '_' + target
        else:
            return edge

    def __neo4j_unlabeled_vertex_name(self):
        return ''

    def __xgt_unlabeled_vertex_name(self):
        return 'unlabeled'

    # TODO(landwehrj) : Is there a way to detect the cache is stale
    # One option is to use the Neo4j count store of relationship/nodes
    # to check if there are changes there. This wouldn't work in certain
    # cases. Is there a way to get database modification time?
    # Is it possible to query individual schema elements?
    def __update_cache_state(self):
        self._neo4j_relationship_types = None
        self._neo4j_node_type_properties = None
        self._neo4j_rel_type_properties = None
        self._neo4j_property_keys = None
        self._neo4j_node_labels = None
        self._neo4j_nodes = None
        n = self.neo4j_node_type_properties
        self._neo4j_nodes = self.__neo4j_process_nodes(n)
        e = self.neo4j_rel_type_properties
        self._neo4j_edges = self.__neo4j_process_edges(e)
        self.__add_neo4j_schema_connectivity_to_neo4j_edges()

