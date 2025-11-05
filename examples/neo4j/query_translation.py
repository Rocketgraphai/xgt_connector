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

from xgt_connector import Neo4jConnector, Neo4jDriver
import xgt

xgt_server = xgt.Connection()

neo4j_driver = Neo4jDriver(auth=('neo4j', 'foo'))
c = Neo4jConnector(xgt_server, neo4j_driver)

def cleanup_neo4j_database(neo4j_driver):
    # clean up neo4j database
    neo4j_driver.query("MATCH (a:TestNode) DETACH DELETE a").finalize()
    neo4j_driver.query("MATCH (a:TestNodeC) DETACH DELETE a").finalize()

cleanup_neo4j_database(neo4j_driver)

# Create graph data for this test
neo4j_driver.query("create (a:TestNodeA:TestNode{descr:'NodeA'})").finalize()
neo4j_driver.query("create (a:TestNodeB:TestNode{descr:'NodeB'})").finalize()
neo4j_driver.query("match(a:TestNode) create (a)-[:REL01]->(:TestNodeC{descr:'NodeC'})").finalize()

nodes_to_copy = [
    'TestNodeA',
    'TestNodeB',
    'TestNodeC',
    'TestNode',
]
edges_to_copy = {
    'REL01' : None,
}

c.transfer_to_xgt(vertices=nodes_to_copy, edges=edges_to_copy)

query = """
MATCH (:TestNodeB)-[:REL01]->(:TestNodeC)
RETURN count(*)
"""

def run_query(query):
    """
    Run a query in Neo4j, then translate that query using the connector,
    passing the resulting query to xGT for running there.
    """
    print(f"Query:\n{query}")
    # Get results with Neo4j
    with neo4j_driver.query(query, write=False) as job:
        for row in job.result():
            print(f"Neo4j counted {row[0]} answers")
    
    translated_query = c.translate_query(query)
    print(f"Translated Query:\n{translated_query}")
    job = xgt_server.run_job(translated_query)
    print(f"xGT counted {job.get_data()[0][0]} answers")

run_query("""
    MATCH (:TestNodeB)-[:REL01]->(:TestNodeC)
    RETURN count(*)
    """)

run_query("""
    MATCH (:TestNode)-[:REL01]->(:TestNodeC)
    RETURN count(*)
    """)

cleanup_neo4j_database(neo4j_driver)
