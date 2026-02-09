#/usr/bin/env bash
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

set -euo pipefail
scriptdir=$(cd $(dirname $0) && pwd)

# go to repo root
cd ${scriptdir}/..

target=src/xgt_connector/neo4j_connector/frontend

curl -o antlr-4.jar https://www.antlr.org/download/antlr-4.10.1-complete.jar

rm -rf ${target}
cp tools/Cypher/Cypher.g4 .
java -Xmx500M -cp "antlr-4.jar" org.antlr.v4.Tool -o ${target} \
  -Dlanguage=Python3 -visitor Cypher.g4
rm -rf Cypher.g4
touch ${targt}/__init__.py

# clean up
rm -f antlr-4.jar
