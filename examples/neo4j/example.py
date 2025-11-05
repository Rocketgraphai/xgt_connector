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

from pprint import pprint
from xgt_connector import Neo4jConnector, Neo4jDriver
import xgt

xgt_server = xgt.Connection()

neo4j_driver = Neo4jDriver(auth=('neo4j', 'foo'))
c = Neo4jConnector(xgt_server, neo4j_driver)

nodes_to_copy = [
    'Forum',
    'Organisation',
    'Person',
    'Tag',
    'TagClass',
]
edges_to_copy = {
    'KNOWS' : None,
    'WORK_AT' : {'source' : 'Person', 'target' : 'Organisation'},
    'HAS_TAG' : None,
}

def individual_steps(nodes_to_copy, edges_to_copy):
    """
    This function shows the individual steps that are invoked for a call to
    `c.transfer_to_xgt(nodes_to_copy, edges_to_copy)`.

    Note that the individual steps would allow a user to update/modify the
    xGT schema prior to creating the frames in xGT.
    """
    xgt_schema = c.get_xgt_schemas(vertices=nodes_to_copy, edges=edges_to_copy)
    # Can update/modify schema parts (e.g., xgt.DATETIME instead of xgt.TEXT)
    c.create_xgt_schemas(xgt_schema)
    c.copy_data_to_xgt(xgt_schemas)


c.transfer_to_xgt(vertices=nodes_to_copy, edges=edges_to_copy)
