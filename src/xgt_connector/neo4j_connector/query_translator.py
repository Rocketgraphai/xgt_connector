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

from antlr4 import InputStream, CommonTokenStream, ParseTreeWalker
from .frontend.CypherLexer import CypherLexer
from .frontend.CypherParser import CypherParser
from .frontend.CypherListener import CypherListener

class Xlater: pass

class QueryTranslator(object):
    """
    It is sometimes necessary to make alterations to naming of graph components
    as part of the automatic graph schema creation from a Neo4j database to 
    hold data in a Rocketgraph xGT server.  One example of this is when a
    relationship type consists of some edges from one source node label and
    other edges from a different source node label.

    Given a Cypher query that formulated to run against a Neo4j database, there
    may be some changes required in order to run that same query against a
    Rocketgraph xGT server holding a graph schema that has been auto-generated.

    This class provides the service of translating a Neo4j-targeted query into
    a Rocketgraph xGT-targeted query.
    """
    def __init__(self, xgt_schemas, verbose = False):
        """
        Initializes a QueryTranslator instance.

        Parameters
        ----------
        xgt_schemas : dict
            Information about an auto-generated schema for Rocketgraph xGT
            based on a Neo4j database.  The structure of this schema should
            be the same the data returned from the
            :py:meth:`~Neo4jConnector.get_xgt_schemas` method.
        verbose : bool
            Print detailed information.  Default is False
        """
        self._verbose = verbose
        self._edge_name_mapping = self._create_edge_name_mapping(xgt_schemas)

    def _create_edge_name_mapping(self, xlate_structure) -> dict():
        mapping = dict()
        for edge, values in xlate_structure['edges'].items():
            if len(values) > 1:
                res = []
                for value in values:
                    res.append({
                        "source" : value['source'],
                        "target" : value['target'],
                        "mapped_name" : f"{value['xgt_source']}_{edge}_{value['xgt_target']}",
                        })
                mapping[edge] = res
        if self._verbose:
            print("Edge Name Mapping:")
            pprint(mapping)
        return mapping
    
    def translate(self, query:str) -> str:
        """
        Translates a Cypher query from a Neo4j-targeted query to a Rocketgraph
        xGT-targeted query.

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
        lexer = CypherLexer(InputStream(query))
        stream = CommonTokenStream(lexer)
        parser = CypherParser(stream)
        tree = parser.oC_Cypher()

        walker = ParseTreeWalker()
        xlater = Xlater(verbose = self._verbose)
        walker.walk(xlater, tree)

        self._rewrites = dict()
        for edge in xlater.edges:
            self._add_rewrites_for_edge_frame_names(edge)

        new_query = self._rewrite_query(query)
        del self._rewrites
        return new_query

    def _add_rewrites_for_edge_frame_names(self, edge) -> None:
        if self._verbose:
            print("In _add_rewrites_for_edge_frame_names")
            pprint(edge)
        left_nodes = edge[0]
        relationship = edge[1]
        right_nodes = edge[2]
        if 'rel_types' not in relationship:
            return
        for frame_name in relationship['rel_types'].keys():
            if self._verbose:
                print(f"Exploring frame name: {frame_name}")
            if frame_name in self._edge_name_mapping:
                left_node_labels = left_nodes['labels']
                if len(left_node_labels) == 0:
                    source = None
                elif len(left_node_labels) == 1:
                    source = list(left_node_labels.keys())[0]
                else:
                    raise ValueError(f"Support for multi-label left nodes not yet support: {left_nodes}")
                right_node_labels = right_nodes['labels']
                if len(right_node_labels) == 0:
                    target = None
                elif len(right_node_labels) == 1:
                    target = list(right_node_labels.keys())[0]
                else:
                    raise ValueError(f"Support for multi-label nodes not yet support: {right_nodes}")

                swap_source_target = relationship['left_arrow'] and not relationship['right_arrow']
                if swap_source_target:
                    temp = source
                    source = target
                    target = temp

                if self._verbose:
                    print(f"----> Source: {source}")
                    print(f"----> Target: {target}")

                if source is not None and target is not None:
                    mapping = self._edge_name_mapping[frame_name]
                    if self._verbose:
                        print(f"Frame to adapt: (:{source})-[:{frame_name}]->(:{target})")
                        print(f"  Frame Name {frame_name} needs adapting, {len(mapping)} mapped frames")
                    for variant in mapping:
                        if variant['source'] == source and variant['target'] == target:
                            if self._verbose:
                                print(f"Use this variant: {variant}")
                            reltype_loc = relationship['rel_types'][frame_name].location
                            if reltype_loc['offset'] in self._rewrites:
                                raise ValueError(f"Internal Error:  Multiple rewrites at the same offset ({reltype_loc['offset']}) is ambiguous")
                            self._rewrites[reltype_loc['offset']] = {
                                'from':reltype_loc, 
                                'to':variant['mapped_name']}

    def _rewrite_query(self, query:str) -> str:
        """Produce a re-written query from the self._rewrites information."""
        if self._verbose:
            print(f"Rewrites:")
            pprint(self._rewrites)
        locations = list(self._rewrites.keys())
        locations.sort(reverse = True)
        for offset in locations:
            rewrite = self._rewrites[offset]
            length = rewrite['from']['length']
            new_text = rewrite['to']
            query = f"{query[:offset]}{new_text}{query[offset+length:]}"

        return query


class QueryElement(object):
    """
    Utility object to store an element of a query.

    The original text is available as a property, and the location within
    the original query is captured.  The location includes the byte offset
    into the query, the length of the element (in bytes), and the line
    number and column number of the start and the stop positions of the
    element.
    """
    def __init__(self, text:str, location):
        self._text = text
        self._location = location

    @property
    def text(self):
        return self._text
    @property
    def location(self):
        return self._location

    def __str__(self) -> str:
        return self._text
    def __repr__(self) -> str:
        return f"<QueryElement: [{self._text}], location: {self._location}"

class Xlater(CypherListener):
    def __init__(self, verbose = False):
        self._verbose = verbose
        self._AST_node_stack = []
        self._symbol_table_node_variables = dict()
        self._edges = []
        self._node_patterns = []
        self._relationship_patterns = []

    @property
    def edges(self):
        return self._edges
    @property
    def node_patterns(self):
        return self._node_patterns

    # Capture edges in patterns
    def exitOC_PatternElementChain(self, ctx:CypherParser.OC_PatternElementChainContext):
        self._trace_context(ctx, "OC_PatternElementChain")
        left_node = self._node_patterns[-2]
        right_node = self._node_patterns[-1]
        self._edges.append([left_node, self._relationship_patterns[-1], right_node])
        if self._verbose:
            print(f"  -->Push PatternElement Edge:")
            pprint(self._edges[-1])

    def exitOC_NodePattern(self, ctx:CypherParser.OC_NodePatternContext):
        self._trace_context(ctx, "OC_NodePattern")

        if ctx.oC_NodeLabels() is None:
            labels = []
        else:
            labels = self._AST_node_stack.pop()
        variable = self._nonterminal_or_none(ctx.oC_Variable())
        if len(labels) == 0 and variable in self._symbol_table_node_variables:
            labels = self._symbol_table_node_variables[variable]
        capture = {'fulltext':ctx.getText(), 'location':self._encode_location(ctx),
                    'variable':variable, 'labels':labels}
        if variable is not None:
            if self._verbose:
                print(f"symbol: {variable}, labels: {labels}")
                if variable in self._symbol_table_node_variables:
                    print(f"Variable {variable} already in symbol table: {self._symbol_table_node_variables[variable]}")
            self._symbol_table_node_variables[variable] = labels
        self._node_patterns.append(capture)
        if self._verbose:
            print(f"  -->Push NodePattern: {capture}")

    def exitOC_NodeLabels(self, ctx:CypherParser.OC_NodeLabelsContext):
        self._trace_context(ctx, "OC_NodeLabels")
        node_labels = dict()
        for child in ctx.children:
            if isinstance(child, CypherParser.OC_NodeLabelContext):
                node_label = self._AST_node_stack.pop()
                node_labels[node_label.text] = node_label
        self._AST_node_stack.append(node_labels)
        if self._verbose:
            print(f"  -->Push NLs: {node_labels}")

    def exitOC_NodeLabel(self, ctx:CypherParser.OC_NodeLabelContext):
        self._trace_context(ctx, "OC_NodeLabel")
        node_label = self._capture_element(ctx.oC_LabelName())
        self._AST_node_stack.append(node_label)
        if self._verbose:
            print(f"  -->Push NL: {node_label}")

    def exitOC_RelationshipPattern(self, ctx:CypherParser.OC_RelationshipPatternContext):
        self._trace_context(ctx, "OC_RelationshipPattern")
        if len(self._AST_node_stack) == 0:
            rel_detail = dict()
        else:
            rel_detail = self._AST_node_stack.pop()

        left_arrow = False
        right_arrow = False
        for child in ctx.children:
            if isinstance(child, CypherParser.OC_LeftArrowHeadContext):
                left_arrow = True
            if isinstance(child, CypherParser.OC_RightArrowHeadContext):
                right_arrow = True
        capture = {'fulltext':ctx.getText(), 'location':self._encode_location(ctx),
                   'left_arrow':left_arrow, 'right_arrow':right_arrow,
                  }
        for key in rel_detail.keys():
            if key == 'location':
                capture['detail_location'] = rel_detail[key]
            else:
                capture[key] = rel_detail[key]

        self._relationship_patterns.append(capture)
        if self._verbose:
            print(f"  -> Push RelationshipPattern: {capture}")

    def exitOC_RelationshipDetail(self, ctx:CypherParser.OC_RelationshipDetailContext):
        self._trace_context(ctx, "OC_RelationshipDetail")
        if ctx.oC_RelationshipTypes() is None:
            rel_types = dict()
        else:
            rel_types = self._AST_node_stack.pop()
        capture = {'fulltext':ctx.getText(), 'location':self._encode_location(ctx),
                    'variable':self._nonterminal_or_none(ctx.oC_Variable()),
                    'rel_types':rel_types,
                    'range_literal':self._nonterminal_or_none(ctx.oC_RangeLiteral()),
                  }
        self._AST_node_stack.append(capture)
        if self._verbose:
            print(f"  -> Push RelationshipDetail: {capture}")

    def exitOC_RelationshipTypes(self, ctx:CypherParser.OC_RelationshipTypesContext):
        self._trace_context(ctx, "exitOC_RelationshipTypes")
        reltypes = dict()
        for child in ctx.children:
            if isinstance(child, CypherParser.OC_RelTypeNameContext):
                reltype = self._AST_node_stack.pop()
                reltypes[reltype.text] = reltype
        self._AST_node_stack.append(reltypes)
        if self._verbose:
            print(f"  -->Push Relationship Types: {reltypes}")

    def exitOC_RelTypeName(self, ctx:CypherParser.OC_RelTypeNameContext):
        self._trace_context(ctx, "exitOC_RelTypeName")
        reltype = self._capture_element(ctx.oC_SchemaName())
        self._AST_node_stack.append(reltype)
        if self._verbose:
            print(f"  -->Push RelTypeName: {reltype}")


    # ----------------------------------------------------------
    # Utility methods

    def _nonterminal_or_none(self, nonterminal):
        if nonterminal is None:
            return None
        return nonterminal.getText()

    def _filter_out_spaces(self, children):
        return [_ for _ in children if _.getText() != ' ']

    def _extract_specific_types_of_children(self, children, specific_type):
        return [_ for _ in children if isinstance(_, specific_type)]

    def _capture_element(self, ctx):
        if ctx is None:
            return QueryElement(None, None)
        return QueryElement(ctx.getText(), self._encode_location(ctx))

    def _encode_location(self, ctx):
        start = ctx.start
        stop = ctx.stop
        length = ctx.stop.stop - ctx.start.start + 1
        data = {'offset': start.start, 'length': length,
                'start': {'column': start.column, 'line': start.line},
                'stop': {'column': stop.column, 'line': stop.line},
               }
        return data

    def _trace_context(self, ctx, name):
        if self._verbose:
            print(f"\n====================> {name}: {ctx.getText()}")
            print(f"  getChildCount: {ctx.getChildCount()}")
            print(f"  children: {ctx.children}")
