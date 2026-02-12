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

import unittest
from parameterized import parameterized_class
import time

import neo4j
import xgt
from xgt_connector import Neo4jConnector, Neo4jDriver

@parameterized_class([
   { "driver": "neo4j" },
   { "driver": "neo4j-bolt" },
])
class TestXgtNeo4jConnector(unittest.TestCase):
  # Print all diffs on failure.
  maxDiff=None
  @classmethod
  def setup_class(cls):
    # Create a connection to Rocketgraph xGT
    cls.xgt = xgt.Connection()
    try:
      cls.xgt.create_namespace('test')
    except:
      pass
    cls.xgt.set_default_namespace('test')
    cls.neo4j_driver, cls.conn = cls._setup_connector(cls.driver)
    return

  @classmethod
  def teardown_class(cls):
    del cls.conn
    cls.xgt.drop_namespace('test', force_drop = True)
    del cls.xgt

  @classmethod
  def _setup_connector(cls, connector_type, retries = 20):
    try:
      if connector_type == "neo4j":
        driver = neo4j.GraphDatabase.driver("neo4j://localhost", auth=('neo4j', 'foo'))
      else:
        driver = Neo4jDriver(auth=('neo4j', 'foo'), driver=connector_type)
      conn = Neo4jConnector(cls.xgt, driver)
      # Validate the db can run queries.
      with conn._neo4j_driver.bolt.session() as session:
        session.run("call db.info()")
      return (conn._neo4j_driver, conn)
    except (neo4j.exceptions.ServiceUnavailable):
      print(f"Neo4j Unavailable, retries = {retries}")
      if retries > 0:
        time.sleep(3)
        return cls._setup_connector(connector_type, retries - 1)
    if connector_type == "neo4j":
        driver = neo4j.GraphDatabase.driver("neo4j://localhost", auth=('neo4j', 'foo'))
    else:
        driver = Neo4jDriver(auth=('neo4j', 'foo'), driver=connector_type)
    conn = Neo4jConnector(cls.xgt, driver)
    return (conn._neo4j_driver, conn)

  def setup_method(self, method):
    self._erase_neo4j_database()

  def teardown_method(self, method):
    self._erase_neo4j_database()

  def test_connector_creation(self) -> None:
    # Must pass at least one parameter to constructor.
    with self.assertRaises(TypeError):
      c = Neo4jConnector()

  def test_neo4j_properties(self):
    assert isinstance(self.neo4j_driver, Neo4jDriver)
    rel = self.conn.neo4j_relationship_types
    assert isinstance(rel, list)
    assert len(rel) == 0
    labels = self.conn.neo4j_node_labels
    assert isinstance(labels, list)
    assert len(labels) == 0
    props = self.conn.neo4j_property_keys
    assert isinstance(props, list)
    assert len(props) >= 0
    props = self.conn.neo4j_node_type_properties
    assert isinstance(props, list)
    assert len(props) == 0
    props = self.conn.neo4j_rel_type_properties
    assert isinstance(props, list)
    assert len(props) == 0
    nodes = self.conn.neo4j_nodes
    assert isinstance(nodes, dict)
    assert len(nodes) == 0
    edges = self.conn.neo4j_edges
    assert isinstance(edges, dict)
    assert len(edges) == 0

  def test_node_attributes(self):
    self._populate_node()
    c = self.conn
    xgt_schema = c.get_xgt_schemas(vertices=['Node'])
    print(xgt_schema)
    vertices = xgt_schema['vertices']['Node']
    schema = dict(vertices['schema'])
    assert len(schema) == 11
    assert schema['int'] == 'int'
    assert schema['real'] == 'float'
    assert schema['str'] == 'text'
    assert schema['bool'] == 'boolean'
    assert schema['date_attr'] == 'date'
    assert schema['time_attr'] == 'time'
    assert schema['datetime_attr'] == 'datetime'
    assert schema['localtime_attr'] == 'time'
    assert schema['localdatetime_attr'] == 'datetime'
    assert schema['duration_attr'] == 'int'
    print(schema)
    print(c.neo4j_node_type_properties)

  def test_neo4j_relationship_types(self):
    c = self.conn
    self.neo4j_driver.query(
        'CREATE (:Node2{})-[:Relationship1{}]->(:Node1{}), (:Node1{})-[:Relationship2{int: 1}]->(:Node2{})').finalize()
    self.assertCountEqual(c.neo4j_relationship_types, ['Relationship1', 'Relationship2'])

  def test_neo4j_node_labels(self):
    c = self.conn
    self.neo4j_driver.query('CREATE (:Node1{}), (:Node2{int : 1})').finalize()
    self.assertCountEqual(c.neo4j_node_labels, ['Node1', 'Node2'])

  def test_neo4j_property_keys(self):
    c = self.conn
    self._populate_node_working_types_bolt()
    self.assertCountEqual(
        c.neo4j_property_keys,
        ['bool', 'bool_array', 'date_array', 'date_attr', 'datetime_array', 'datetime_attr', 'double_array', 'duration_array', 'duration_attr',
         'geo_attr2', 'geo_attr3', 'int', 'localdatetime_array', 'localdatetime_attr', 'localtime_array', 'localtime_attr', 'long_array',
         'point_array', 'point_attr2', 'point_attr3', 'real', 'str', 'string_array', 'time_array', 'time_attr', 'x', 'y'])

  def test_neo4j_rel_type_properties(self):
    c = self.conn
    self.neo4j_driver.query(
        'CREATE (:Node2{})-[:Relationship1{}]->(:Node1{}), (:Node1{})-[:Relationship2{int: 1, str: "hello"}]->(:Node2{}),'
        '(:Node1{})-[:Relationship2{str: "goodbye"}]->(:Node2{})').finalize()
    self.assertCountEqual(
        c.neo4j_rel_type_properties,
        [{'relType': ':`Relationship1`', 'propertyName': None, 'propertyTypes': None, 'mandatory': False},
         {'relType': ':`Relationship2`', 'propertyName': 'int', 'propertyTypes': ['Long'], 'mandatory': False},
         {'relType': ':`Relationship2`', 'propertyName': 'str', 'propertyTypes': ['String'], 'mandatory': True}])

  def test_neo4j_node_type_properties(self):
    c = self.conn
    self.neo4j_driver.query(
        'CREATE (:Node1{}), (:Node2{int : 1, str : "hello"}), (:Node2{str : "goodbye"})').finalize()
    self.assertCountEqual(
        c.neo4j_node_type_properties,
        [{'nodeType': ':`Node1`', 'nodeLabels': ['Node1'], 'propertyName': None, 'propertyTypes': None, 'mandatory': False},
         {'nodeType': ':`Node2`', 'nodeLabels': ['Node2'], 'propertyName': 'int', 'propertyTypes': ['Long'], 'mandatory': False},
         {'nodeType': ':`Node2`', 'nodeLabels': ['Node2'], 'propertyName': 'str', 'propertyTypes': ['String'], 'mandatory': True}])

  def test_neo4j_edges(self):
    c = self.conn
    self.neo4j_driver.query(
        'CREATE (:Node2{})-[:Relationship1{}]->(:Node1{}), (:Node1{})-[:Relationship2{int: 1}]->(:Node2{})').finalize()
    assert len(c.neo4j_edges) == 2
    assert c.neo4j_edges['Relationship1']['endpoints'] == {('Node2', 'Node1')}
    assert c.neo4j_edges['Relationship1']['sources'] == {'Node2'}
    assert c.neo4j_edges['Relationship1']['targets'] == {'Node1'}
    assert c.neo4j_edges['Relationship1']['schema'] == {}
    assert c.neo4j_edges['Relationship2']['endpoints'] == {('Node1', 'Node2')}
    assert c.neo4j_edges['Relationship2']['sources'] == {'Node1'}
    assert c.neo4j_edges['Relationship2']['targets'] == {'Node2'}
    assert c.neo4j_edges['Relationship2']['schema'] == {'int' : 'Long'}

  def test_neo4j_edges_multi(self):
    c = self.conn
    self.neo4j_driver.query(
          'CREATE (:Node2{})-[:Relationship1{int: 2}]->(:Node1{}), (:Node1{})-[:Relationship1{int: 1}]->(:Node2{})').finalize()
    assert len(c.neo4j_edges) == 1
    assert c.neo4j_edges['Relationship1']['endpoints'] == {('Node1', 'Node2'), ('Node2', 'Node1')}
    assert c.neo4j_edges['Relationship1']['sources'] == {'Node1', 'Node2'}
    assert c.neo4j_edges['Relationship1']['targets'] == {'Node1', 'Node2'}
    assert c.neo4j_edges['Relationship1']['schema'] == {'int' : 'Long'}

  def test_neo4j_nodes(self):
    c = self.conn
    self.neo4j_driver.query('CREATE (:Node1{}), (:Node2{int : 1})').finalize()
    assert len(c.neo4j_nodes) == 2
    assert c.neo4j_nodes['Node1'] == {}
    assert c.neo4j_nodes['Node2'] == {'int' : 'Long'}

  def test_graph_update_after_connector_created(self):
    c = self.conn
    self._populate_node()
    xgt_schema = c.get_xgt_schemas(vertices=['Node'])
    vertices = xgt_schema['vertices']['Node']
    schema = dict(vertices['schema'])
    assert len(schema) == 11
    assert schema['int'] == 'int'
    assert schema['real'] == 'float'
    assert schema['str'] == 'text'
    assert schema['bool'] == 'boolean'
    assert schema['date_attr'] == 'date'
    assert schema['time_attr'] == 'time'
    assert schema['datetime_attr'] == 'datetime'
    assert schema['localtime_attr'] == 'time'
    assert schema['localdatetime_attr'] == 'datetime'
    assert schema['duration_attr'] == 'int'

  def test_graph_delete_after_connector_created(self):
    self._populate_node()
    c = self.conn
    self.neo4j_driver.query("MATCH (n) DETACH DELETE n").finalize()
    with self.assertRaises(ValueError):
      xgt_schema = c.get_xgt_schemas(vertices=['Node'])

  def disable_test_transfer_node(self):
    self._populate_node()
    c = self.conn
    xgt_schema = c.get_xgt_schemas(vertices=['Node'])
    c.create_xgt_schemas(xgt_schema)
    for vertex, schema in xgt_schema['vertices'].items():
      table_schema = schema['schema']
      attributes = {_:t for _, t in table_schema}
      print(f"\nAttributes: {attributes}")
    c.copy_data_to_xgt(xgt_schema)
    node_frame = self.xgt.get_frame('Node')
    assert node_frame.num_rows == 1

  def test_transfer_node_working_types_bolt(self):
    self._populate_node_working_types_bolt()
    c = self.conn
    xgt_schema = c.get_xgt_schemas(vertices=['Node'])
    c.create_xgt_schemas(xgt_schema)
    for vertex, schema in xgt_schema['vertices'].items():
      table_schema = schema['schema']
      attributes = {_:t for _, *t  in table_schema}
      print(f"\nAttributes: {attributes}")
    c.copy_data_to_xgt(xgt_schema)
    node_frame = self.xgt.get_frame('Node')
    assert node_frame.num_rows == 3
    print(node_frame.get_data())

  def test_transfer_nodes_to_neo4j(self):
    self._populate_node_working_types_bolt()
    c = self.conn
    c.transfer_to_xgt(vertices=['Node'])
    node_frame = self.xgt.get_frame('Node')
    assert node_frame.num_rows == 3
    expected = [row[1:] for row in node_frame.get_data()]
    self.neo4j_driver.query("MATCH (n) DETACH DELETE n").finalize()
    c.transfer_to_neo4j(vertices=['Node'])
    self.xgt.drop_frame("Node")
    c.transfer_to_xgt(vertices=['Node'])
    node_frame = self.xgt.get_frame('Node')
    assert node_frame.num_rows == 3
    result = [row[1:] for row in node_frame.get_data()]
    # The column ordering can change when uploading to neo4j
    # So we just need to verify the None rows are correct
    # and the same elements are in the row with data, but with a different order.
    expected_pos = 0
    result_pos = 0
    for i in range(0,3):
        if result[i][0] != None:
            result_pos = i
        else:
            assert result[i].count(None) == len(result[i])
        if expected[i][0] != None:
            expected_pos = i
        else:
            assert expected[i].count(None) == len(expected[i])
    self.assertCountEqual(expected[expected_pos], result[result_pos])

  def test_transfer_edges_to_neo4j(self):
    self._populate_relationship_working_types_bolt()
    c = self.conn
    c.transfer_to_xgt(edges=['Relationship'])
    node_frame = self.xgt.get_frame('Node')
    edge_frame = self.xgt.get_frame('Relationship')
    assert edge_frame.num_rows == 3
    node_expected = [row[1:] for row in node_frame.get_data()]
    edge_expected = [row[2:] for row in edge_frame.get_data()]
    self.neo4j_driver.query("MATCH (n) DETACH DELETE n").finalize()
    c.transfer_to_neo4j(edges=['Relationship'])
    self.xgt.drop_frame("Relationship")
    self.xgt.drop_frame("Node")
    c.transfer_to_xgt(edges=['Relationship'])
    node_frame = self.xgt.get_frame('Node')
    edge_frame = self.xgt.get_frame('Relationship')
    assert edge_frame.num_rows == 3
    node_result = [row[1:] for row in node_frame.get_data()]
    edge_result = [row[2:] for row in edge_frame.get_data()]
    self.assertCountEqual(node_expected, node_result)
    # The column ordering can change when uploading to neo4j
    # So we just need to verify the None rows are correct
    # and the same elements are in the row with data, but with a different order.
    expected_pos = 0
    result_pos = 0
    for i in range(0,3):
        if edge_result[i][0] != None:
            result_pos = i
        else:
            assert edge_result[i].count(None) == len(edge_result[i])
        if edge_expected[i][0] != None:
            expected_pos = i
        else:
            assert edge_expected[i].count(None) == len(edge_expected[i])
    self.assertCountEqual(edge_expected[expected_pos], edge_result[result_pos])

  def test_transfer_relationship_working_types_bolt(self):
    self._populate_relationship_working_types_bolt()
    c = self.conn
    xgt_schema = c.get_xgt_schemas(vertices=['Node'], edges=['Relationship'])
    c.create_xgt_schemas(xgt_schema)
    c.copy_data_to_xgt(xgt_schema)
    edge_frame = self.xgt.get_frame('Relationship')
    assert edge_frame.num_rows == 3
    print(edge_frame.get_data())
    self.xgt.drop_frame("Relationship")

  def test_transfer_relationship_working_types_bolt_map(self):
    self._populate_relationship_working_types_bolt()
    c = self.conn
    xgt_schema = c.get_xgt_schemas(vertices=[('Node', 'n')], edges=[('Relationship', 'r')])
    c.create_xgt_schemas(xgt_schema)
    c.copy_data_to_xgt(xgt_schema)
    node_frame = self.xgt.get_frame('n')
    edge_frame = self.xgt.get_frame('r')
    assert node_frame.num_rows == 6
    assert edge_frame.num_rows == 3
    print(edge_frame.get_data())
    self.xgt.drop_frame('r')

  def test_transfer_relationship_without_vertex_bolt(self):
    self._populate_relationship_working_types_bolt()
    c = self.conn
    xgt_schema = c.get_xgt_schemas(edges=['Relationship'])
    c.create_xgt_schemas(xgt_schema)
    c.copy_data_to_xgt(xgt_schema)
    node_frame = self.xgt.get_frame('Node')
    edge_frame = self.xgt.get_frame('Relationship')
    assert node_frame.num_rows == 6
    assert edge_frame.num_rows == 3
    assert node_frame.get_data(length=1)[0][1] == 1
    self.xgt.drop_frame("Relationship")

  def test_transfer_relationship_without_vertex_bolt_two_phase(self):
    self._populate_relationship_working_types_bolt()
    c = self.conn
    c.transfer_to_xgt(vertices=['Node'])
    xgt_schema = c.get_xgt_schemas(edges=['Relationship'], import_edge_nodes=False)
    c.create_xgt_schemas(xgt_schema, append=True)
    c.copy_data_to_xgt(xgt_schema)
    node_frame = self.xgt.get_frame('Node')
    edge_frame = self.xgt.get_frame('Relationship')
    assert node_frame.num_rows == 6
    assert edge_frame.num_rows == 3
    assert node_frame.get_data(length=1)[0][1] == 1
    self.xgt.drop_frame("Relationship")

  def test_transfer_everything_bolt(self):
    self._populate_relationship_working_types_bolt()
    c = self.conn
    xgt_schema = c.get_xgt_schemas()
    c.create_xgt_schemas(xgt_schema)
    c.copy_data_to_xgt(xgt_schema)
    node_frame = self.xgt.get_frame('Node')
    edge_frame = self.xgt.get_frame('Relationship')
    assert node_frame.num_rows == 6
    assert edge_frame.num_rows == 3
    self.xgt.drop_frame("Relationship")

  def test_append(self):
    c = self.conn
    self.neo4j_driver.query(
      'CREATE (:Node{int: 343, str: "string"})').finalize()
    xgt_schema = c.get_xgt_schemas(vertices=['Node'])
    c.create_xgt_schemas(xgt_schema)

    c.copy_data_to_xgt(xgt_schema)
    c.create_xgt_schemas(xgt_schema, append=True)

    self.neo4j_driver.query("MATCH (n) DETACH DELETE n").finalize()
    self.neo4j_driver.query(
        'CREATE (:Node{int: 344, str: "string"})').finalize()
    c.copy_data_to_xgt(xgt_schema)
    node_frame = self.xgt.get_frame('Node')
    assert node_frame.num_rows == 2

    c.create_xgt_schemas(xgt_schema, append=False)
    node_frame = self.xgt.get_frame('Node')
    assert node_frame.num_rows == 0

  def test_dropping(self):
    c = self.conn
    self.neo4j_driver.query(
        'CREATE (:Node{})-[:Relationship]->(:Node{})').finalize()
    xgt_schema1 = c.get_xgt_schemas(vertices=['Node'], edges=['Relationship'])
    xgt_schema2 = c.get_xgt_schemas(vertices=['Node'])

    c.create_xgt_schemas(xgt_schema1)
    self.xgt.get_frame('Node')
    self.xgt.get_frame('Relationship')

    c.create_xgt_schemas(xgt_schema1)
    self.xgt.get_frame('Node')
    self.xgt.get_frame('Relationship')

    with self.assertRaises(xgt.XgtFrameDependencyError):
        c.create_xgt_schemas(xgt_schema2)
    c.create_xgt_schemas(xgt_schema2, force=True)
    self.xgt.get_frame('Node')
    with self.assertRaises(xgt.XgtNameError):
        self.xgt.get_frame('Relationship')

  def test_multiple_node_labels_to(self):
    c = self.conn
    self.neo4j_driver.query(
        'CREATE (:Node1{})-[:Relationship{}]->(:Node1{}), (:Node1{})-[:Relationship{}]->(:Node2{})').finalize()
    schema = c.get_xgt_schemas(vertices=['Node1', 'Node2'], edges=['Relationship'])
    c.create_xgt_schemas(schema)
    c.copy_data_to_xgt(schema)

    node_frame = self.xgt.get_frame('Node1_Relationship_Node1')
    assert node_frame.num_rows == 1
    node_frame = self.xgt.get_frame('Node1_Relationship_Node2')
    assert node_frame.num_rows == 1
    self.xgt.drop_frame("Node1_Relationship_Node1")
    self.xgt.drop_frame("Node1_Relationship_Node2")

  def test_multiple_node_labels_from(self):
    c = self.conn
    self.neo4j_driver.query(
        'CREATE (:Node1{})-[:Relationship{}]->(:Node1{}), (:Node2{})-[:Relationship{}]->(:Node1{})').finalize()
    schema = c.get_xgt_schemas(vertices=['Node1', 'Node2'], edges=['Relationship'])
    c.create_xgt_schemas(schema)
    c.copy_data_to_xgt(schema)

    node_frame = self.xgt.get_frame('Node1_Relationship_Node1')
    assert node_frame.num_rows == 1
    node_frame = self.xgt.get_frame('Node2_Relationship_Node1')
    assert node_frame.num_rows == 1
    self.xgt.drop_frame("Node1_Relationship_Node1")
    self.xgt.drop_frame("Node2_Relationship_Node1")

  def test_multiple_property_types_vertex_negative(self):
    c = self.conn
    self.neo4j_driver.query(
        'CREATE (:Node{x: 1})-[:Relationship{}]->(:Node{x: "hello"})').finalize()
    with self.assertRaises(ValueError):
        c.get_xgt_schemas(vertices=['Node'], edges=['Relationship'])

  def test_multiple_property_types_edge_negative(self):
    c = self.conn
    self.neo4j_driver.query(
        'CREATE (:Node{})-[:Relationship{x: 1}]->(:Node{}), (:Node{})-[:Relationship{x: "hello"}]->(:Node{})').finalize()
    with self.assertRaises(ValueError):
      c.get_xgt_schemas(vertices=['Node'], edges=['Relationship'])

  def test_different_properties_combine_into_single_schema(self):
    c = self.conn
    self.neo4j_driver.query('CREATE (:Node{x: 1}), (:Node{y: "hello"})').finalize()
    schema = c.get_xgt_schemas(vertices=['Node'])
    node_schema = schema['vertices']['Node']['schema']
    assert len(node_schema) == 3

  def test_transfer_no_data(self):
    c = self.conn
    # Transfer all graphs:
    c.transfer_to_xgt()
    # Transfer all graphs in namespace:
    c.transfer_to_neo4j()

  def test_transfer_missing_graphs(self):
    c = self.conn
    with self.assertRaises(ValueError):
        c.transfer_to_xgt(vertices=['cars'])
    with self.assertRaises(ValueError):
        c.transfer_to_xgt(edges=['cars'])
    with self.assertRaises(ValueError):
        c.get_xgt_schemas(vertices=['cars'])
    with self.assertRaises(ValueError):
        c.get_xgt_schemas(edges=['cars'])
    with self.assertRaises(xgt.XgtNameError):
        c.transfer_to_neo4j(vertices=['cars'])
    with self.assertRaises(xgt.XgtNameError):
        c.transfer_to_neo4j(edges=['cars'])

  def test_empty_labels(self):
    c = self.conn
    self.neo4j_driver.query('CREATE ()').finalize()
    c.transfer_to_xgt(vertices=[''])
    node_frame = self.xgt.get_frame('unlabeled')
    assert node_frame.num_rows == 1

  def test_map_empty_labels(self):
    c = self.conn
    self.neo4j_driver.query('CREATE ()').finalize()
    c.transfer_to_xgt(vertices=[('', 'custom_name')])
    node_frame = self.xgt.get_frame('custom_name')
    assert node_frame.num_rows == 1
    with self.assertRaises(xgt.XgtNameError):
        node_frame = self.xgt.get_frame('unlabeled')

  def test_empty_labels_schema(self):
    c = self.conn
    self.neo4j_driver.query('CREATE ({int:2})').finalize()
    c.transfer_to_xgt(vertices=[''])
    node_frame = self.xgt.get_frame('unlabeled')
    res = self.xgt.run_job('match (v) return v.int')
    assert node_frame.num_rows == 1
    assert res.get_data()[0][0] == 2
    self.neo4j_driver.query("MATCH (n) DETACH DELETE n").finalize()
    self.neo4j_driver.query('CREATE ({str:"bbb"})').finalize()
    c.transfer_to_xgt(vertices=[''])
    node_frame = self.xgt.get_frame('unlabeled')
    res = self.xgt.run_job('match (v) return v.str')
    assert node_frame.num_rows == 1
    assert res.get_data()[0][0] == "bbb"

  def test_edge_empty_labels(self):
    c = self.conn
    self.neo4j_driver.query(
        'CREATE ()-[:e1]->(), (:Node)-[:e2]->(), ()-[:e3]->(:Node)').finalize()
    c.transfer_to_xgt(edges=['e1', 'e2', 'e3'])
    node_frame = self.xgt.get_frame('e1')
    assert node_frame.num_rows == 1
    node_frame = self.xgt.get_frame('e2')
    assert node_frame.num_rows == 1
    node_frame = self.xgt.get_frame('e3')
    assert node_frame.num_rows == 1
    node_frame = self.xgt.get_frame('unlabeled')
    assert node_frame.num_rows == 4
    node_frame = self.xgt.get_frame('Node')
    assert node_frame.num_rows == 2

  def test_edge_empty_labels_schema(self):
    c = self.conn
    self.neo4j_driver.query(
        'CREATE ()-[:e1]->({int:1}), (:Node)-[:e2]->({str:"aaa"}), ({bool:True})-[:e3]->(:Node)').finalize()
    c.transfer_to_xgt(edges=['e1', 'e2', 'e3'])
    node_frame = self.xgt.get_frame('e1')
    res = self.xgt.run_job('match ()-[:e1]->(v) return v.int')
    assert node_frame.num_rows == 1
    assert res.get_data()[0][0] == 1
    node_frame = self.xgt.get_frame('e2')
    res = self.xgt.run_job('match ()-[:e2]->(v) return v.str')
    assert node_frame.num_rows == 1
    assert res.get_data()[0][0] == "aaa"
    node_frame = self.xgt.get_frame('e3')
    res = self.xgt.run_job('match (v)-[:e3]->() return v.bool')
    assert node_frame.num_rows == 1
    assert res.get_data()[0][0] == True
    node_frame = self.xgt.get_frame('unlabeled')
    assert node_frame.num_rows == 4
    node_frame = self.xgt.get_frame('Node')
    assert node_frame.num_rows == 2

  def test_map_edge_empty_labels(self):
    c = self.conn
    self.neo4j_driver.query(
        'CREATE ()-[:e1]->(), (:Node)-[:e2]->(), ()-[:e3]->(:Node)').finalize()
    c.transfer_to_xgt(vertices=[('', 'custom_empty'), ('Node', 'custom_Node')], edges=[('e1', 'edge1'), ('e2', 'edge2'), 'e3'])
    node_frame = self.xgt.get_frame('edge1')
    assert node_frame.num_rows == 1
    node_frame = self.xgt.get_frame('edge2')
    assert node_frame.num_rows == 1
    node_frame = self.xgt.get_frame('e3')
    assert node_frame.num_rows == 1
    node_frame = self.xgt.get_frame('custom_empty')
    assert node_frame.num_rows == 4
    node_frame = self.xgt.get_frame('custom_Node')
    assert node_frame.num_rows == 2
    with self.assertRaises(xgt.XgtNameError):
        node_frame = self.xgt.get_frame('unlabeled')
    with self.assertRaises(xgt.XgtNameError):
        node_frame = self.xgt.get_frame('Node')

  def test_edge_empty_labels_schema_no_implicit(self):
    c = self.conn
    self.neo4j_driver.query(
        'CREATE ()-[:e1]->({int:1}), (:Node)-[:e2]->({str:"aaa"}), ({bool:True})-[:e3]->(:Node)').finalize()
    c.transfer_to_xgt(vertices=['', 'Node'])
    c.transfer_to_xgt(edges=['e1', 'e2', 'e3'], append=True, import_edge_nodes=False)
    node_frame = self.xgt.get_frame('e1')
    res = self.xgt.run_job('match ()-[:e1]->(v) return v.int')
    assert node_frame.num_rows == 1
    assert res.get_data()[0][0] == 1
    node_frame = self.xgt.get_frame('e2')
    res = self.xgt.run_job('match ()-[:e2]->(v) return v.str')
    assert node_frame.num_rows == 1
    assert res.get_data()[0][0] == "aaa"
    node_frame = self.xgt.get_frame('e3')
    res = self.xgt.run_job('match (v)-[:e3]->() return v.bool')
    assert node_frame.num_rows == 1
    assert res.get_data()[0][0] == True
    node_frame = self.xgt.get_frame('unlabeled')
    assert node_frame.num_rows == 4
    node_frame = self.xgt.get_frame('Node')
    assert node_frame.num_rows == 2

  def test_query_translator_loop_data(self):
    self.neo4j_driver.query("create (a:Node{int:1})-[b:EDGE{int:1}]->(a)").finalize()
    query = "match(a) return a"
    assert query == self.conn.translate_query(query)
    query = "match(a:Node) return a"
    assert query == self.conn.translate_query(query)
    query = "match(v0)-[]->(v1) return v0"
    assert query == self.conn.translate_query(query)
    query = "match(v0:Node)-[]->(v1) return v0"
    assert query == self.conn.translate_query(query)
    query = "match(v0:Node)-[]->(v1:Node) return v0"
    assert query == self.conn.translate_query(query)
    query = "match(v0:Node)-[e:EDGE]->(v1:Node) return v0"
    assert query == self.conn.translate_query(query)
    query = "match()-[e]->() return v0"
    assert query == self.conn.translate_query(query)
    query = "match()-[e:EDGE]->() return v0"
    assert query == self.conn.translate_query(query)
    query = "match(a)-->()-->(a) return a"
    assert query == self.conn.translate_query(query)
    query = "match(a)-->()-->()-->(a) return a"
    assert query == self.conn.translate_query(query)
    query = "match(a:Node)-->()-->(a) return a"
    assert query == self.conn.translate_query(query)
    query = "match(a:Node)-->()-->()-->(a) return a"
    assert query == self.conn.translate_query(query)
    query = "match(a:Node)-->(e:Edge)-->(a) return a"
    assert query == self.conn.translate_query(query)
    query = "match(a:Node)-->(e1:Edge)-->(e2:Edge)-->(a) return a"
    assert query == self.conn.translate_query(query)

  def test_query_translator_loop_no_data(self):
    query = "match(a) return a"
    assert query == self.conn.translate_query(query)
    query = "match(a:Node) return a"
    assert query == self.conn.translate_query(query)
    query = "match(v0)-[]->(v1) return v0"
    assert query == self.conn.translate_query(query)
    query = "match(v0:Node)-[]->(v1) return v0"
    assert query == self.conn.translate_query(query)
    query = "match(v0:Node)-[]->(v1:Node) return v0"
    assert query == self.conn.translate_query(query)
    query = "match(v0:Node)-[e:EDGE]->(v1:Node) return v0"
    assert query == self.conn.translate_query(query)
    query = "match()-[e]->() return v0"
    assert query == self.conn.translate_query(query)
    query = "match()-[e:EDGE]->() return v0"
    assert query == self.conn.translate_query(query)
    query = "match(a)-->()-->(a) return a"
    assert query == self.conn.translate_query(query)
    query = "match(a)-->()-->()-->(a) return a"
    assert query == self.conn.translate_query(query)
    query = "match(a:Node)-->()-->(a) return a"
    assert query == self.conn.translate_query(query)
    query = "match(a:Node)-->()-->()-->(a) return a"
    assert query == self.conn.translate_query(query)
    query = "match(a:Node)-->(e:Edge)-->(a) return a"
    assert query == self.conn.translate_query(query)
    query = "match(a:Node)-->(e1:Edge)-->(e2:Edge)-->(a) return a"
    assert query == self.conn.translate_query(query)

  def test_query_translator_multiple_node_labels_to(self):
    c = self.conn
    self.neo4j_driver.query(
      'CREATE (:Node1{})-[:REL{}]->(:Node1{}), (:Node1{})-[:REL{}]->(:Node2{})').finalize()

    query = "MATCH (:Node1)-[:REL]->(b:Node1) RETURN count(*)"
    assert "Node1_REL_Node1" in c.translate_query(query)
    query = "MATCH (:Node1)-[:REL]->(b:Node2) RETURN count(*)"
    assert "Node1_REL_Node2" in c.translate_query(query)
    query = "MATCH (:Node2)-[:REL]->(b:Node1) RETURN count(*)"
    assert "Node2_REL_Node1" not in c.translate_query(query)
    query = "MATCH (:Node1)-[:REL]->(b:Node3) RETURN count(*)"
    assert "Node1_REL_Node3" not in c.translate_query(query)

  def test_query_translator_multiple_node_labels_from(self):
    c = self.conn
    self.neo4j_driver.query(
      'CREATE (:Node1{})-[:REL{}]->(:Node1{}), (:Node2{})-[:REL{}]->(:Node1{})').finalize()

    query = "MATCH (:Node1)-[:REL]->(b:Node1) RETURN count(*)"
    assert "Node1_REL_Node1" in c.translate_query(query)
    query = "MATCH (:Node2)-[:REL]->(b:Node1) RETURN count(*)"
    assert "Node2_REL_Node1" in c.translate_query(query)
    query = "MATCH (:Node1)-[:REL]->(b:Node2) RETURN count(*)"
    assert "Node1_REL_Node2" not in c.translate_query(query)
    query = "MATCH (:Node3)-[:REL]->(b:Node1) RETURN count(*)"
    assert "Node3_REL_Node1" not in c.translate_query(query)

  def test_query_translator_multiple_node_labels_to_and_from(self):
    c = self.conn
    self.neo4j_driver.query(
      'CREATE (:Node1{})-[:REL{}]->(:Node1{}), (:Node2{})-[:REL{}]->(:Node1{}),'
            '(:Node1{})-[:REL{}]->(:Node2{}), (:Node2{})-[:REL{}]->(:Node2{})').finalize()

    query = "MATCH (:Node1)-[:REL]->(b:Node1) RETURN count(*)"
    assert "Node1_REL_Node1" in c.translate_query(query)
    query = "MATCH (:Node2)-[:REL]->(b:Node1) RETURN count(*)"
    assert "Node2_REL_Node1" in c.translate_query(query)
    query = "MATCH (:Node1)-[:REL]->(b:Node2) RETURN count(*)"
    assert "Node1_REL_Node2" in c.translate_query(query)
    query = "MATCH (:Node3)-[:REL]->(b:Node1) RETURN count(*)"
    assert "Node3_REL_Node1" not in c.translate_query(query)
    query = "MATCH (:Node1)-[:REL]->(b:Node3) RETURN count(*)"
    assert "Node1_REL_Node3" not in c.translate_query(query)

  def _populate_node(self):
    self.neo4j_driver.query(
      # Integer, Float, String, Boolean, Point, Date, Time, LocalTime,
      # DateTime, LocalDateTime, and Duration.
      # FIXME: Point listed in comment above, but not in the list
      'CREATE (:Node{int: 343, real: 3.14, str: "string", bool: true, ' +
      'date_attr: date("+2015-W13-4"), time_attr: time("125035.556+0100"), ' +
      'datetime_attr: datetime("2015-06-24T12:50:35.556+0100"), ' +
      'localtime_attr: localtime("12:50:35.556"), ' +
      'localdatetime_attr: localdatetime("2015185T19:32:24"), ' +
      'duration_attr: duration("P14DT16H12M")})').finalize()

  # Point not working for bolt.
  def _populate_node_working_types_bolt(self):
    self.neo4j_driver.query(
      # Integer, Float, String, Boolean, Date, Time, LocalTime,
      # DateTime, LocalDateTime, various Points, and Lists.
      'CREATE (:Node{}), (:Node{int: 343, real: 3.14, str: "string", bool: true, ' +
      'date_attr: date("+2015-W13-4"), time_attr: time("125035.556+0100"), ' +
      'datetime_attr: datetime("2015-06-24T12:50:35.556+0100"), ' +
      'localtime_attr: localtime("12:50:35.556"), ' +
      'localdatetime_attr: localdatetime("2015185T19:32:24"), ' +
      'duration_attr: duration({days: 14, hours:16, minutes: 12}), ' +
      'point_attr2: point({x:0.5, y:1.2}), ' +
      'point_attr3: point({x:0.23, y:1.5, z:1.2}), ' +
      'geo_attr2: point({latitude:7.23, longitude:3.5}), ' +
      'geo_attr3: point({latitude:0.23, longitude:1.5, height:10.2}), ' +
      'bool_array: [true, false, false], ' +
      'long_array: [7, 1, 5], ' +
      'string_array: ["ad", "bc", "de"], ' +
      'double_array: [0.7, 1.9, 5.2], ' +
      'date_array: [date("+2015-W13-4"), date("+2000-W1-2"), date("+2011-W4-6")], ' +
      'time_array: [time("125035.556+0100"), time("110535.7+0500"), time("100000.0+0700")], ' +
      'datetime_array: [datetime("2015-06-24T12:50:35.556+0100"), datetime("2000-01-1T1:1:1+0400"), datetime("1904-02-1T10:40:12.34+0300")], ' +
      'localtime_array: [localtime("125035.556"), localtime("110535.7"), localtime("100000.0")], ' +
      'localdatetime_array: [localdatetime("2015-06-24T12:50:35.556"), localdatetime("2000-01-1T1:1:1"), localdatetime("1904-02-1T10:40:12.34")], ' +
      'duration_array: [duration({days: 14, hours:16, minutes: 12}), duration({days: 5, hours:5, minutes: 5}), duration({days: 0, hours:6, minutes: 1})], ' +
      'point_array: [point({x:0.5, y:1.2}), point({x:0.5, y:1.2}), point({x:0.5, y:1.2})]}), ' +
      '(:Node{})').finalize()

  # Point not working for bolt.
  def _populate_relationship_working_types_bolt(self):
    self.neo4j_driver.query(
      # Integer, Float, String, Boolean, Date, Time, LocalTime,
      # DateTime, LocalDateTime, various Points, and Lists.
      'CREATE (:Node{int: 1})-[:Relationship{}]->(:Node{int: 1}), (:Node{int: 1})-' +
      '[:Relationship{int: 343, real: 3.14, str: "string", bool: true, ' +
      'date_attr: date("+2015-W13-4"), time_attr: time("125035.556+0100"), ' +
      'datetime_attr: datetime("2015-06-24T12:50:35.556+0100"), ' +
      'localtime_attr: localtime("12:50:35.556"), ' +
      'localdatetime_attr: localdatetime("2015185T19:32:24"), ' +
      'duration_attr: duration({days: 14, hours:16, minutes: 12}),' +
      'point_attr2: point({x:0.5, y:1.2}), ' +
      'point_attr3: point({x:0.23, y:1.5, z:1.2}), ' +
      'geo_attr2: point({latitude:7.23, longitude:3.5}), ' +
      'geo_attr3: point({latitude:0.23, longitude:1.5, height:10.2}),' +
      'bool_array: [true, false, false], ' +
      'long_array: [7, 1, 5], ' +
      'string_array: ["ad", "bc", "de"], ' +
      'double_array: [0.7, 1.9, 5.2], ' +
      'date_array: [date("+2015-W13-4"), date("+2000-W1-2"), date("+2011-W4-6")], ' +
      'time_array: [time("125035.556+0100"), time("110535.7+0500"), time("100000.0+0700")], ' +
      'datetime_array: [datetime("2015-06-24T12:50:35.556+0100"), datetime("2000-01-1T1:1:1+0400"), datetime("1904-02-1T10:40:12.34+0300")], ' +
      'localtime_array: [localtime("125035.556"), localtime("110535.7"), localtime("100000.0")], ' +
      'localdatetime_array: [localdatetime("2015-06-24T12:50:35.556"), localdatetime("2000-01-1T1:1:1"), localdatetime("1904-02-1T10:40:12.34")], ' +
      'duration_array: [duration({days: 14, hours:16, minutes: 12}), duration({days: 5, hours:5, minutes: 5}), duration({days: 0, hours:6, minutes: 1})], ' +
      'point_array: [point({x:0.5, y:1.2}), point({x:0.5, y:1.2}), point({x:0.5, y:1.2})]}]' +
      '->(:Node{int: 1}), (:Node{int: 1})-[:Relationship{}]->(:Node{int: 1})').finalize()

  def _erase_neo4j_database(self):
    self.neo4j_driver.query("MATCH (n) DETACH DELETE n").finalize()
    self.xgt.drop_namespace('test', force_drop = True)
