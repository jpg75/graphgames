from graph_tool import Graph
import string
from networkx import read_graphml
from networkx.readwrite import json_graph
from json import dumps

__author__ = 'Gian Paolo Jesi'
"""
Collection of useful networks.
"""


def graphml_to_json(graph_file, outfile):
    """
    Converts GraphML file to json. JSON output is usable with D3 force layout.

    :param graph_file: graphml file
    :param outfile: json output file
    """
    G = read_graphml(graph_file)
    node_link = json_graph.node_link_data(G)
    with open(outfile) as f:
        f.write(dumps(node_link))


def make_toy_graph(n=7,
                   tuples=[('a', 'b'), ('a', 'c'), ('a', 'd'), ('b', 'a'), ('b', 'd'), ('c', 'g'),
                           ('d', 'a'), ('d', 'f'), ('d', 'g'), ('e', 'b'), ('e', 'd'), ('f', 'c'),
                           ('g', 'e')], as_undirected=False):
    """
    Generate a toy graph for experimenting algorithms. By default the graph has 7 vertexes linked
    by 13 edges. Each vertex is represented by a lowercase letter.

    :param n: number of vertexes; default 7
    :param tuples: list of pairs representing the edges. It is the toy graph in my notebook :-)
    :param as_undirected: makes the graph undirected, but keeping an explicit directional
    representation. Essentially, the graph is still directed and each edge is reproduced in the
    opposite direction.
    :return:
    """
    assert n <= 26

    if as_undirected:
        tuples.extend([(item[1], item[0]) for item in tuples])
        print tuples

    g = Graph()
    vertex_it = g.add_vertex(n=n)
    g.vertex_properties['name'] = g.new_vertex_property('string')
    alphabet = list(string.ascii_lowercase)
    d = dict()
    i = 0
    for v in vertex_it:
        d[alphabet[i]] = v
        g.vp.name[v] = alphabet[i]
        i += 1

    vt = [(d[item[0]], d[item[1]]) for item in tuples]
    g.add_edge_list(vt)

    return g
