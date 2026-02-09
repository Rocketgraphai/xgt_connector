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

from pprint import pprint
from xgt_connector import Neo4jConnector
from neo4j import GraphDatabase
import xgt

xgt_server = xgt.Connection()

neo4j_driver = GraphDatabase.driver("bolt://localhost", auth=('neo4j', 'foo'))
c = Neo4jConnector(xgt_server, neo4j_driver)

def show(label, values):
    print("\n========> " + label)
    pprint(values)

show("relationship types:", c.neo4j_relationship_types)
show("node labels:", c.neo4j_node_labels)
show("property keys:", c.neo4j_property_keys)
show("node type properties:", c.neo4j_node_type_properties)
show("rel type properties:", c.neo4j_rel_type_properties)
show("nodes:", c.neo4j_nodes)
show("edges:", c.neo4j_edges)

